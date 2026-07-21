#!/usr/bin/env python3
"""Build index.html for the publications page from papers.json.

Reusable: re-run after fetch_papers.py to regenerate the page with fresh data.

Run with:  python -X utf8 build_page.py
"""
import datetime
import html
import json
import math

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
# categorical palette (readable on both light and dark panels)
PALETTE = ["#1668b0", "#d97706", "#0f9d9d", "#7c3aed", "#c02662",
           "#2ca24c", "#b45309", "#0891b2"]
# Okabe-Ito colorblind-safe palette for the co-authorship network (validated
# all-pairs with dataviz/scripts/validate_palette.js: normal-vision floor 15.6,
# CVD in the legal band given the graph's spatial + label secondary encoding).
# Order chosen so ranks 2 (Technion, amber) and 6 (Tel Aviv, sky) — the two
# institutions that share the organic-electronics cluster — get the most
# distinct hues rather than the two warm ones.
NET_PALETTE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9"]

def force_layout(n, edges, W, H, iters=700):
    """Deterministic force-directed layout, computed server-side so the graph
    renders as plain SVG (no JavaScript needed). Returns list of (x, y).

    Model: capped repulsion between all nodes + springs on edges (which also
    push apart when closer than the rest length) + light gravity + speed cap +
    in-bounds clamp. Disconnected communities separate into distinct clusters."""
    m = 30
    x0, y0, x1, y1 = m, m, W - m, H - m
    bw, bh, cx, cy = x1 - x0, y1 - y0, W / 2, H / 2
    GA = 2.399963229  # golden angle → even initial spread, no stacking
    px, py, vx, vy = [], [], [0.0] * n, [0.0] * n
    for i in range(n):
        rad = math.sqrt((i + 0.5) / n)
        px.append(cx + math.cos(i * GA) * rad * bw * 0.48)
        py.append(cy + math.sin(i * GA) * rad * bh * 0.48)
    kRep, fMax, Ld, damp, vmax, grav = 2700.0, 52.0, 52.0, 0.9, 16.0, 0.004
    for it in range(iters):
        cool = 1 - (it / iters) * 0.55
        for i in range(n):
            for j in range(i + 1, n):
                dx, dy = px[i] - px[j], py[i] - py[j]
                d = math.hypot(dx, dy) or 0.1
                dd = 8.0 if d < 8 else d
                f = kRep / (dd * dd)
                if f > fMax:
                    f = fMax
                ux, uy = dx / d, dy / d
                vx[i] += f * ux; vy[i] += f * uy
                vx[j] -= f * ux; vy[j] -= f * uy
        for e in edges:
            a, b, w = e["s"], e["t"], e["w"]
            dx, dy = px[b] - px[a], py[b] - py[a]
            d = math.hypot(dx, dy) or 0.1
            ux, uy = dx / d, dy / d
            f = 0.02 * (d - Ld) * (1 + (w - 1) * 0.5)
            vx[a] += f * ux; vy[a] += f * uy
            vx[b] -= f * ux; vy[b] -= f * uy
        for i in range(n):
            vx[i] += (cx - px[i]) * grav
            vy[i] += (cy - py[i]) * grav
            vx[i] *= damp; vy[i] *= damp
            sp = math.hypot(vx[i], vy[i])
            if sp > vmax:
                vx[i] *= vmax / sp; vy[i] *= vmax / sp
            px[i] += vx[i] * cool; py[i] += vy[i] * cool
            px[i] = min(max(px[i], x0), x1)
            py[i] = min(max(py[i], y0), y1)
    return list(zip(px, py))

ERAS = [
    ("Protein materials design", "2021–2025", lambda y: y and y >= 2020),
    ("Organic electronics & device physics", "2009–2015", lambda y: y and y < 2020),
]


def is_me(author):
    a = author.lower()
    return "ben" in a and "sasson" in a


def esc(s):
    return html.escape(str(s or ""))


def cumulative(counts_by_year, full):
    """Cumulative running total over the given list of years."""
    cum, running = [], 0
    for yr in full:
        running += (counts_by_year or {}).get(yr, 0) or (counts_by_year or {}).get(str(yr), 0)
        cum.append(running)
    return cum


