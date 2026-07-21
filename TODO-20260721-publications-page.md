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
- [ ] Design interview (~10 questions) → fold answers in here → approve.
- [ ] Build `index.html`, review in browser.
- [ ] Publish with GitHub Pages, get live URL.
- [ ] Mark complete, final commit.

## Design decisions

_(to be filled from the design interview)_
