#!/usr/bin/env python3
"""Build index.html for the publications page from papers.json.

Reusable: re-run after fetch_papers.py to regenerate the page with fresh data.

Run with:  python -X utf8 build_page.py
"""
import datetime
import html
import json

# --- Page config -----------------------------------------------------------
NAME = "Ariel J. Ben-Sasson"
INTRO = ("Research spanning organic electronics — pioneering the "
         "self-assembling, block-copolymer-based first vertical organic "
         "field-effect transistors — to the design of the first macro-scale "
         "binary 2D protein materials, and on to synthetic cell biology.")
AFFILIATION = "University of Washington"
ORCID_URL = "https://orcid.org/0000-0003-3395-6327"
GITHUB_URL = "https://github.com/Arielbs"
SCHOLAR_URL = "https://scholar.google.com/citations?user=JDKB-uQAAAAJ&hl=en"
ACCENT = "#1668b0"          # deep blue (light)
ACCENT_DARK = "#5aa9e6"     # deep blue (dark mode, lighter for contrast)

ERAS = [
    ("Protein materials design", "2021–2025", lambda y: y and y >= 2020),
    ("Organic electronics & device physics", "2009–2015", lambda y: y and y < 2020),
]


def is_me(author):
    a = author.lower()
    return "ben" in a and "sasson" in a


def esc(s):
    return html.escape(str(s or ""))