def build_chart(works, accent, highlights=None):
    """Cumulative-citations chart: total area + optional per-paper lines.

    highlights: list of dicts {"label", "color", "work"} to overlay as their
    own independent cumulative curves.
    """
    highlights = highlights or []
    per_year = {}
    for p in works:
        for y, c in (p.get("counts_by_year") or {}).items():
            per_year[int(y)] = per_year.get(int(y), 0) + c
    if not per_year:
        return "<p>No yearly citation data.</p>", "", 0
    years = sorted(per_year)
    # fill gaps
    full = list(range(years[0], years[-1] + 1))
    cum = cumulative(per_year, full)
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

    # per-paper overlay curves (independent cumulative totals)
    overlays = []
    legend_items = [(accent, "All papers (total)")]
    for h in highlights:
        hc = cumulative(h["work"].get("counts_by_year"), full)
        # start the curve at the paper's publication year — before it existed,
        # a "0 citations" segment would be misleading.
        pub = h["work"].get("year") or full[0]
        start = next((i for i, yr in enumerate(full) if yr >= pub), 0)
        hpts = [(x(i), y(hc[i])) for i in range(start, n)]
        hline = " ".join(f"{px:.1f},{py:.1f}" for px, py in hpts)
        color = h["color"]
        overlays.append(
            f'<polyline points="{hline}" fill="none" stroke="{color}" '
            f'stroke-width="2"/>' +
            f'<circle cx="{hpts[-1][0]:.1f}" cy="{hpts[-1][1]:.1f}" r="3" fill="{color}"/>')
        legend_items.append((color, h["label"]))

    svg = f'''<svg viewBox="0 0 {W} {H}" class="chart" role="img"
     aria-label="Cumulative citations from {full[0]} to {full[-1]}, total and top two papers">
  <defs>
    <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{accent}" stop-opacity="0.30"/>
      <stop offset="100%" stop-color="{accent}" stop-opacity="0.02"/>
    </linearGradient>
  </defs>
  {''.join(ylabels)}
  <path d="{area}" fill="url(#fill)"/>
  <polyline points="{line}" fill="none" stroke="{accent}" stroke-width="2.5"/>
  <circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="3" fill="{accent}"/>
  {''.join(overlays)}
  {''.join(xlabels)}
</svg>'''

    legend = '<div class="legend">' + "".join(
        f'<span class="lg"><span class="sw" style="background:{c}"></span>{esc(lbl)}</span>'
        for c, lbl in legend_items) + '</div>'
    return svg, legend, cum[-1]


def _axes(ml, mt, pw, ph, xmin, xmax, ymax, xticks, ylab_fmt=str):
    """Shared gridlines + axis labels for a scatter plot."""
    out = []
    for s in range(5):
        v = ymax * s / 4
        gy = mt + ph - ph * (v / ymax if ymax else 0)
        out.append(f'<line x1="{ml}" y1="{gy:.1f}" x2="{ml+pw}" y2="{gy:.1f}" class="grid"/>'
                   f'<text x="{ml-8}" y="{gy+4:.1f}" class="ylab" text-anchor="end">{ylab_fmt(round(v))}</text>')
    for xv in xticks:
        gx = ml + pw * (xv - xmin) / (xmax - xmin) if xmax > xmin else ml + pw / 2
        out.append(f'<text x="{gx:.1f}" y="{mt+ph+22:.0f}" class="xlab" text-anchor="middle">{xv}</text>')
    return "".join(out)


def _legend(items):
    return '<div class="legend">' + "".join(
        f'<span class="lg"><span class="dot" style="background:{c}"></span>{esc(l)}</span>'
        for c, l in items) + '</div>'


def research_program(p):
    """Split the corpus into the two research programs."""
    return "Protein design" if (p.get("year") and p["year"] >= 2020) \
        else "Organic electronics"


