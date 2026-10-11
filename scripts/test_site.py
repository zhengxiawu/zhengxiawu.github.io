#!/usr/bin/env python3
"""Offline structural checks for every generated page."""

from html.parser import HTMLParser
from html import escape as html_escape
import json
import re
import unittest
from urllib.parse import unquote, urlsplit

from build_site import INDUSTRY_IDS, PAGES, ROOT, SUPPORT_IDS, build


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.links = []
        self.images = []
        self.lang = ""
        self.headings = []
        self.project_descriptions = 0
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "html":
            self.lang = attrs.get("lang")
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag == "img":
            self.images.append(attrs)
        if tag == "p" and attrs.get("class") == "project-description":
            self.project_descriptions += 1
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append(tag)


class SiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texts = {
            filename: (ROOT / filename).read_text(encoding="utf-8")
            for pages in PAGES.values() for filename in pages.values()
        }
        cls.docs = {key: Document(value) for key, value in cls.texts.items()}

    def test_generated_pages_match_sources(self):
        build(check=True)

    def test_language_and_headings(self):
        for locale, pages in PAGES.items():
            for filename in pages.values():
                with self.subTest(page=filename):
                    doc = self.docs[filename]
                    self.assertEqual(doc.lang, "en" if locale == "en" else "zh-CN")
                    self.assertEqual(doc.headings.count("h1"), 1)
                    self.assertEqual(len(doc.ids), len(set(doc.ids)))
                    self.assertNotIn("{{", self.texts[filename])

    def test_relative_links_and_fragments(self):
        for filename, doc in self.docs.items():
            for href in doc.links:
                with self.subTest(page=filename, href=href):
                    self.assertTrue(href)
                    url = urlsplit(href)
                    if url.scheme or url.netloc:
                        self.assertIn(url.scheme, ("https", "mailto"))
                        continue
                    target_name = unquote(url.path) or filename
                    self.assertTrue((ROOT / target_name).is_file())
                    if url.fragment and target_name in self.docs:
                        self.assertIn(url.fragment, self.docs[target_name].ids)

    def test_images_are_present_and_described(self):
        for filename, doc in self.docs.items():
            for image in doc.images:
                with self.subTest(page=filename, image=image.get("src")):
                    self.assertTrue(image.get("alt"))
                    self.assertTrue((ROOT / image["src"]).is_file())
        publication_images = [
            image for image in self.docs["index.html"].images
            if not image.get("class", "").startswith("project-logo")
        ]
        self.assertEqual(len(publication_images), 17)
        self.assertEqual(
            [image["src"] for image in self.docs["index.html"].images],
            [image["src"] for image in self.docs["zh.html"].images],
        )

    def test_language_switch_stays_on_same_page_type(self):
        for pages in PAGES.values():
            for page, filename in pages.items():
                for destination in PAGES.values():
                    self.assertIn(destination[page], self.docs[filename].links)

    def test_user_confirmed_destinations(self):
        groups = json.loads((ROOT / "data/students.json").read_text(encoding="utf-8"))
        people = next(group for group in groups if group["id"] == "alumni")["people"]
        expected = [
            ("谢展豪", "Tencent", "腾讯"),
            ("王瑞霖", "Tencent", "腾讯"),
            ("罗咏东", "Alibaba", "阿里"),
            ("周陈昱", "Kuaishou", "快手"),
            ("蒋易耕", "Shanghai AI Laboratory", "上海AI Lab"),
        ]
        self.assertEqual(len(people), 6)
        for name, english, chinese in expected:
            matches = [person for person in people if person["zh"]["name"] == name]
            self.assertEqual(len(matches), 1)
            self.assertIn(english, matches[0]["en"]["destination"])
            self.assertIn(chinese, matches[0]["zh"]["destination"])
            self.assertIn(name, matches[0]["en"]["name"])
            if name in ("谢展豪", "王瑞霖"):
                self.assertIn("Qingyun Program", matches[0]["en"]["destination"])
                self.assertIn("青云计划", matches[0]["zh"]["destination"])
            self.assertFalse(matches[0]["en"].get("graduation"))
            self.assertFalse(matches[0]["zh"].get("graduation"))
        for filename in ("students.html", "students-zh.html"):
            text = self.texts[filename]
            for name in ("谢展豪", "王瑞霖", "罗咏东", "周陈昱", "蒋易耕"):
                self.assertIn(name, text)
            alumni_section = re.search(r'<section id="alumni">(.*?)</section>',
                                       text, re.DOTALL).group(1)
            self.assertNotIn("TEG", alumni_section)
            self.assertNotIn("AI Infra", alumni_section)
            self.assertNotIn("Hunyuan", alumni_section)
            self.assertNotIn("混元", alumni_section)
            self.assertNotIn("Video-RAG", alumni_section)
            self.assertIn("QuoTA", alumni_section)
        self.assertEqual(self.texts["students-zh.html"].count("青云计划"), 2)

    def test_full_roster_and_bilingual_fields(self):
        groups = json.loads((ROOT / "data/students.json").read_text(encoding="utf-8"))
        self.assertEqual(
            {group["id"]: len(group["people"]) for group in groups},
            {"phd": 8, "masters": 23, "alumni": 6},
        )
        names = []
        for group in groups:
            for person in group["people"]:
                name = person["zh"]["name"]
                names.append(name)
                self.assertIn(name, person["en"]["name"])
                for column in group["columns"]:
                    key = column["key"]
                    self.assertEqual(bool(person["en"].get(key)), bool(person["zh"].get(key)))
                for filename in ("students.html", "students-zh.html"):
                    self.assertIn(name, self.texts[filename])
        self.assertEqual(len(names), len(set(names)))
        alumni = next(group for group in groups if group["id"] == "alumni")["people"]
        graduate = next(person for person in alumni if person["zh"]["name"] == "许希威")
        self.assertFalse(graduate["zh"].get("destination"))
        for person in alumni:
            self.assertEqual(person["zh"]["cohort"], "2023级")
            self.assertEqual(person["en"]["cohort"], "Entered 2023")
            for locale in ("en", "zh"):
                self.assertNotIn("graduation", person[locale])
        alumni_group = next(group for group in groups if group["id"] == "alumni")
        self.assertEqual([column["key"] for column in alumni_group["columns"]],
                         ["name", "cohort", "destination"])
        masters = next(group for group in groups if group["id"] == "masters")["people"]
        sun = next(person for person in masters if person["zh"]["name"] == "孙颢城")
        self.assertEqual(sun["en"]["internship"], "Tencent Youtu")

    def test_all_project_details_and_roles(self):
        projects = json.loads((ROOT / "data/projects.json").read_text(encoding="utf-8"))
        self.assertEqual(
            [project["id"] for project in projects],
            ["nsfc", "postdoc-innovation", "postdoc-general", "xiaomi", "mindpipe",
             "alibaba", "honor", "vivo", "tencent", "didi", "oppo", "pengcheng",
             "huawei-multi-strategy-compression", "huawei-carbu", "hisilicon"],
        )
        for project in projects:
            self.assertEqual(len(project["en"]["details"]), len(project["zh"]["details"]))
            for locale in ("en", "zh"):
                item = project[locale]
                self.assertGreaterEqual(len(item["details"]), 2)
                page = self.texts[PAGES[locale]["projects"]]
                self.assertIn(html_escape(item["title"]), page)
                self.assertIn(html_escape(item["role"]), page)
                if project["id"] in INDUSTRY_IDS:
                    for paragraph in item["details"]:
                        self.assertIn(html_escape(paragraph), page)
                    separator = " " if locale == "en" else ""
                    self.assertIn(
                        f'<p class="project-description">{html_escape(separator.join(item["details"]), quote=True)}',
                        page,
                    )
                else:
                    self.assertIn(html_escape(item["summary"]), page)
        for locale in ("en", "zh"):
            self.assertEqual(self.docs[PAGES[locale]["projects"]].project_descriptions,
                             len(INDUSTRY_IDS))
        mindpipe = next(project for project in projects if project["id"] == "mindpipe")
        self.assertEqual(mindpipe["en"]["role"], "Project Leader")
        for project in projects:
            if project["id"] in ("hisilicon", "huawei-carbu", "alibaba", "honor", "vivo", "oppo"):
                self.assertEqual(project["en"]["role"], "Project Leader")
                self.assertEqual(project["zh"]["role"], "项目负责人 / Project Leader")
                self.assertIn("As project leader", " ".join(project["en"]["details"]))
                self.assertIn("本人作为项目负责人", "".join(project["zh"]["details"]))
            if project["id"] in ("tencent", "didi"):
                self.assertEqual(project["en"]["role"], "Core Algorithm Developer")
            text = json.dumps(project, ensure_ascii=False)
            self.assertNotIn("纪荣嵘", text)
            self.assertNotIn("Rongrong Ji", text)
        for project in projects:
            for locale in ("en", "zh"):
                self.assertNotRegex(json.dumps(project[locale], ensure_ascii=False),
                                    r"Hi3516|39个|5个指定|62576299|万元|/Users/")

    def test_current_user_roster_corrections(self):
        groups = json.loads((ROOT / "data/students.json").read_text(encoding="utf-8"))
        people = {person["zh"]["name"]: person for group in groups for person in group["people"]}
        for name in ("杨晨艺", "刘文婧", "张蓓蓓", "陈诺", "邱聪祝", "吕瑞峰"):
            self.assertNotIn(name, people)
        expected = {
            "吴宇航": ("字节跳动", "ByteDance"),
            "陈志刚": ("美图、宁德时代", "Meitu; CATL"),
            "李桂林": ("腾讯", "Tencent"),
            "李旭东": ("腾讯", "Tencent"),
            "焦雨飞": ("京东", "JD.com"),
        }
        for name, (chinese, english) in expected.items():
            self.assertEqual(people[name]["zh"]["internship"], chinese)
            self.assertEqual(people[name]["en"]["internship"], english)
        self.assertNotIn("廖鲲鹏", people)
        self.assertIn("Kunpeng Liao", people["廖锟鹏"]["en"]["name"])
        self.assertEqual(people["廖锟鹏"]["zh"]["year"], "研三（2024级）")
        self.assertIn("Yufei Jiao", people["焦雨飞"]["en"]["name"])
        for locale in ("en", "zh"):
            self.assertNotRegex(people["黄伟中"][locale]["internship"], r"2026|2027")

    def test_reported_academic_internships(self):
        groups = json.loads((ROOT / "data/students.json").read_text(encoding="utf-8"))
        people = {person["zh"]["name"]: person for group in groups for person in group["people"]}
        expected = {
            "曾宇晖": ("快手可灵：基模数据算子与后训练", "Kuaishou Kling"),
            "吴豪翔": ("vivo：多模态大模型后训练；蚂蚁集团：多媒体大模型后训练", "vivo"),
            "廖锟鹏": ("百度：大模型预训练；新研智材：Agent开发", "Baidu"),
            "许靖": ("字节跳动：模型优化", "ByteDance"),
            "谢天宇": ("某初创公司：全模态实时交互大模型预训练与后训练", "A startup"),
            "黄皓禹": ("字节跳动：Agentic大模型优化", "ByteDance"),
            "龙成武": ("京东：AI Infra推理加速", "JD.com"),
            "吴鑫雄": ("蚂蚁集团：Infra与模型量化", "Ant Group"),
            "苏锦森": ("美团：多模态大模型评测", "Meituan"),
            "张岳": ("小米：语言模型与多模态模型量化", "Xiaomi"),
            "郑旭哲": ("蚂蚁集团：LLM Infra量化与稀疏化", "Ant Group"),
        }
        for name, (chinese, english) in expected.items():
            person = people[name]
            self.assertEqual(person["zh"]["internship"], chinese)
            self.assertIn(english, person["en"]["internship"])
            for locale in ("en", "zh"):
                self.assertIn(html_escape(person[locale]["internship"]),
                              self.texts[PAGES[locale]["students"]])
                self.assertNotRegex(person[locale]["internship"], r"2027|2028|届|水下")
        self.assertIn("Ant Group", people["吴豪翔"]["en"]["internship"])
        self.assertIn("multimedia", people["吴豪翔"]["en"]["internship"])
        self.assertIn("新研智材", people["廖锟鹏"]["en"]["internship"])
        for person in people.values():
            for locale in ("en", "zh"):
                self.assertNotRegex(person[locale].get("internship", ""),
                                    r"\d{4}|远程|线下|remote|on-site|intern since")
        for locale in ("en", "zh"):
            self.assertEqual(people["宋卓奇"][locale]["internship"], "")

    def test_uniform_student_links(self):
        groups = json.loads((ROOT / "data/students.json").read_text(encoding="utf-8"))
        people = {person["zh"]["name"]: person for group in groups for person in group["people"]}
        for name in ("谢天宇", "马晴川"):
            self.assertFalse(people[name].get("url"))
            self.assertFalse(people[name].get("links"))
        for filename in ("students.html", "students-zh.html"):
            self.assertNotIn('href="https://tianyuxie.github.io', self.texts[filename])
            self.assertNotIn('href="https://qingchuanma.github.io', self.texts[filename])

    def test_project_figures_are_responsive_and_attributed(self):
        projects = json.loads((ROOT / "data/projects.json").read_text(encoding="utf-8"))
        media = json.loads((ROOT / "data/project-media.json").read_text(encoding="utf-8"))
        illustrated = [project for project in projects if project["id"] in INDUSTRY_IDS]
        self.assertEqual(set(media), set(INDUSTRY_IDS))
        for project in illustrated:
            figure = media[project["id"]]
            raw = (ROOT / figure["src"]).read_bytes()
            self.assertEqual(raw[:4], b"RIFF")
            self.assertEqual(raw[8:12], b"WEBP")
            self.assertEqual(figure["kind"], "ai_generated_concept")
            for locale in ("en", "zh"):
                page = PAGES[locale]["projects"]
                images = [image for image in self.docs[page].images
                          if image["src"] == figure["src"]]
                self.assertEqual(len(images), 1)
                self.assertIn(project[locale]["title"], images[0]["alt"])
                self.assertEqual(images[0]["width"], str(figure["width"]))
                self.assertEqual(images[0]["height"], str(figure["height"]))
                self.assertIn(f'title="{html_escape(figure[locale]["caption"])}"',
                              self.texts[page])
                self.assertNotIn("<figcaption>", self.texts[page])
        for filename in ("index.html", "zh.html"):
            self.assertNotIn('class="project-figure"', self.texts[filename])

    def test_industry_precedes_compact_research_support(self):
        for locale, pages in PAGES.items():
            for page_type in ("home", "projects"):
                page = self.texts[pages[page_type]]
                ordered_ids = list(INDUSTRY_IDS) + list(SUPPORT_IDS)
                offsets = [page.index(f'id="{project_id}"') for project_id in ordered_ids]
                self.assertEqual(offsets, sorted(offsets))
                self.assertIn('class="project-list support-list"', page)
        groups = json.loads((ROOT / "data/students.json").read_text(encoding="utf-8"))
        phd = next(group for group in groups if group["id"] == "phd")
        column = next(column for column in phd["columns"] if column["key"] == "internship")
        self.assertEqual(column["zh"], "实习情况")
        self.assertEqual(column["en"], "Internship")

    def test_removed_students_and_normal_name_weight(self):
        for filename in ("students.html", "students-zh.html"):
            text = self.texts[filename]
            for name in ("杨晨艺", "刘文婧", "张蓓蓓", "陈诺", "邱聪祝", "吕瑞峰"):
                self.assertNotIn(name, text)
            self.assertNotRegex(text, r"<(?:strong|b)(?:\s[^>]*)?>")
        for filename in ("index.html", "zh.html"):
            self.assertNotRegex(
                self.texts[filename],
                r"<(?:strong|b)(?:\s[^>]*)?>[^<]*(?:Qingchuan Ma|Tianyu Xie)",
            )
        css = (ROOT / "style.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"\.student-name a\s*\{\s*font-weight:\s*400;")

    def test_unnecessary_profile_link_is_absent(self):
        for filename in self.texts:
            self.assertNotIn("https://iai.xmu.edu.cn/info/2981/5135.htm",
                             self.docs[filename].links)
        for filename in ("index.html", "zh.html"):
            self.assertNotIn("Institute Profile", self.texts[filename])
            self.assertNotIn("研究院主页", self.texts[filename])

    def test_leadership_is_consistent_on_home_and_projects(self):
        for locale, pages in PAGES.items():
            for page in ("home", "projects"):
                text = self.texts[pages[page]]
                self.assertEqual(text.count('class="project-role"'),
                                 len(INDUSTRY_IDS) + len(SUPPORT_IDS))
                self.assertEqual(text.count("Project Leader</strong>"), 7)

    def test_removed_results_and_enterprise_claim_boundaries(self):
        projects = json.loads((ROOT / "data/projects.json").read_text(encoding="utf-8"))
        for project in projects:
            self.assertNotIn("outcome_scope", project)
            for locale in ("en", "zh"):
                self.assertNotIn("outcomes", project[locale])
        for filename in ("projects.html", "projects-zh.html"):
            self.assertNotIn("technical-results", self.texts[filename])
            self.assertNotIn("Core Algorithms &amp; Published Results", self.texts[filename])
            self.assertNotIn("核心算法与公开实测结果", self.texts[filename])
            self.assertNotIn("Institution profile", self.texts[filename])
            self.assertNotIn("学校介绍", self.texts[filename])
            self.assertNotIn("1.5x", self.texts[filename])
            self.assertNotIn("模型9倍压缩", self.texts[filename])
            self.assertNotIn("精度无损", self.texts[filename])
            self.assertNotIn("4.5×", self.texts[filename])

    def test_project_indicators_keep_reported_scope(self):
        projects = json.loads((ROOT / "data/projects.json").read_text(encoding="utf-8"))
        reported = [project for project in projects if project.get("reported_metrics")]
        self.assertEqual([project["id"] for project in reported],
                         ["honor", "huawei-multi-strategy-compression"])
        for project in projects:
            if project["id"] in INDUSTRY_IDS:
                for locale in ("en", "zh"):
                    self.assertIn(html_escape(project["evaluation"][locale]),
                                  self.texts[PAGES[locale]["projects"]])
        for project in reported:
            metrics = project["reported_metrics"]
            self.assertIn(metrics["status"], (
                "dated_project_summary_not_independent_acceptance",
                "academic_report_performance_not_independent_acceptance",
            ))
            self.assertTrue(metrics["requires_public_clearance"])
            self.assertNotIn("summary-reported", metrics["en"])
            self.assertNotIn("尚待确认", metrics["zh"])
            for locale in ("en", "zh"):
                self.assertIn(html_escape(metrics[locale]),
                              self.texts[PAGES[locale]["projects"]])

    def test_distinct_huawei_projects_and_award(self):
        projects = json.loads((ROOT / "data/projects.json").read_text(encoding="utf-8"))
        by_id = {project["id"]: project for project in projects}
        early = by_id["huawei-multi-strategy-compression"]
        self.assertEqual(early["zh"]["period"], "2024年前后")
        self.assertEqual(early["en"]["period"], "Around 2024")
        self.assertIn("产品线级优秀合作项目", "".join(early["zh"]["details"]))
        self.assertNotIn("产品线级优秀合作项目",
                         "".join(by_id["mindpipe"]["zh"]["details"]))
        self.assertNotIn("reported_metrics", by_id["mindpipe"])
        carbu = by_id["huawei-carbu"]
        self.assertEqual(carbu["zh"]["role"], "项目负责人 / Project Leader")
        for locale in ("en", "zh"):
            text = json.dumps(carbu[locale], ensure_ascii=False)
            self.assertNotRegex(text, r"50%|30%|1%|2024|ADAS")
        for filename in ("projects.html", "projects-zh.html"):
            self.assertNotIn("尚待确认", self.texts[filename])
            self.assertNotIn("阶段总结记录", self.texts[filename])
            self.assertNotIn("independent acceptance", self.texts[filename])

    def test_removed_project_labels_and_update_footers(self):
        for filename, text in self.texts.items():
            with self.subTest(page=filename):
                self.assertNotIn("研发合作", text)
                self.assertNotIn("研发经历", text)
                self.assertNotIn("Research collaboration", text)
                self.assertNotIn("2024年结题", text)
                self.assertNotIn("2024年结", text)
                self.assertNotIn("Completed in 2024", text)
                self.assertNotIn("completed in 2024", text)
                self.assertNotIn("页面更新", text)
                self.assertNotIn("Last updated:", text)
                self.assertNotIn("<footer", text)
                self.assertNotIn('<div class="project-period"></div>', text)

    def test_homepage_has_compact_section_links_and_student_preview(self):
        for locale, pages in PAGES.items():
            text = self.texts[pages["home"]]
            projects = re.search(r'<section id="projects">(.*?)</section>',
                                 text, re.DOTALL).group(1)
            students = re.search(r'<section id="students">(.*?)</section>',
                                 text, re.DOTALL).group(1)
            self.assertIn('<span class="heading-detail">', projects)
            self.assertIn(f'href="{pages["projects"]}"', projects)
            self.assertEqual(len(Document(projects).links), 1)
            self.assertNotIn("项目详情", projects)
            self.assertNotIn("Project details", projects)
            self.assertNotIn("查看完整项目与技术工作详情", projects)
            self.assertNotIn("逐项列明本人承担角色", projects)
            self.assertNotIn("section-note", projects)
            self.assertIn(f'href="{pages["students"]}"', students)
            self.assertEqual(students.count('class="student-preview-line"'), 3)
            groups = json.loads((ROOT / "data/students.json").read_text(encoding="utf-8"))
            for group in groups:
                for person in group["people"]:
                    self.assertIn(html_escape(person[locale]["name"]), students)
            self.assertNotIn("联合培养", students)
            self.assertNotIn("Years of study", students)
            self.assertNotIn("students_page_intro", self.texts[pages["students"]])
            self.assertNotIn("年级按2026年秋季列示", self.texts[pages["students"]])
            self.assertNotIn("Students working with me through supervision",
                             self.texts[pages["students"]])

    def test_scale_based_metrics_and_documented_project_years(self):
        projects = json.loads((ROOT / "data/projects.json").read_text(encoding="utf-8"))
        by_id = {project["id"]: project for project in projects}
        for locale, pages in PAGES.items():
            text = self.texts[pages["projects"]]
            self.assertNotIn("LLaMA", text)
            self.assertIn("10B", text)
            self.assertIn("70B", text)
            self.assertNotIn("R&amp;D experience</div>", text)
        for project_id in ("alibaba", "honor", "vivo"):
            self.assertEqual(by_id[project_id]["zh"]["period"], "2021—2022年")
            self.assertEqual(by_id[project_id]["en"]["period"], "2021 - 2022")
        self.assertEqual(by_id["mindpipe"]["zh"]["period"], "2025—2027年")
        for project_id in ("tencent", "didi", "oppo"):
            self.assertEqual(by_id[project_id]["zh"]["period"], "博士期间")
        self.assertEqual(by_id["huawei-carbu"]["zh"]["period"], "2025年")
        self.assertEqual(by_id["huawei-carbu"]["en"]["period"], "2025")
        self.assertEqual(by_id["hisilicon"]["zh"]["period"], "2026年至今")
        self.assertEqual(by_id["hisilicon"]["en"]["period"], "2026 - present")

    def test_homepage_omits_editorial_notes_and_biography_date_qualifiers(self):
        forbidden = (
            "精选 IEEE TPAMI", "按时间由近及远", "优先展示近期通讯作者",
            "随后列出", "* 通讯作者", "* corresponding author",
            "ordered from recent", "appear first", "含共同",
            "including shared authorship", "截至2026年10月", "As of October 2026",
            "2025年5月至2026年5月", "From May 2025 to May 2026",
            "2021年12月", "December 2021",
        )
        for locale, pages in PAGES.items():
            text = self.texts[pages["home"]]
            for phrase in forbidden:
                self.assertNotIn(phrase, text)
            self.assertNotIn("section-note", text)
            biography = re.search(r'<section id="biography">(.*?)</section>',
                                  text, re.DOTALL).group(1)
            self.assertEqual(biography.count("<p>"), 1)
            self.assertIn("曾担任" if locale == "zh" else "previously served", biography)

    def test_socialomni_has_original_figure_verified_links_and_preprint_status(self):
        for pages in PAGES.values():
            text = self.texts[pages["home"]]
            article = re.search(
                r'<article class="pub">\s*<a[^>]*aria-label="SocialOmni paper".*?</article>',
                text, re.DOTALL).group(0)
            self.assertIn('src="images/papers/real/socialomni.jpg"', article)
            self.assertIn('href="https://arxiv.org/abs/2603.16859">Paper', article)
            self.assertIn('href="https://mac-automl.github.io/SocialOmni/">Project', article)
            self.assertIn('href="https://github.com/MAC-AutoML/SocialOmni">Code', article)
            self.assertIn('<span class="pub-venue">arXiv, 2026</span>', article)
            self.assertNotIn("AAAI", article)
            self.assertIn('Rongrong Ji, and <strong>Xiawu Zheng</strong>'
                          '<sup class="corresponding-star">*</sup>', article)

    def test_socialomni_and_alumni_are_first(self):
        for locale, pages in PAGES.items():
            home = self.texts[pages["home"]]
            publications = re.search(r'<section id="publications">(.*?)</section>',
                                     home, re.DOTALL).group(1)
            first_article = re.search(r'<article class="pub">(.*?)</article>',
                                      publications, re.DOTALL).group(1)
            self.assertIn('aria-label="SocialOmni paper"', first_article)
            self.assertEqual(publications.count('aria-label="SocialOmni paper"'), 1)
            students = re.search(r'<section id="students">(.*?)</section>',
                                 home, re.DOTALL).group(1)
            labels = re.findall(r'class="student-preview-label">(.*?)</span>',
                                students)
            expected = ("毕业生", "在读博士", "在读硕士") if locale == "zh" else (
                "Alumni", "PhD", "Master's")
            for label, prefix in zip(labels, expected):
                self.assertTrue(label.startswith(html_escape(prefix)))
            student_page = self.texts[pages["students"]]
            self.assertLess(student_page.index('<section id="alumni">'),
                            student_page.index('<section id="phd">'))
            self.assertLess(student_page.index('<section id="phd">'),
                            student_page.index('<section id="masters">'))

    def test_paper_project_links_are_official_and_separate_from_code(self):
        expected = (
            "https://mac-automl.github.io/SocialOmni/",
            "https://video-rag.github.io/",
            "https://vita-home.github.io/",
            "https://video-mme.github.io/",
            "https://mme-benchmark.github.io/",
            "https://foundationagents.deepwisdom.ai/projects/metagpt/",
        )
        for pages in PAGES.values():
            text = self.texts[pages["home"]]
            projects = re.findall(r'<a href="([^"]+)">Project</a>', text)
            self.assertEqual(tuple(projects), expected)
            for article in re.findall(r'<article class="pub">(.*?)</article>', text, re.DOTALL):
                links = re.findall(r'<a href="([^"]+)">(Paper|Project|Code|XNAS)</a>', article)
                self.assertEqual(len({url for url, label in links}), len(links))

    def test_logos_load_eagerly_and_nsfc_mark_is_trimmed(self):
        projects = json.loads((ROOT / "data/projects.json").read_text(encoding="utf-8"))
        by_id = {project["id"]: project for project in projects}
        for project_id in ("vivo", "didi"):
            self.assertEqual(by_id[project_id]["logo"]["theme"], "dark")
        for filename, doc in self.docs.items():
            for image in doc.images:
                if image.get("class", "").startswith("project-logo"):
                    self.assertEqual(image["loading"], "eager")
                    self.assertEqual(image["decoding"], "sync")
        for locale, pages in PAGES.items():
            for page_type in ("home", "projects"):
                image = next(image for image in self.docs[pages[page_type]].images
                             if image["alt"] == ("NSFC" if locale == "en" else "国家自然科学基金"))
                self.assertEqual(image["src"], "images/logos/nsfc-mark-20261010.png")
                self.assertIn("logo-symbol", image["class"])

    def test_postdoctoral_support_has_official_foundation_logo(self):
        projects = json.loads((ROOT / "data/projects.json").read_text(encoding="utf-8"))
        by_id = {project["id"]: project for project in projects}
        for project_id in ("postdoc-innovation", "postdoc-general"):
            logo = by_id[project_id]["logo"]
            self.assertEqual(logo["src"], "images/logos/postdoc-foundation-mark-20261010.png")
            self.assertEqual(logo["zh"], "中国博士后科学基金会")
            self.assertTrue((ROOT / logo["src"]).is_file())
            for locale, pages in PAGES.items():
                for page_type in ("home", "projects"):
                    self.assertEqual(self.texts[pages[page_type]].count(
                        f'src="{logo["src"]}"'), 2)

    def test_biography_is_one_paragraph(self):
        for filename in ("index.html", "zh.html"):
            section = re.search(r'<section id="biography">(.*?)</section>',
                                self.texts[filename], re.DOTALL).group(1)
            self.assertEqual(section.count("<p>"), 1)
            self.assertEqual(section.count("</p>"), 1)

    def test_public_files_do_not_contain_private_paths(self):
        paths = [
            ROOT / "README.md", ROOT / "WORKING_STATE.md",
            *ROOT.glob("data/*.json"), *ROOT.glob("templates/*.html"),
            *(ROOT / filename for filename in self.texts),
        ]
        for path in paths:
            filename = str(path.relative_to(ROOT))
            text = path.read_text(encoding="utf-8")
            with self.subTest(page=filename):
                self.assertNotIn("/Users/", text)
                self.assertNotIn("file://", text)
                self.assertNotRegex(text, r"\bUID\s*[`:=]?\s*\d+")
                if filename.endswith(".html"):
                    self.assertNotIn("localhost", text)


if __name__ == "__main__":
    unittest.main()
