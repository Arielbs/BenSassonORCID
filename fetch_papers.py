#!/usr/bin/env python3
"""Fetch a researcher's works from OpenAlex by ORCID.

Saves:
  - papers.json : full structured list (title, year, venue, type, DOI/URL,
                  citations, counts_by_year, authors)
  - papers.csv  : a skimmable spreadsheet (title, year, venue, type, cites,
                  co-authors) for eyeballing that the list is really yours

Run with:  python -X utf8 fetch_papers.py [ORCID]

Handles OpenAlex rate limiting (HTTP 429) by pausing and retrying instead of
failing. Reads an optional exclusions file (excluded_works.txt, one OpenAlex
work id or DOI per line) so a re-run drops the same papers again.

Name guard: OpenAlex can mis-link another researcher's paper to your ORCID. Such
a paper carries your ORCID but NOT your name, so every fetched work is checked
for your surname (derived from your OpenAlex author record) in its author list;
any that lack it are held out of papers.json and reported in flagged_works.txt.
An allowlist (confirmed_mine.txt) can force-include a genuine paper that fails.
"""
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ORCID = sys.argv[1] if len(sys.argv) > 1 else "0000-0003-3395-6327"
MAILTO = "arielbs10@gmail.com"  # polite pool: faster, nicer to OpenAlex
EXCLUSIONS_FILE = "excluded_works.txt"
CONFIRMED_FILE = "confirmed_mine.txt"   # allowlist: force-include these ids
FLAGGED_FILE = "flagged_works.txt"      # report: works held out by the name guard
AUTHORS_API = "https://api.openalex.org/authors"
API = "https://api.openalex.org/works"


def load_id_file(path):
    """Read a file of OpenAlex work ids / DOIs (one per line, inline # comments
    allowed) into a lowercased set of bare ids."""
    if not os.path.exists(path):
        return set()
    out = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.split("#", 1)[0].strip()
            if not s:
                continue
            out.add(s.split()[0].rstrip("/").split("/")[-1].lower())
    return out


def surname_tokens(orcid):
    """Derive the author's surname sub-tokens from their OpenAlex record, so the
    name guard works for any ORCID (not just a hardcoded name). E.g. "Ariel J.
    Ben-Sasson" -> {"ben", "sasson"}. Returns an empty set if it can't tell,
    in which case the guard is skipped rather than flagging everything."""
    try:
        d = get(f"{AUTHORS_API}/https://orcid.org/{orcid}?mailto={MAILTO}")
    except SystemExit:
        return set()
    name = d.get("display_name") or ""
    if not name:
        return set()
    # surname = the last whitespace token; split compound names on hyphens/dots
    last = name.strip().split()[-1]
    toks = {t for t in re.split(r"[-‐‑–—.\s]+", last.lower()) if len(t) >= 2 and t.isalpha()}
    return toks


def name_is_author(authorships, toks):
    """True if any author's name contains all of the surname sub-tokens."""
    if not toks:
        return True  # can't check -> don't flag
    for a in authorships:
        low = (a.get("name") or "").lower()
        if all(t in low for t in toks):
            return True
    return False


