# Site Maintenance

- English default: `index.html`; Chinese home: `zh.html`.
- Student pages: `students.html` and `students-zh.html`.
- Project detail pages: `projects.html` and `projects-zh.html`.
- October 10 user-refined update: 8 current PhD students, 23 current master's students,
  6 alumni/career records, and 15 project/support entries in both languages.
- Ten industry collaborations precede five grouped funding/platform entries.
  Company logos and ten generated concept illustrations sit beside project text;
  funding, Peng Cheng Laboratory and Xiaomi support use compact logo-only entries.
- Early Huawei multi-strategy compression is separate from later MindPipe.
  Its Product-Line-Level Outstanding Collaborative Project award is retained;
  completion wording is omitted. Automotive BU is listed separately.
- MindPipe, HiSilicon, Automotive BU, Alibaba/Tmall, HONOR, vivo and OPPO:
  Project Leader, including the October 10 user-confirmed execution roles.
  Early Huawei compression: project management and algorithm R&D.
- Both postdoctoral funding entries use the official foundation emblem.
- Research-collaboration and R&D-experience labels and all update-date footers are omitted.
- Project periods use recorded years or PhD-stage wording. October 10 confirmation:
  early Huawei around 2024, Automotive BU 2025, HiSilicon 2026 to present.
- Early Huawei metrics use 10B-class and 70B-class LLM wording.
- All logos load immediately. The NSFC emblem is tightly trimmed and displayed at 56px.
- Source-supported results appear inside project descriptions. The former
  standalone published-benchmark section has been removed.
- Thirty offline regression checks pass. All six pages were rechecked at
  320, 390 and 1280 pixels on October 10 with no horizontal overflow.
  New postdoctoral emblems load correctly; earlier ten concept images are unchanged.
- Project pages omit institutional-introduction links and other project leaders.
- Student scope includes supervision, joint training and collaboration;
  the roster is not a count of independent admissions.
- Study years refer to autumn 2026. Blank fields remain blank.
- October 9 internship reports are reflected in 11 master's student summaries.
  Multiple placements are retained; the undisclosed startup is not named.
  Kunpeng Liao's current Chinese name is 廖锟鹏.
- Internship cells show company and direction only. Ma Qingchuan and Tianyu Xie
  have no special links; Tianyu's company is "a startup".
- Both student tables label the field Internship; all six alumni show the
  user-confirmed 2023 entry cohort and no graduation-date column.
- Alumni destinations use company and existing talent-program names only.
  Yongdong Luo's student row retains QuoTA but no Video-RAG link.
- The latest roster removes Chen Nuo, Congzhu Qiu and Ruifeng Lv.
- The student-page explanatory introduction is omitted.
- Home sections use a single compact link beside each heading. All 37 retained
  student/alumni names appear in three groups; names remain intact when wrapping.
  Project items have no individual details links.
- Biography and each industry-project description are a single paragraph.
- Publication ordering commentary and corresponding-author legend are removed.
  Biography omits the shared-authorship qualifier, statistics date, PhD award
  date and secondment period; secondment is expressed as previous service.
- SocialOmni is listed as arXiv 2026 with its official project/code links, v3
  authorship and original Figure 1 thumbnail. The first five recent-paper
  repositories do not link independent project sites; their code links remain.
- Followup ordering: alumni precede current PhD and master's students on both
  homepage summaries and full rosters; SocialOmni is the first publication.
- All 16 displayed papers were checked for project sites. MetaGPT now links the
  official Foundation Agents project overview. Existing five Project links are
  retained; no duplicate Project/Code links or guessed project URLs are added.
- The four modified bilingual homepage/student pages pass 12 followup viewport
  checks at 320, 390 and 1280 pixels. New MetaGPT navigation was browser-tested.
- Edit bilingual content in `data/` and shared markup in `templates/`.
- Rebuild with `python3 scripts/build_site.py`.
- Validate with `python3 scripts/test_site.py`.
- Keep original paper figures and evidence-backed author markings.
- Career destinations do not imply a graduation year or an employment start.
- Keep private source records and verification notes outside this public repo.
- Local validation does not mean the website has been deployed.
- Publication approved by the site owner on October 11, 2026.
- Read-only local browser preview: `python3 scripts/preview_site.py --port 8765`.
  The server binds only to loopback and serves a startup snapshot of the six
  generated pages, CSS and referenced images, not source or archive files.
- Restart the preview server after rebuilding pages. Five preview security
  tests pass with `python3 scripts/test_preview_site.py`.
