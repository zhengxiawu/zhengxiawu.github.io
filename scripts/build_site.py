#!/usr/bin/env python3
"""Build the bilingual, JavaScript-free GitHub Pages site."""

import argparse
import html
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://zhengxiawu.github.io/"
PAGES = {
    "en": {"home": "index.html", "students": "students.html", "projects": "projects.html"},
    "zh": {"home": "zh.html", "students": "students-zh.html", "projects": "projects-zh.html"},
}
INDUSTRY_IDS = (
    "hisilicon", "mindpipe", "huawei-carbu", "bytedance",
    "alibaba", "honor", "vivo", "oppo",
    "huawei-multi-strategy-compression", "tencent", "didi",
)
SUPPORT_IDS = ("nsfc", "postdoc-innovation", "postdoc-general", "pengcheng", "xiaomi")


def escape(value):
    return html.escape(str(value), quote=True)


def render(template, values):
    def substitute(match):
        key = match.group(1)
        if key not in values:
            raise ValueError(f"Missing template value: {key}")
        return values[key]

    return re.sub(r"\{\{([a-z_]+)\}\}", substitute, template)


def navigation(locale, page, text):
    home = PAGES[locale]["home"]
    students = PAGES[locale]["students"]
    projects = PAGES[locale]["projects"]
    home_current = ' aria-current="page"' if page == "home" else ""
    students_current = ' aria-current="page"' if page == "students" else ""
    projects_current = ' aria-current="page"' if page == "projects" else ""
    languages = []
    for code, label in (("en", "English"), ("zh", "中文")):
        current = ' aria-current="page"' if code == locale else ""
        lang = "en" if code == "en" else "zh-CN"
        languages.append(
            f'<a href="{PAGES[code][page]}" lang="{lang}" '
            f'hreflang="{lang}"{current}>{label}</a>'
        )
    return (
        f'<nav class="site-nav" aria-label="{escape(text["navigation_label"])}">'
        '<div class="nav-links">'
        f'<a href="{home}"{home_current}>{text["home_label"]}</a>'
        f'<a href="{home}#publications">{text["papers_label"]}</a>'
        f'<a href="{projects}"{projects_current}>{text["projects_label"]}</a>'
        f'<a href="{students}"{students_current}>{text["students_label"]}</a>'
        '</div>'
        f'<div class="language-switch" aria-label="{escape(text["language_label"])}">'
        + "".join(languages)
        + "</div></nav>"
    )


def project_list(projects, locale, detailed=False, group="industry"):
    entries = []
    by_id = {project["id"]: project for project in projects}
    ids = INDUSTRY_IDS if group == "industry" else SUPPORT_IDS
    for project_id in ids:
        project = by_id[project_id]
        item = project[locale]
        period_markup = (
            f'<div class="project-period">{escape(item["period"])}</div>'
            if item.get("period") else ""
        )
        figure_markup = ""
        logo_markup = ""
        if project.get("logo"):
            logo = project["logo"]
            logo_classes = ["project-logo"]
            if logo.get("theme") == "dark":
                logo_classes.append("logo-dark")
            if logo.get("shape") == "symbol":
                logo_classes.append("logo-symbol")
            logo_class = " ".join(logo_classes)
            logo_markup = (
                f'<img class="{logo_class}" src="{escape(logo["src"])}" '
                f'alt="{escape(logo[locale])}" width="140" height="44" '
                'loading="eager" decoding="sync" />'
            )
        if detailed and group == "industry":
            separator = " " if locale == "en" else ""
            description = escape(separator.join(item["details"]))
            if project.get("evaluation"):
                description += separator + escape(project["evaluation"][locale])
            if project.get("reported_metrics"):
                description += separator + (
                    '<span class="reported-metric">'
                    f'{escape(project["reported_metrics"][locale])}</span>'
                )
            body = f'<p class="project-description">{description}</p>'
            if project.get("figure"):
                figure = project["figure"]
                caption = figure[locale]
                figure_markup = (
                    '<div class="project-figure">'
                    f'<a href="{escape(figure["src"])}" aria-label="{escape(caption["alt"])}" '
                    f'title="{escape(caption["caption"])}">'
                    f'<img src="{escape(figure["src"])}" alt="{escape(caption["alt"])}" '
                    f'width="{figure["width"]}" height="{figure["height"]}" '
                    'loading="lazy" decoding="async" /></a>'
                    '</div>'
                )
        elif group == "support":
            body = f'<p>{escape(item["summary"])}</p>'
        else:
            body = f'<p>{escape(item["summary"])}</p>'
        if item.get("outcomes"):
            outcomes = "".join(f'<li>{escape(outcome)}</li>' for outcome in item["outcomes"])
            body += (
                f'<p class="outcome-label">{escape(item["outcome_label"])}</p>'
                f'<ul class="result-metrics">{outcomes}</ul>'
            )
        entries.append(
            f'<li class="project-entry" id="{escape(project["id"])}">'
            '<div class="project-aside">'
            f'{logo_markup}'
            f'{period_markup}'
            f'{figure_markup}</div>'
            '<div>'
            f'<h3>{escape(item["title"])}</h3>'
            f'<p class="project-meta">{escape(item["sponsor"])} · '
            f'<strong class="project-role">{escape(item["role"])}</strong></p>'
            f'{body}'
            '</div></li>'
        )
    return f'<ul class="project-list {group}-list">' + "".join(entries) + "</ul>"