def build_pub_scatter(works):
    """Scatter of publications: x=year, y=citations, colored by research
    program (organic electronics vs protein design). Dots are clickable."""
    color_of = {"Organic electronics": "#0f9d9d", "Protein design": "#d97706"}

    W, H = 720, 340
    ml, mr, mt, mb = 52, 16, 16, 40
    pw, ph = W - ml - mr, H - mt - mb
    years = [p["year"] for p in works if p["year"]]
    xmin, xmax = min(years), max(years)
    ymax = max((p["cited_by_count"] for p in works), default=1) or 1
    ymax = ((ymax // 25) + 1) * 25  # round up to nice number

    def X(yr):
        return ml + pw * (yr - xmin) / (xmax - xmin) if xmax > xmin else ml + pw / 2

    def Y(c):
        return mt + ph - ph * (c / ymax)

    xticks = list(range(xmin, xmax + 1, 2))
    dots = []
    for p in works:
        if not p["year"]:
            continue
        prog = research_program(p)
        c = color_of[prog]
        cx, cy = X(p["year"]), Y(p["cited_by_count"])
        sub = f'{p["year"]} · {p.get("venue") or ""} · {p["cited_by_count"]} cites'
        dots.append(
            f'<circle class="node" cx="{cx:.1f}" cy="{cy:.1f}" r="6.5" fill="{c}" '
            f'fill-opacity="0.9" '
            f'data-title="{esc(p["title"])}" data-sub="{esc(sub)}">'
            f'<title>{esc(p["title"])} ({p["year"]})</title></circle>')

    svg = f'''<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Publications by year and citations, colored by research program">
  {_axes(ml, mt, pw, ph, xmin, xmax, ymax, xticks)}
  <text x="13" y="{mt+ph/2:.0f}" class="axtitle" transform="rotate(-90 13 {mt+ph/2:.0f})" text-anchor="middle">citations</text>
  <text x="{ml+pw/2:.0f}" y="{H-3}" class="axtitle" text-anchor="middle">year</text>
  {''.join(dots)}
</svg>'''
    order = ["Organic electronics", "Protein design"]
    return svg, _legend([(color_of[k], k) for k in order])


def build_coauthor_graph(works, palette):
    """Co-authorship network: nodes = co-authors (sized by shared papers with
    Ariel, colored by institution), edges = pairs of co-authors weighted by how
    many papers they share. Positions are solved by a force layout in-browser;
    here we just emit the node/edge data + an empty <svg> for the JS to fill."""
    from collections import Counter, defaultdict
    n_papers = Counter()
    insts = defaultdict(Counter)
    first_year = {}
    pair = Counter()
    for p in works:
        yr = p["year"]
        names = [a["name"] for a in p.get("authorships", []) if not is_me(a["name"])]
        for a in p.get("authorships", []):
            nm = a["name"]
            if is_me(nm):
                continue
            n_papers[nm] += 1
            for inst in a.get("institutions", []):
                insts[nm][inst] += 1
            if yr:
                first_year[nm] = min(first_year.get(nm, 9999), yr)
        uniq = sorted(set(names))
        for i in range(len(uniq)):
            for j in range(i + 1, len(uniq)):
                pair[(uniq[i], uniq[j])] += 1

    def lab_of(nm):
        return insts[nm].most_common(1)[0][0] if insts[nm] else "Unspecified"

    lab_count = Counter(lab_of(nm) for nm in n_papers)
    ranked = [l for l, _ in lab_count.most_common() if l != "Unspecified"]
    top_labs = ranked[:6]
    # Always name Tel Aviv University if present (Ariel's early collaborators),
    # even if it ties out of the top 6 by count.
    TAU = "Tel Aviv University"
    if TAU in ranked and TAU not in top_labs:
        top_labs = top_labs[:5] + [TAU]
    color_of = {l: palette[i % len(palette)] for i, l in enumerate(top_labs)}
    other_color = "#8a94a6"

    def surname(nm):
        parts = nm.replace("‐", "-").replace("‑", "-").split()
        return parts[-1] if parts else nm

    names_sorted = sorted(n_papers, key=lambda nm: (-n_papers[nm], nm))
    id_of = {nm: i for i, nm in enumerate(names_sorted)}
    nodes = []
    for nm in names_sorted:
        cnt = n_papers[nm]
        lab = lab_of(nm)
        yr = first_year.get(nm)
        nodes.append({
            "id": id_of[nm],
            "label": nm,
            "short": surname(nm),
            "sub": f'{cnt} paper{"s" if cnt > 1 else ""} together · {lab}'
                   + (f' · since {yr}' if yr and yr != 9999 else ''),
            "color": color_of.get(lab, other_color),
            "r": round(4 + cnt * 1.7, 1),
            "big": cnt >= 2,
        })
    edges = [{"s": id_of[a], "t": id_of[b], "w": w} for (a, b), w in pair.items()]

    legend_items = [(color_of[l], l) for l in top_labs]
    if any(lab_of(nm) not in top_labs for nm in n_papers):
        legend_items.append((other_color, "Other institutions"))

    # Solve the layout here (server-side) and bake positions into static SVG,
    # so the network renders without any JavaScript.
    W, H = 720, 470
    pos = force_layout(len(nodes), edges, W, H)

    edge_svg = []
    for e in edges:
        ax, ay = pos[e["s"]]
        bx, by = pos[e["t"]]
        w = e["w"]
        edge_svg.append(
            f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
            f'class="edge" stroke-width="{0.5 + w * 0.9:.2f}" '
            f'stroke-opacity="{min(0.65, 0.16 + w * 0.14):.2f}"/>')

    node_svg = []
    label_svg = []
    for nd in nodes:
        x, y = pos[nd["id"]]
        node_svg.append(
            f'<circle class="node" cx="{x:.1f}" cy="{y:.1f}" r="{nd["r"]}" '
            f'fill="{nd["color"]}" fill-opacity="0.92" '
            f'data-title="{esc(nd["label"])}" data-sub="{esc(nd["sub"])}">'
            f'<title>{esc(nd["label"])}</title></circle>')
        if nd["big"]:
            label_svg.append(
                f'<text class="netlab" x="{x:.1f}" y="{y - nd["r"] - 4:.1f}" '
                f'text-anchor="middle">{esc(nd["short"])}</text>')

    svg = (f'<svg class="chart net" viewBox="0 0 {W} {H}" role="img" '
           'aria-label="Co-authorship network graph">'
           + "".join(edge_svg) + "".join(node_svg) + "".join(label_svg)
           + '</svg>')
    return svg, _legend(legend_items), len(nodes), len(edges)


def paper_card(p, badge_labels=None):
    labels = badge_labels or []
    if isinstance(labels, str):
        labels = [labels]
    featured = bool(labels)
    doi = p.get("url") or p.get("doi") or ""
    title = esc(p["title"])
    title_html = f'<a href="{esc(doi)}" target="_blank" rel="noopener">{title}</a>' if doi else title
    authors = " · ".join(
        (f'<span class="me">{esc(a)}</span>' if is_me(a) else esc(a))
        for a in p.get("authors", []))
    badges = "".join(f'<span class="badge">{esc(l)}</span>' for l in labels)
    badge_row = f'<div class="badges">{badges}</div>' if badges else ""
    venue = esc(p["venue"])
    return f'''<article class="card{' featured' if featured else ''}">
  <div class="card-head">
    <h3>{title_html}</h3>
    <span class="cites" title="citations">{p['cited_by_count']}</span>
  </div>
  {badge_row}
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

    # Featured papers -> list of badge labels
    featured_labels = {most["id"]: ["most cited", "first de novo macro-scale material"]}
    first_paper = next(
        (p for p in works if p["title"].startswith(
            "Patterned electrode vertical field effect transistor fabricated")),
        None)
    if first_paper:
        featured_labels[first_paper["id"]] = ["first vertical OFET"]

    # two most-cited papers -> independent overlay curves
    top2 = sorted(works, key=lambda p: p["cited_by_count"], reverse=True)[:2]
    overlay_colors = ["#d97706", "#0f9d9d"]  # amber, teal (readable in both themes)

    def short(p):
        t = p["title"]
        if t.startswith("Design of biologically active binary protein"):
            return "2D protein materials · Nature 2021"
        if t.startswith("Patterned electrode vertical field effect transistor fabricated"):
            return "Vertical OFET · APL 2009"
        return f"{t[:28]}… · {p['year']}"

    highlights = [
        {"label": f"{short(p)} ({p['cited_by_count']})",
         "color": overlay_colors[i], "work": p}
        for i, p in enumerate(top2)]
    chart_svg, chart_legend, _ = build_chart(works, ACCENT, highlights)
    pub_svg, pub_legend = build_pub_scatter(works)
    co_svg, co_legend, n_coauthors, n_edges = build_coauthor_graph(works, NET_PALETTE)

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
    --accent:{ACCENT}; --accent-soft:#eaf2fb;
    --bg:#f4f6f9; --panel:#ffffff; --panel-2:#fafbfd; --ink:#111722;
    --muted:#5b6572; --line:#e5e9f0; --hair:#eef1f6; --me:#0d3b66;
    --shadow:0 1px 2px rgba(16,24,40,.04),0 8px 24px rgba(16,24,40,.06);
    --shadow-lift:0 2px 6px rgba(16,24,40,.08),0 16px 40px rgba(16,24,40,.10);
    --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
    --sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  }}
  html[data-theme="dark"]{{
    --accent:{ACCENT_DARK}; --accent-soft:#12283f;
    --bg:#0b0e13; --panel:#161b23; --panel-2:#1b212b; --ink:#e8ecf2;
    --muted:#9aa5b4; --line:#273040; --hair:#1e2530; --me:#8fc4f0;
    --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
    --shadow-lift:0 2px 8px rgba(0,0,0,.4),0 18px 44px rgba(0,0,0,.5);
  }}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);
    line-height:1.55;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}}
  .wrap{{max-width:840px;margin:0 auto;padding:52px 24px 80px}}
  a{{color:var(--accent);text-decoration:none}}
  a:hover{{text-decoration:underline}}
  header.top{{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;
    padding-bottom:26px;border-bottom:1px solid var(--line)}}
  h1{{font-size:2.15rem;margin:0 0 8px;letter-spacing:-.025em;line-height:1.1}}
  .affil{{font-family:var(--mono);font-size:.76rem;color:var(--accent);
    text-transform:uppercase;letter-spacing:.12em;margin-bottom:12px}}
  .intro{{color:var(--muted);max-width:62ch;margin:0 0 18px;font-size:1.02rem}}
  .links{{font-family:var(--mono);font-size:.8rem;display:flex;gap:9px;flex-wrap:wrap}}
  .links a{{border:1px solid var(--line);border-radius:999px;padding:5px 13px;
    color:var(--ink);background:var(--panel);transition:all .12s}}
  .links a:hover{{text-decoration:none;border-color:var(--accent);color:var(--accent);
    box-shadow:var(--shadow)}}
  .toggle{{flex:none;font-family:var(--mono);font-size:.78rem;cursor:pointer;
    background:var(--panel);border:1px solid var(--line);color:var(--ink);
    border-radius:999px;padding:7px 14px;transition:all .12s}}
  .toggle:hover{{border-color:var(--accent);color:var(--accent);box-shadow:var(--shadow)}}
  .stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:32px 0 4px}}
  .stat{{position:relative;background:var(--panel);border:1px solid var(--line);
    border-radius:14px;padding:20px 20px 18px;box-shadow:var(--shadow);
    transition:transform .14s,box-shadow .14s;overflow:hidden}}
  .stat::before{{content:"";position:absolute;top:0;left:0;width:100%;height:3px;
    background:var(--accent);opacity:.85}}
  .stat:hover{{transform:translateY(-2px);box-shadow:var(--shadow-lift)}}
  .stat .num{{font-family:var(--mono);font-size:2.05rem;font-weight:600;color:var(--ink);
    letter-spacing:-.03em;font-variant-numeric:tabular-nums}}
  .stat .lbl{{font-family:var(--mono);font-size:.7rem;text-transform:uppercase;
    letter-spacing:.11em;color:var(--muted);margin-top:6px}}
  .panel{{background:var(--panel);border:1px solid var(--line);border-radius:16px;
    padding:24px;margin:24px 0;box-shadow:var(--shadow)}}
  .panel h2{{font-size:.82rem;font-family:var(--mono);text-transform:uppercase;
    letter-spacing:.1em;color:var(--ink);margin:0 0 14px;font-weight:600}}
  .legend{{display:flex;flex-wrap:wrap;gap:8px 18px;margin:0 2px 14px;
    font-family:var(--mono);font-size:.75rem;color:var(--muted)}}
  .legend .lg{{display:inline-flex;align-items:center;gap:6px}}
  .legend .sw{{width:16px;height:3px;border-radius:2px;display:inline-block}}
  .legend .dot{{width:10px;height:10px;border-radius:50%;display:inline-block;
    outline:2px solid var(--panel);outline-offset:-1px}}
  .chart{{width:100%;height:auto;display:block;overflow:visible}}
  .chart circle{{transition:fill-opacity .1s}}
  .chart .node{{cursor:pointer;stroke:var(--panel);stroke-width:1.5;paint-order:stroke}}
  .chart .node:hover{{fill-opacity:1;stroke:var(--ink);stroke-width:1.5}}
  .chart .node.sel{{stroke:var(--ink);stroke-width:2}}
  .popup{{position:fixed;z-index:50;max-width:280px;background:var(--panel);
    border:1px solid var(--line);border-left:3px solid var(--accent);
    border-radius:10px;padding:10px 12px;box-shadow:var(--shadow-lift);
    display:none;pointer-events:none}}
  .popup .pt{{font-size:.82rem;font-weight:600;line-height:1.32;color:var(--ink)}}
  .popup .ps{{font-family:var(--mono);font-size:.68rem;color:var(--muted);margin-top:5px}}
  .chart .grid{{stroke:var(--hair);stroke-width:1}}
  .chart .ylab,.chart .xlab{{fill:var(--muted);font-family:var(--mono);font-size:11px}}
  .chart .axtitle{{fill:var(--muted);font-family:var(--mono);font-size:10.5px;
    text-transform:uppercase;letter-spacing:.08em}}
  .chart.net{{min-height:340px}}
  .chart .edge{{stroke:var(--muted);stroke-linecap:round}}
  .chart .netlab{{fill:var(--ink);font-family:var(--mono);font-size:10px;
    paint-order:stroke;stroke:var(--panel);stroke-width:3px;pointer-events:none}}
  .note{{font-size:.79rem;color:var(--muted);margin:12px 2px 0;line-height:1.5;max-width:70ch}}
  .era{{margin-top:44px}}
  .era-head{{display:flex;align-items:baseline;gap:12px;border-bottom:2px solid var(--accent);
    padding-bottom:9px;margin-bottom:4px}}
  .era-head h2{{font-size:1.22rem;margin:0;letter-spacing:-.01em}}
  .era-sub{{font-family:var(--mono);font-size:.74rem;color:var(--muted)}}
  .card{{border-bottom:1px solid var(--hair);padding:16px 10px;margin:0 -10px;
    border-radius:10px;transition:background .12s}}
  .card:hover{{background:var(--panel-2)}}
  .card:last-child{{border-bottom:0}}
  .card.featured{{background:linear-gradient(95deg,var(--accent-soft),transparent 70%)}}
  .card.featured:hover{{background:linear-gradient(95deg,var(--accent-soft),var(--panel-2) 80%)}}
  .card-head{{display:flex;justify-content:space-between;gap:14px;align-items:baseline}}
  .card h3{{font-size:1.04rem;font-weight:600;margin:0;line-height:1.36}}
  .card h3 a{{color:var(--ink)}}
  .card h3 a:hover{{color:var(--accent)}}
  .badges{{display:flex;flex-wrap:wrap;gap:6px;margin:7px 0 0}}
  .badge{{font-family:var(--mono);font-size:.6rem;text-transform:uppercase;
    letter-spacing:.07em;background:var(--accent);color:#fff;border-radius:5px;
    padding:3px 8px;white-space:nowrap;font-weight:600}}
  .cites{{font-family:var(--mono);font-size:1.08rem;font-weight:600;color:var(--accent);
    flex:none;font-variant-numeric:tabular-nums}}
  .cites::after{{content:" cites";font-size:.6rem;color:var(--muted);font-weight:400}}
  .meta{{font-family:var(--mono);font-size:.79rem;color:var(--muted);margin:6px 0 7px;
    display:flex;gap:10px;flex-wrap:wrap}}
  .meta .year::before{{content:"· "}}
  .authors{{font-size:.86rem;color:var(--muted);line-height:1.5}}
  .authors .me{{color:var(--me);font-weight:600}}
  footer{{margin-top:52px;padding-top:20px;border-top:1px solid var(--line);
    font-family:var(--mono);font-size:.74rem;color:var(--muted);line-height:1.7}}
  @media(max-width:560px){{.stats{{grid-template-columns:1fr}}
    .wrap{{padding:36px 18px 64px}} h1{{font-size:1.8rem}}
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
  <div class="popup" id="popup"><div class="pt"></div><div class="ps"></div></div>

  <div class="stats">
    <div class="stat"><div class="num">{span}</div><div class="lbl">Years active</div></div>
    <div class="stat"><div class="num">{n_pubs}</div><div class="lbl">Publications</div></div>
    <div class="stat"><div class="num">{total_cites}</div><div class="lbl">Total citations</div></div>
  </div>

  <div class="panel">
    <h2>Cumulative citations over time</h2>
    {chart_legend}
    {chart_svg}
    <p class="note">Solid blue is the running total across all papers; the amber
      and teal lines are the independent cumulative citations of the two
      most-cited papers, on the same axis.
      Yearly citation data from OpenAlex begins ~2012. Citations
      earned before 2012 are included in the total above but not broken out by
      year, so the early curve is conservative.</p>
  </div>

  <div class="panel">
    <h2>Publications by research program &amp; year</h2>
    {pub_legend}
    {pub_svg}
    <p class="note">Each dot is a paper — horizontal by year, vertical by total
      citations, colored by research program (organic electronics vs protein
      design). <strong>Click any dot</strong> for its title and year.</p>
  </div>

  <div class="panel">
    <h2>Co-authorship network</h2>
    {co_legend}
    {co_svg}
    <p class="note">A force-directed graph of your {n_coauthors} co-authors
      ({n_edges} co-authorship links). Each node is a collaborator — sized by how
      many papers you share, colored by their institution (proxy for lab). An
      edge joins two co-authors who appear together on a paper, and is thicker the
      more papers they share; the layout pulls frequent collaborators together, so
      your distinct research communities settle into separate clusters.
      <strong>Click any node</strong> for the name.</p>
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

    // click a scatter node -> compact info box with title + year
    var popup=document.getElementById('popup');
    var pt=popup.querySelector('.pt'), ps=popup.querySelector('.ps'), cur=null;
    function hide(){{popup.style.display='none';if(cur){{cur.classList.remove('sel');cur=null;}}}}
    document.addEventListener('click',function(e){{
      var node=e.target.closest && e.target.closest('.node');
      if(!node){{hide();return;}}
      e.stopPropagation();
      if(cur) cur.classList.remove('sel');
      cur=node; node.classList.add('sel');
      pt.textContent=node.getAttribute('data-title')||'';
      ps.textContent=node.getAttribute('data-sub')||'';
      var r=node.getBoundingClientRect();
      popup.style.display='block';
      var pw=popup.offsetWidth, ph=popup.offsetHeight;
      var left=r.left+r.width/2-pw/2;
      left=Math.max(8,Math.min(left,window.innerWidth-pw-8));
      var top=r.top-ph-10;
      if(top<8) top=r.bottom+10;
      popup.style.left=left+'px';
      popup.style.top=top+'px';
    }});
    window.addEventListener('scroll',hide,true);
    window.addEventListener('resize',hide);
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
