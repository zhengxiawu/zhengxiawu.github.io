# Xiawu Zheng Homepage

Lightweight academic homepage with English as the default and separate Chinese
and student/project pages. All six pages are static and work without JavaScript.

## Editing

- `data/content.json`: English and Chinese biography, headings and navigation.
- `data/projects.json`: public project descriptions and roles.
- `data/technical-results.json`: first-author published benchmark results.
- `data/students.json`: current student roster, training and career destinations.
- `templates/home.html`: shared publication list and home-page structure.
- `templates/students.html`: student-page structure.
- `templates/projects.html`: project detail structure.
- `style.css`: shared desktop and mobile styles.

Do not put private evidence, contracts, student IDs, contact lists, or local
source paths in this public repository. Do not infer graduation or employment
start dates from an enrollment cohort or an offer destination.

After editing source files, regenerate and test:

```bash
python3 scripts/build_site.py
python3 scripts/test_site.py
```

Commit the generated `index.html`, `zh.html`, `students.html`, and
`students-zh.html`, `projects.html`, and `projects-zh.html` alongside source
changes. GitHub Pages needs no build step.

## Local Preview

Open `index.html` directly in a browser, or run from the repository root:

```bash
python3 -m http.server 8000
```

Then visit `http://localhost:8000`.

## Deployment Notes

Repository:

```text
zhengxiawu.github.io
```

Publishing requires pushing the reviewed changes to the configured GitHub
Pages branch. Local generation or a successful preview is not a deployment.