def student_sections(groups, locale):
    sections = []
    order = {"alumni": 0, "phd": 1, "masters": 2}
    for group in sorted(groups, key=lambda item: order[item["id"]]):
        rows = []
        columns = group["columns"]
        for person in group["people"]:
            item = person[locale]
            cells = []
            name = escape(item["name"])
            if person.get("url"):
                name = f'<a href="{escape(person["url"])}">{name}</a>'
            links = "".join(
                f'<a href="{escape(link["url"])}">{escape(link["label"])}</a> '
                for link in person.get("links", [])
            )
            name = f'<span class="student-name">{name}</span>'
            name += f'<div class="person-work">{links}</div>' if links else ""
            for column in columns:
                value = name if column["key"] == "name" else escape(item.get(column["key"], ""))
                tag = "th" if column["key"] == "name" else "td"
                scope = ' scope="row"' if tag == "th" else ""
                cells.append(f'<{tag}{scope} data-label="{escape(column[locale])}">{value}</{tag}>')
            rows.append("<tr>" + "".join(cells) + "</tr>")
        heading = escape(group[locale]["heading"])
        headers = "".join(f'<th scope="col">{escape(column[locale])}</th>' for column in columns)
        sections.append(
            f'<section id="{escape(group["id"])}">'
            f'<h2>{heading}</h2>'
            f'<table class="student-table" aria-label="{heading}">'
            f'<thead><tr>{headers}</tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></section>"
        )
    return "\n".join(sections)


def student_preview(groups, locale):
    lines = []
    by_id = {group["id"]: group for group in groups}
    labels = {
        "en": {"phd": "PhD", "masters": "Master's", "alumni": "Alumni"},
        "zh": {"phd": "在读博士", "masters": "在读硕士", "alumni": "毕业生"},
    }
    separator = "; " if locale == "en" else "、"
    for group_id in ("alumni", "phd", "masters"):
        names = []
        for person in by_id[group_id]["people"]:
            item = person[locale]
            name = f'<span class="student-preview-name">{escape(item["name"])}</span>'
            if group_id == "alumni" and item.get("destination"):
                brackets = (" (", ")") if locale == "en" else ("（", "）")
                name += brackets[0] + escape(item["destination"]) + brackets[1]
            names.append(name)
        lines.append(
            '<p class="student-preview-line">'
            f'<span class="student-preview-label">{escape(labels[locale][group_id])}'
            f'{"：" if locale == "zh" else ": "}</span>'
            + separator.join(names) + "</p>"
        )
    return "\n".join(lines)


def build(check=False):
    content = json.loads((ROOT / "data/content.json").read_text(encoding="utf-8"))
    projects = json.loads((ROOT / "data/projects.json").read_text(encoding="utf-8"))
    media = json.loads((ROOT / "data/project-media.json").read_text(encoding="utf-8"))
    for project in projects:
        if project["id"] in media:
            project["figure"] = media[project["id"]]
            for locale in ("en", "zh"):
                project["figure"][locale]["alt"] = (
                    project[locale]["title"] + ": " + project["figure"][locale]["alt"]
                )
    students = json.loads((ROOT / "data/students.json").read_text(encoding="utf-8"))
    stale = []
    for locale, pages in PAGES.items():
        for page, filename in pages.items():
            values = dict(content[locale])
            values["lang"] = "en" if locale == "en" else "zh-CN"
            values["navigation"] = navigation(locale, page, values)
            values["students_url"] = pages["students"]
            values["projects_url"] = pages["projects"]
            values["projects"] = project_list(projects, locale, detailed=page == "projects")
            values["support_projects"] = project_list(projects, locale, group="support")
            values["project_index"] = '<ul class="project-index">' + "".join(
                f'<li><a href="#{escape(project_id)}">{escape(next(project for project in projects if project["id"] == project_id)[locale]["title"])}</a></li>'
                for project_id in INDUSTRY_IDS
            ) + "</ul>"
            values["student_sections"] = student_sections(students, locale)
            values["student_preview"] = student_preview(students, locale)
            values["alternate_links"] = "\n  ".join([
                f'<link rel="canonical" href="{BASE_URL}{filename}" />',
                f'<link rel="alternate" hreflang="en" href="{BASE_URL}{PAGES["en"][page]}" />',
                f'<link rel="alternate" hreflang="zh-CN" href="{BASE_URL}{PAGES["zh"][page]}" />',
                f'<link rel="alternate" hreflang="x-default" href="{BASE_URL}{PAGES["en"][page]}" />',
            ])
            template = (ROOT / f"templates/{page}.html").read_text(encoding="utf-8")
            output = render(template, values)
            target = ROOT / filename
            if check:
                if not target.exists() or target.read_text(encoding="utf-8") != output:
                    stale.append(filename)
            else:
                target.write_text(output, encoding="utf-8")
                print(f"Built {filename}")
    if stale:
        raise SystemExit("Generated pages are stale: " + ", ".join(stale))
    if check:
        print("All six generated pages are up to date.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check without writing.")
    build(parser.parse_args().check)
