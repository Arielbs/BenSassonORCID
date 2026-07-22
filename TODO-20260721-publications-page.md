# TODO — Publications page with citation charts

**Started:** 2026-07-21
**Repo:** BenSassonORCID (public) — https://github.com/Arielbs/BenSassonORCID

## Goal

An interactive HTML page of Ariel J. Ben-Sasson's published papers, with charts
of how citations have grown over time, published live via GitHub Pages so it can
be shared.

## Facts learned

- **ORCID:** 0000-0003-3395-6327 → Ariel J. Ben-Sasson, University of Washington
  (verified on OpenAlex 2026-07-21). Alt names: Ariel Ben-Sasson, Ariel J.
  Ben-Sasson, Ariel Jaques Ben-Sasson.
- **OpenAlex snapshot:** 19 works, 731 total citations (pre-fetch, unfiltered).
- Data source: OpenAlex. Yearly citation breakdown only available from ~2012 on;
  older citations count in lifetime totals but aren't broken out by year.

## Plan / status

- [x] Create public repo `BenSassonORCID`, push to GitHub, default branch `main`.
- [x] Start this spec.
- [x] Fetch works from OpenAlex by ORCID via `fetch_papers.py` → `papers.json` +
      `papers.csv`. Retry-on-429 built in.
- [x] Review the list. All confirmed mine. Dropped 4 duplicates (3 bioRxiv
      preprints + 1 Author Correction erratum) via `excluded_works.txt`.
      **Kept 15 unique works, 712 citations** (13 articles, 1 conference paper,
      1 conference abstract). Two eras: organic FETs/device physics 2009–2015,
      protein materials design 2021–2025.
- [x] Design interview (3 rounds) → folded into design decisions below → approved.
- [x] Build `index.html` via `build_page.py`, reviewed in browser.
- [x] Refinements: added Google Scholar link, new intro sentence, second
      highlight ("first vertical OFET") on the 2009 block-copolymer paper.
- [x] Publish with GitHub Pages. **LIVE: https://arielbs.github.io/BenSassonORCID/**
- [x] Marked complete, final commit.

## Status: COMPLETE (2026-07-21)

Live page: https://arielbs.github.io/BenSassonORCID/ — 15 papers, 712 citations,
two eras, cumulative-citation chart, light/dark toggle. Regenerate anytime with
`python -X utf8 fetch_papers.py && python -X utf8 build_page.py`.

## Enhancements (post-launch, 2026-07-21)

- Citation chart: overlay independent cumulative curves for the two most-cited
  papers; each curve starts at its publication year (no misleading pre-pub zeros).
- New **Publications scatter** (x=year, y=citations) colored by research program
  (organic electronics vs protein design). Dots are clickable → compact info box.
- New **Co-authors scatter** (x=first collaboration year, y=papers together,
  size=papers) colored by institution (OpenAlex institution = proxy for lab).
  Clickable dots. Needed new fetch fields: `field`/`topic`, per-author
  `institutions` — see `fetch_papers.py`.
- Design-quality pass using the `dataviz` skill: ran its colorblind-safety
  validator (palette passes all six checks, light + dark); added surface rings on
  scatter marks, x-axis titles, recessive gridlines; refined stat cards, header
  pills, card hover, elevation, and type scale.
- Automation: `.github/workflows/update-page.yml` — GitHub Actions, weekly
  (Fridays 15:00 UTC ≈ 08:00 Seattle) + manual `workflow_dispatch`. Re-runs `fetch_papers.py`
  and `build_page.py`, commits `index.html`/`papers.json`/`papers.csv` only if
  changed (no empty commits); push to `main` triggers a Pages rebuild. Uses
  workflow-scoped `contents: write`; stdlib-only so no dependency install.
  Verified with a manual run (2026-07-21): all steps green, "no changes"
  reported as expected.
- Name guard (2026-07-22): `fetch_papers.py` derives your surname from your
  OpenAlex author record and holds out any returned work whose author list does
  NOT contain your name (catches OpenAlex mis-links — a wrong-person paper keeps
  the ORCID but not the name). Held-out works go to `flagged_works.txt` (tracked)
  instead of the page; `confirmed_mine.txt` is an allowlist to force-include a
  false positive. The workflow surfaces any held-out works as a `::warning::`
  and a run-summary block. Unit-tested: real paper kept, "Malcolm MacCoss"-style
  mis-link held out, name-spelling variants still match.

## Design decisions (from interview 2026-07-21)

- **Style:** lab / technical — data-forward, mono accents, restrained.
- **Accent:** deep blue (works in light + dark).
- **Theme:** light/dark **toggle**, respects system pref, remembers choice.
- **Header:** name "Ariel J. Ben-Sasson" + a short intro sentence spanning
  organic electronics → designed protein materials. Links: **ORCID**,
  **Google Scholar** (need URL from Ariel — omit if not provided), **GitHub**
  (github.com/Arielbs).
- **Stat cards:** Years active (2009–2025), plus Publications (15) and Total
  citations (712) as core numbers.
- **Primary chart:** cumulative citations over time (area). Uses OpenAlex
  yearly counts (2012+); footnote notes pre-2012 citations are in the lifetime
  total but not broken out by year.
- **Second chart:** none.
- **Papers:** two eras, newest-first within each —
  "Protein materials design (2021–2025)" and
  "Organic electronics & device physics (2009–2015)".
  Each card: **title links to DOI**, venue + year, citation count, co-authors
  (Ariel highlighted). Nature 2021 paper gets a subtle "most cited" badge.
- **Footer:** data source OpenAlex, built with Claude, last-updated date.

## Build approach

- Single self-contained `index.html` at repo root (what GitHub Pages serves).
- No external libraries/CDNs: charts drawn as inline SVG, vanilla JS.
- Paper data embedded inline from `papers.json` so the page also works opened
  locally (file://) for review.
- Generated by a reusable `build_page.py` (reads papers.json → writes
  index.html), so the page can be regenerated after a re-fetch.