def get(url, tries=6):
    """GET with retry/backoff on 429 (rate limit) and transient errors."""
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": f"pubs-page ({MAILTO})"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 2 ** attempt
                print(f"  rate limited (429), waiting {wait}s and retrying...", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
        except urllib.error.URLError:
            wait = 2 ** attempt
            print(f"  network hiccup, waiting {wait}s and retrying...", file=sys.stderr)
            time.sleep(wait)
    raise SystemExit("OpenAlex kept failing after retries; try again later.")


def fetch_all():
    excl = load_id_file(EXCLUSIONS_FILE)
    filt = f"author.orcid:{ORCID}"
    cursor = "*"
    works = []
    while cursor:
        params = urllib.parse.urlencode({
            "filter": filt,
            "per-page": 200,
            "cursor": cursor,
            "mailto": MAILTO,
        })
        data = get(f"{API}?{params}")
        for w in data["results"]:
            wid = (w.get("id") or "").rstrip("/").split("/")[-1].lower()
            doi = (w.get("doi") or "").rstrip("/").split("/")[-1].lower()
            if wid in excl or (doi and doi in excl):
                continue
            loc = w.get("primary_location") or {}
            src = (loc.get("source") or {}) if loc else {}
            authors = [a["author"]["display_name"] for a in w.get("authorships", [])]
            # per-author institutions (best available proxy for "lab")
            authorships = []
            for a in w.get("authorships", []):
                insts = [i.get("display_name") for i in a.get("institutions", []) if i.get("display_name")]
                authorships.append({
                    "name": a["author"]["display_name"],
                    "orcid": a["author"].get("orcid"),
                    "institutions": insts,
                })
            pt = w.get("primary_topic") or {}
            works.append({
                "id": wid,
                "title": w.get("title") or "(untitled)",
                "year": w.get("publication_year"),
                "date": w.get("publication_date"),
                "venue": src.get("display_name") or "",
                "type": w.get("type") or "",
                "doi": w.get("doi") or "",
                "url": w.get("doi") or (loc.get("landing_page_url") or ""),
                "cited_by_count": w.get("cited_by_count") or 0,
                "counts_by_year": {c["year"]: c["cited_by_count"]
                                   for c in w.get("counts_by_year", [])},
                "topic": pt.get("display_name") or "",
                "subfield": ((pt.get("subfield") or {}).get("display_name")) or "",
                "field": ((pt.get("field") or {}).get("display_name")) or "",
                "authors": authors,
                "authorships": authorships,
            })
        cursor = data["meta"].get("next_cursor")
        if not data["results"]:
            break
    works.sort(key=lambda x: (x["year"] or 0), reverse=True)
    return works


def main():
    print(f"Fetching works for ORCID {ORCID} from OpenAlex...")
    works = fetch_all()

    # --- Name guard: "is this really mine?" -------------------------------
    # A mis-linked wrong-person paper still carries the ORCID (that is the bug),
    # but it will NOT carry the author's name. So hold out any work where the
    # author's surname is absent from the author list. An allowlist
    # (confirmed_mine.txt) can force-include a genuine paper that fails the check
    # (e.g. an odd name spelling).
    toks = surname_tokens(ORCID)
    allow = load_id_file(CONFIRMED_FILE)
    if toks:
        print(f"Name guard: keeping works whose authors include {sorted(toks)}")
    else:
        print("Name guard: could not derive a surname from OpenAlex — guard skipped.")

    verified, flagged = [], []
    for p in works:
        if name_is_author(p["authorships"], toks) or p["id"] in allow:
            verified.append(p)
        else:
            flagged.append(p)

    with open("papers.json", "w", encoding="utf-8") as f:
        json.dump(verified, f, ensure_ascii=False, indent=2)

    with open("papers.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["title", "year", "venue", "type", "cited_by_count", "authors"])
        for p in verified:
            w.writerow([p["title"], p["year"], p["venue"], p["type"],
                        p["cited_by_count"], "; ".join(p["authors"])])

    # Write the flag report (always, so CI can read it and the file stays tracked)
    with open(FLAGGED_FILE, "w", encoding="utf-8") as f:
        f.write("# Works returned for this ORCID but HELD OUT because the "
                "author's name was not found in the author list.\n")
        f.write("# These are likely mis-attributions. To force-include a real "
                "one, add its id to confirmed_mine.txt.\n")
        f.write(f"# count: {len(flagged)}\n")
        for p in flagged:
            f.write(f"{p['id']}  # {p['year']} — {p['title'][:70]} — "
                    f"authors: {', '.join(p['authors'][:6])}\n")

    # Summary
    total_cites = sum(p["cited_by_count"] for p in verified)
    by_type = {}
    for p in verified:
        by_type[p["type"]] = by_type.get(p["type"], 0) + 1
    print(f"\nSaved {len(verified)} works to papers.json and papers.csv")
    print(f"Total citations: {total_cites}")
    print("By type:")
    for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {t:14s} {n}")
    if flagged:
        print(f"\n⚠️  {len(flagged)} work(s) HELD OUT by the name guard "
              f"(see {FLAGGED_FILE}):")
        for p in flagged:
            print(f"   - [{p['year']}] {p['title'][:60]}")
    else:
        print("\nName guard: all shown works list your name. ✓")


if __name__ == "__main__":
    main()