def build_chart(works, accent):
    """Cumulative-citations-over-time area chart as inline SVG."""
    per_year = {}
    for p in works:
        for y, c in (p.get("counts_by_year") or {}).items():
            per_year[int(y)] = per_year.get(int(y), 0) + c
    if not per_year:
        return "<p>No yearly citation data.</p>", 0
    years = sorted(per_year)
    # fill gaps
    full = list(range(years[0], years[-1] + 1))
    cum, running = [], 0
    for y in full:
        running += per_year.get(y, 0)
        cum.append(running)
    max_c = max(cum) or 1

    W, H = 720, 300
    ml, mr, mt, mb = 52, 20, 20, 40
    pw, ph = W - ml - mr, H - mt - mb
    n = len(full)

    def x(i):
        return ml + (pw * i / (n - 1) if n > 1 else pw / 2)

    def y(v):
        return mt + ph - (ph * v / max_c)

    pts = [(x(i), y(cum[i])) for i in range(n)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = f"M{ml},{mt+ph:.1f} L" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts) + \
           f" L{ml+pw:.1f},{mt+ph:.1f} Z"

    # y gridlines / labels
    ylabels = []
    steps = 4
    for s in range(steps + 1):
        v = round(max_c * s / steps)
        gy = y(v)
        ylabels.append(
            f'<line x1="{ml}" y1="{gy:.1f}" x2="{ml+pw}" y2="{gy:.1f}" class="grid"/>'
            f'<text x="{ml-8}" y="{gy+4:.1f}" class="ylab" text-anchor="end">{v}</text>')
    # x labels (every ~4 years + ends)
    xlabels = []
    idxs = sorted(set([0, n - 1] + list(range(0, n, max(1, n // 6)))))
    for i in idxs:
        xlabels.append(
            f'<text x="{x(i):.1f}" y="{mt+ph+22:.0f}" class="xlab" text-anchor="middle">{full[i]}</text>')

    svg = f'''<svg viewBox="0 0 {W} {H}" class="chart" role="img"
     aria-label="Cumulative citations from {full[0]} to {full[-1]}">
  <defs>
    <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{accent}" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="{accent}" stop-opacity="0.02"/>
    </linearGradient>
  </defs>
  {''.join(ylabels)}
  <path d="{area}" fill="url(#fill)"/>
  <polyline points="{line}" fill="none" stroke="{accent}" stroke-width="2.5"/>
  {''.join(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.6" fill="{accent}"/>' for px, py in pts)}
  {''.join(xlabels)}
</svg>'''
    return svg, cum[-1]


def paper_card(p, badge_label=None):
    featured = badge_label is not None
    doi = p.get("url") or p.get("doi") or ""
    title = esc(p["title"])
    title_html = f'<a href="{esc(doi)}" target="_blank" rel="noopener">{title}</a>' if doi else title
    authors = " · ".join(
        (f'<span class="me">{esc(a)}</span>' if is_me(a) else esc(a))
        for a in p.get("authors", []))
    badge = f'<span class="badge">{esc(badge_label)}</span>' if featured else ""
    venue = esc(p["venue"])
    return f'''<article class="card{' featured' if featured else ''}">
  <div class="card-head">
    <h3>{title_html}{badge}</h3>
    <span class="cites" title="citations">{p['cited_by_count']}</span>
  </div>
  <div class="meta"><span class="venue">{venue}</span><span class="year">{p['year']}</span></div>
  <div class="authors">{authors}</div>
</article>'''


def main():
    works = json.load(open("papers.json", encoding="utf-8"))
    total_cites = sum(p["cited_by_count"] for p in works)
    n_pubs = len(works)
    years = [p["year"] for p in works if p["year"]]
    span = f"{min(years)}–{max(years)}"
    most = max(works, key=lambda p: p["cited_by_count"])
    updated = datetime.date.today().isoformat()

    # Featured papers -> badge label
    featured_labels = {most["id"]: "most cited"}
    first_paper = next(
        (p for p in works if p["title"].startswith(
            "Patterned electrode vertical field effect transistor fabricated")),
        None)
    if first_paper:
        featured_labels[first_paper["id"]] = "first vertical OFET"

    chart_svg, _ = build_chart(works, ACCENT)

    # links
    links = [f'<a href="{ORCID_URL}" target="_blank" rel="noopener">ORCID</a>']
    if SCHOLAR_URL:
        links.append(f'<a href="{SCHOLAR_URL}" target="_blank" rel="noopener">Google Scholar</a>')
    links.append(f'<a href="{GITHUB_URL}" target="_blank" rel="noopener">GitHub</a>')
    links_html = " ".join(links)

    # era sections
    sections = []
    for label, sub, pred in ERAS:
        group = [p for p in works if pred(p["year"])]
        group.sort(key=lambda p: (p["year"] or 0, p.get("date") or ""), reverse=True)
        if not group:
            continue
        cards = "\n".join(paper_card(p, featured_labels.get(p["id"])) for p in group)
        sections.append(f'''<section class="era">
  <div class="era-head"><h2>{esc(label)}</h2><span class="era-sub">{esc(sub)} · {len(group)} papers</span></div>
  {cards}
</section>''')

    html_doc = f'''<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{esc(NAME)} — Publications</title>
<meta name="description" content="Publications and citation record of {esc(NAME)}."/>
<style>
  :root{{
    --accent:{ACCENT}; --bg:#f7f8fa; --panel:#ffffff; --ink:#14181f;
    --muted:#5b6572; --line:#e4e8ee; --badge:#eaf2fb; --me:#0d3b66;
    --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
    --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  }}
  html[data-theme="dark"]{{
    --accent:{ACCENT_DARK}; --bg:#0e1116; --panel:#171b22; --ink:#e6e9ee;
    --muted:#95a0af; --line:#262c36; --badge:#12283f; --me:#8fc4f0;
  }}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);
    line-height:1.5;-webkit-font-smoothing:antialiased}}
  .wrap{{max-width:820px;margin:0 auto;padding:40px 22px 72px}}
  a{{color:var(--accent);text-decoration:none}}
  a:hover{{text-decoration:underline}}
  header.top{{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}}
  h1{{font-size:1.9rem;margin:0 0 6px;letter-spacing:-.02em}}
  .affil{{font-family:var(--mono);font-size:.8rem;color:var(--accent);
    text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px}}
  .intro{{color:var(--muted);max-width:60ch;margin:0 0 14px}}
  .links{{font-family:var(--mono);font-size:.85rem;display:flex;gap:16px;flex-wrap:wrap}}
  .toggle{{flex:none;font-family:var(--mono);font-size:.8rem;cursor:pointer;
    background:var(--panel);border:1px solid var(--line);color:var(--ink);
    border-radius:8px;padding:8px 12px}}
  .toggle:hover{{border-color:var(--accent)}}
  .stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:30px 0 8px}}
  .stat{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px}}
  .stat .num{{font-family:var(--mono);font-size:1.9rem;font-weight:600;color:var(--accent);
    letter-spacing:-.02em}}
  .stat .lbl{{font-family:var(--mono);font-size:.72rem;text-transform:uppercase;
    letter-spacing:.09em;color:var(--muted);margin-top:4px}}
  .panel{{background:var(--panel);border:1px solid var(--line);border-radius:12px;
    padding:20px;margin:26px 0}}
  .panel h2{{font-size:.8rem;font-family:var(--mono);text-transform:uppercase;
    letter-spacing:.09em;color:var(--muted);margin:0 0 12px;font-weight:600}}
  .chart{{width:100%;height:auto;display:block}}
  .chart .grid{{stroke:var(--line);stroke-width:1}}
  .chart .ylab,.chart .xlab{{fill:var(--muted);font-family:var(--mono);font-size:11px}}
  .note{{font-size:.78rem;color:var(--muted);margin:10px 2px 0}}
  .era{{margin-top:38px}}
  .era-head{{display:flex;align-items:baseline;gap:12px;border-bottom:2px solid var(--accent);
    padding-bottom:8px;margin-bottom:6px}}
  .era-head h2{{font-size:1.15rem;margin:0}}
  .era-sub{{font-family:var(--mono);font-size:.75rem;color:var(--muted)}}
  .card{{border-bottom:1px solid var(--line);padding:16px 4px}}
  .card.featured{{background:linear-gradient(90deg,var(--badge),transparent);
    border-radius:8px;padding-left:12px}}
  .card-head{{display:flex;justify-content:space-between;gap:14px;align-items:baseline}}
  .card h3{{font-size:1.02rem;font-weight:600;margin:0;line-height:1.35}}
  .badge{{font-family:var(--mono);font-size:.62rem;text-transform:uppercase;
    letter-spacing:.06em;background:var(--accent);color:#fff;border-radius:5px;
    padding:2px 7px;margin-left:8px;vertical-align:middle}}
  .cites{{font-family:var(--mono);font-size:1.05rem;font-weight:600;color:var(--accent);flex:none}}
  .cites::after{{content:" cites";font-size:.62rem;color:var(--muted);font-weight:400}}
  .meta{{font-family:var(--mono);font-size:.8rem;color:var(--muted);margin:5px 0 6px;
    display:flex;gap:10px;flex-wrap:wrap}}
  .meta .year::before{{content:"· "}}
  .authors{{font-size:.85rem;color:var(--muted)}}
  .authors .me{{color:var(--me);font-weight:600}}
  footer{{margin-top:48px;padding-top:18px;border-top:1px solid var(--line);
    font-family:var(--mono);font-size:.75rem;color:var(--muted)}}
  @media(max-width:560px){{.stats{{grid-template-columns:1fr}}
    header.top{{flex-direction:column}}}}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div>
      <h1>{esc(NAME)}</h1>
      <div class="affil">{esc(AFFILIATION)}</div>
      <p class="intro">{esc(INTRO)}</p>
      <nav class="links">{links_html}</nav>
    </div>
    <button class="toggle" id="themeBtn" aria-label="Toggle dark mode">◐ theme</button>
  </header>

  <div class="stats">
    <div class="stat"><div class="num">{span}</div><div class="lbl">Years active</div></div>
    <div class="stat"><div class="num">{n_pubs}</div><div class="lbl">Publications</div></div>
    <div class="stat"><div class="num">{total_cites}</div><div class="lbl">Total citations</div></div>
  </div>

  <div class="panel">
    <h2>Cumulative citations over time</h2>
    {chart_svg}
    <p class="note">Yearly citation data from OpenAlex begins ~2012. Citations
      earned before 2012 are included in the total above but not broken out by
      year, so the early curve is conservative.</p>
  </div>

  {''.join(sections)}

  <footer>
    Data: <a href="https://openalex.org" target="_blank" rel="noopener">OpenAlex</a>
    · {n_pubs} works · {total_cites} citations · updated {updated} · built with Claude
  </footer>
</div>
<script>
  (function(){{
    var root=document.documentElement, btn=document.getElementById('themeBtn');
    var saved=localStorage.getItem('theme');
    if(saved){{root.setAttribute('data-theme',saved);}}
    else if(window.matchMedia&&window.matchMedia('(prefers-color-scheme:dark)').matches){{
      root.setAttribute('data-theme','dark');
    }}
    btn.addEventListener('click',function(){{
      var t=root.getAttribute('data-theme')==='dark'?'light':'dark';
      root.setAttribute('data-theme',t);
      localStorage.setItem('theme',t);
    }});
  }})();
</script>
</body>
</html>'''

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_doc)
    print(f"Wrote index.html — {n_pubs} papers, {total_cites} citations, "
          f"most cited: {most['title'][:40]}... ({most['cited_by_count']})")


if __name__ == "__main__":
    main()
