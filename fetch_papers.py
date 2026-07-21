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
"""
import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ORCID = sys.argv[1] if len(sys.argv) > 1 else "0000-0003-3395-6327"
MAILTO = "arielbs10@gmail.com"  # polite pool: faster, nicer to OpenAlex
EXCLUSIONS_FILE = "excluded_works.txt"
API = "https://api.openalex.org/works"


def load_exclusions():
    if not os.path.exists(EXCLUSIONS_FILE):
        return set()
    out = set()
    with open(EXCLUSIONS_FILE, encoding="utf-8") as f:
        for line in f:
            s = line.split("#", 1)[0].strip()  # drop inline comments
            if not s:
                continue
            token = s.split()[0]  # id/DOI is the first token
            out.add(token.rstrip("/").split("/")[-1].lower())
    return out


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
    excl = load_exclusions()
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

    with open("papers.json", "w", encoding="utf-8") as f:
        json.dump(works, f, ensure_ascii=False, indent=2)

    with open("papers.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["title", "year", "venue", "type", "cited_by_count", "authors"])
        for p in works:
            w.writerow([p["title"], p["year"], p["venue"], p["type"],
                        p["cited_by_count"], "; ".join(p["authors"])])

    # Summary
    total_cites = sum(p["cited_by_count"] for p in works)
    by_type = {}
    for p in works:
        by_type[p["type"]] = by_type.get(p["type"], 0) + 1
    print(f"\nSaved {len(works)} works to papers.json and papers.csv")
    print(f"Total citations: {total_cites}")
    print("By type:")
    for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {t:14s} {n}")


if __name__ == "__main__":
    main()
