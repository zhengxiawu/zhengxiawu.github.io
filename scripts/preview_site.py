#!/usr/bin/env python3
"""Read-only, exact-asset website preview on 127.0.0.1."""

import argparse
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import mimetypes
import os
from pathlib import Path
import stat
from urllib.parse import unquote, urlsplit

from build_site import PAGES, ROOT


def asset_path(path):
    """Reject ambiguous and private paths instead of normalizing them."""
    path = unquote(path, errors="strict")
    if not path or "\\" in path or "%" in path or "\x00" in path:
        raise ValueError("Invalid asset path")
    parts = path.removeprefix("/").split("/")
    if any(not part or part.startswith(".") or
           part in {"data", "scripts", "templates"} for part in parts):
        raise ValueError("Private or noncanonical asset path")
    return "/".join(parts)


def read_asset(root, name):
    """Open each component without following symlinks, then snapshot bytes."""
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parts = name.split("/")
        for part in parts[:-1]:
            child = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=directory,
            )
            os.close(directory)
            directory = child
        descriptor = os.open(
            parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=directory,
        )
        with os.fdopen(descriptor, "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ValueError(f"Not a regular file: {name}")
            return source.read()
    finally:
        os.close(directory)


class ImageSources(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sources = []

    def handle_starttag(self, tag, attributes):
        if tag == "img":
            src = dict(attributes).get("src")
            if src:
                self.sources.append(src)


def collect_assets(root):
    assets = {}
    for pages in PAGES.values():
        for filename in pages.values():
            name = asset_path(filename)
            assets["/" + name] = (read_asset(root, name), "text/html; charset=utf-8")
    assets["/style.css"] = (read_asset(root, "style.css"), "text/css; charset=utf-8")
    for body, content_type in list(assets.values()):
        if not content_type.startswith("text/html"):
            continue
        parser = ImageSources()
        parser.feed(body.decode("utf-8"))
        parser.close()
        for src in parser.sources:
            url = urlsplit(src)
            if url.scheme or url.netloc:
                continue
            name = asset_path(url.path)
            media_type = mimetypes.guess_type(name)[0]
            if not media_type or not media_type.startswith("image/"):
                raise ValueError(f"Non-image local src: {src}")
            key = "/" + name
            if key not in assets:
                assets[key] = (read_asset(root, name), media_type)
    return assets


class PreviewHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def parse_request(self):
        if not super().parse_request():
            return False
        hosts = self.headers.get_all("Host", [])
        port = self.server.server_port
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if port == 80:
            allowed.update({"127.0.0.1", "localhost"})
        if len(hosts) != 1 or hosts[0].lower() not in allowed:
            self.send_error(403, "Loopback Host required")
            return False
        if self.command not in {"GET", "HEAD"}:
            self.send_response(405)
            self.send_header("Allow", "GET, HEAD")
            self.send_header("Content-Length", "0")
            self.end_headers()
            self.close_connection = True
            return False
        # BaseHTTPRequestHandler normalizes leading //; inspect the raw target.
        target = self.raw_requestline.split()[1].decode("iso-8859-1")
        if not target.startswith("/") or target.startswith("//"):
            self.send_error(404)
            return False
        return True

    def do_GET(self):
        try:
            path = urlsplit(self.path).path
            name = "index.html" if path == "/" else asset_path(path)
            asset = self.server.assets.get("/" + name)
        except (ValueError, UnicodeError):
            asset = None
        if asset is None:
            self.send_error(404)
            return
        body, content_type = asset
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command == "GET":
            self.wfile.write(body)

    do_HEAD = do_GET


def create_server(port=8765, root=ROOT):
    if not 0 <= port <= 65535:
        raise ValueError("Port must be between 0 and 65535")
    assets = collect_assets(Path(root))
    server = ThreadingHTTPServer(("127.0.0.1", port), PreviewHandler)
    server.assets = assets
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    with create_server(args.port) as server:
        print(f"Preview: http://127.0.0.1:{server.server_port}/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
