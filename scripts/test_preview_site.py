#!/usr/bin/env python3
"""Focused loopback preview security and serving tests."""

from contextlib import contextmanager
import http.client
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from build_site import PAGES, ROOT
from preview_site import ImageSources, collect_assets, create_server


@contextmanager
def running_server(root=ROOT):
    server = create_server(0, root)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        if thread.is_alive():
            raise RuntimeError("Test server did not stop")


def request(server, path, method="GET", host=None, body=None):
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        headers = {} if host is None else {"Host": host}
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


class PreviewTest(unittest.TestCase):
    def test_actual_assets_get_and_head(self):
        expected = {"/style.css"}
        for pages in PAGES.values():
            for filename in pages.values():
                expected.add("/" + filename)
                parser = ImageSources()
                parser.feed((ROOT / filename).read_text(encoding="utf-8"))
                expected.update("/" + src for src in parser.sources)
        with running_server() as server:
            self.assertEqual(server.server_address[0], "127.0.0.1")
            self.assertEqual(set(server.assets), expected)
            self.assertEqual(len([p for p in expected if p.endswith(".html")]), 6)
            for path in sorted(expected):
                with self.subTest(path=path):
                    status, headers, body = request(server, path)
                    self.assertEqual(status, 200)
                    self.assertEqual(body, (ROOT / path[1:]).read_bytes())
                    self.assertEqual(int(headers["Content-Length"]), len(body))
                    self.assertEqual(headers["Cache-Control"], "no-store")
                    self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
                    status, head_headers, body = request(server, path, "HEAD")
                    self.assertEqual(status, 200)
                    self.assertEqual(body, b"")
                    self.assertEqual(head_headers["Content-Length"], headers["Content-Length"])
                    self.assertEqual(head_headers["Content-Type"], headers["Content-Type"])
            self.assertEqual(request(server, "/")[2], (ROOT / "index.html").read_bytes())
            self.assertEqual(request(server, "/style.css?v=1")[0], 200)
            self.assertEqual(request(server, "/")[1]["Content-Type"],
                             "text/html; charset=utf-8")
            self.assertEqual(request(server, "/style.css")[1]["Content-Type"],
                             "text/css; charset=utf-8")

    def test_private_paths_traversal_and_methods(self):
        paths = [
            "/data/content.json", "/scripts/build_site.py", "/templates/home.html",
            "/.git/config", "/README.md", "/WORKING_STATE.md", "/images/",
            "/images/unreferenced.jpg", "/../data/content.json",
            "/images/../style.css", "/%2e%2e/data/content.json",
            "/images/%2E%2E/style.css", "/%252e%252e/data/content.json",
            "/images%2f..%2fstyle.css", "/images\\..\\style.css",
            "/%00style.css", "//style.css", "/./style.css",
            "/images//xiawu-zheng.jpg", "/%GG", "/%ff",
        ]
        with running_server() as server:
            for path in paths:
                for method in ("GET", "HEAD"):
                    with self.subTest(path=path, method=method):
                        status, headers, body = request(server, path, method)
                        self.assertEqual(status, 404)
                        self.assertEqual(headers["Cache-Control"], "no-store")
                        if method == "HEAD":
                            self.assertEqual(body, b"")
            for method in ("POST", "PUT", "DELETE", "PATCH", "OPTIONS", "TRACE"):
                with self.subTest(method=method):
                    status, headers, body = request(server, "/index.html", method, body=b"write")
                    self.assertEqual(status, 405)
                    self.assertEqual(headers["Allow"], "GET, HEAD")
                    self.assertEqual(headers["Cache-Control"], "no-store")
                    self.assertEqual(body, b"")

    def test_host_validation(self):
        with running_server() as server:
            for host in ("evil.example", "evil.example:8765", "127.0.0.1.evil",
                         "localhost.evil", "127.0.0.1:1", "[::1]:8765",
                         "user@127.0.0.1", ""):
                with self.subTest(host=host):
                    status, headers, _ = request(server, "/", host=host)
                    self.assertEqual(status, 403)
                    self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertEqual(request(server, "/", host=f"localhost:{server.server_port}")[0], 200)
            for hosts in ([], ["127.0.0.1", "evil.example"]):
                connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                try:
                    connection.putrequest("GET", "/", skip_host=True)
                    for host in hosts:
                        connection.putheader("Host", host)
                    connection.endheaders()
                    response = connection.getresponse()
                    self.assertEqual(response.status, 403)
                    response.read()
                finally:
                    connection.close()

    def test_fixture_allowlist_snapshot_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "images").mkdir()
            (root / "images/allowed.png").write_bytes(b"allowed")
            (root / "images/unreferenced.png").write_bytes(b"private")
            (root / "style.css").write_text("body {}", encoding="utf-8")
            for pages in PAGES.values():
                for filename in pages.values():
                    (root / filename).write_text(
                        '<!-- <img src="images/unreferenced.png"> -->'
                        '<img src="images/allowed.png">'
                        '<img src="https://example.com/external.png">',
                        encoding="utf-8",
                    )
            (root / "images/link.png").symlink_to(root / "images/unreferenced.png")
            with running_server(root) as server:
                self.assertEqual(request(server, "/images/unreferenced.png")[0], 404)
                self.assertEqual(request(server, "/images/link.png")[0], 404)
                self.assertEqual(request(server, "/images/allowed.png", "HEAD")[0], 200)
                (root / "images/allowed.png").unlink()
                (root / "images/allowed.png").symlink_to(root / "images/unreferenced.png")
                self.assertEqual(request(server, "/images/allowed.png")[2], b"allowed")
            with self.assertRaises(OSError):
                collect_assets(root)
            (root / "images/allowed.png").unlink()
            (root / "images/allowed.png").write_bytes(b"allowed")
            (root / "images").rename(root / "other-images")
            (root / "images").symlink_to(root / "other-images", target_is_directory=True)
            with self.assertRaises(OSError):
                collect_assets(root)

    def test_private_references_and_invalid_port_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "style.css").write_text("", encoding="utf-8")
            for src in ("data/private.png", ".git/private.png", "../private.png",
                        "scripts/private.png", "templates/private.png", "README.md"):
                for pages in PAGES.values():
                    for filename in pages.values():
                        (root / filename).write_text(f'<img src="{src}">', encoding="utf-8")
                with self.subTest(src=src), self.assertRaises(ValueError):
                    collect_assets(root)
        for port in (-1, 65536):
            with self.subTest(port=port), patch("preview_site.collect_assets") as collect:
                with self.assertRaises(ValueError):
                    create_server(port)
                collect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
