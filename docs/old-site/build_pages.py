"""Rebuild the archived Cargo pages as responsive standalone HTML.

Usage: python3 -I build_pages.py <cargo-site-export.json> <out_pages_dir> <old_site_dir>
"""
import json, re, sys, os, html, urllib.parse
from bs4 import BeautifulSoup

src, out, root = sys.argv[1], sys.argv[2], sys.argv[3]
o = json.load(open(src))
pages = {p["project_url"]: p for p in o["pages"]}

# hash -> local image path (same layout as the image zips)
local = {}
for p in o["pages"]:
    for i in p["images"]:
        local.setdefault(i["hash"], f"../images/{p['project_url']}/{i['hash'][:8]}_{i['name']}")

# internal page names -> files ("Mii" was an old alias of the Mibby project)
alias = {"Mii": "Mibby"}
def page_href(name):
    name = alias.get(name, name)
    return f"{name}.html" if name in pages else None

def fix(content, page):
    c = content
    # Cargo's private "Icons" font glyphs -> plain Unicode
    icons = {"": "→", "": "→", "": "←", "": "⚡", "": "•"}
    c = re.sub(r"[-]︎?", lambda m: icons.get(m.group()[0], ""), c)
    # images: remote Cargo URLs -> local files, lazy-loaded
    def img(m):
        url = m.group(1)
        h = re.search(r"/i/([0-9a-f]{64})/", url)
        path = local.get(h.group(1)) if h else None
        return f'src="{path or url}" loading="lazy"'
    c = re.sub(r'data-src="([^"]+)"', img, c)
    # "{image N}" placeholders -> the page's Nth image
    def ph(m):
        n = int(m.group(1)) - 1
        imgs = page["images"]
        if 0 <= n < len(imgs):
            return f'<img src="{local[imgs[n]["hash"]]}" loading="lazy" alt="">'
        return ""
    c = re.sub(r"\{image (\d+)\}", ph, c)
    # internal links
    def link(m):
        target = page_href(m.group(1))
        return f'href="{target}"' if target else m.group(0)
    c = re.sub(r'href="([A-Za-z0-9_@-]+)"', link, c)
    c = c.replace(' rel="history"', "")
    # tag galleries by mode so slideshows can scroll sideways
    def gal(m):
        data = urllib.parse.unquote(m.group(1))
        mode = "slideshow" if '"Slideshow"' in data else "grid"
        return f'<div class="image-gallery gallery-{mode}"'
    c = re.sub(r'<div class="image-gallery" data-gallery="([^"]*)"', gal, c)
    # mark columns with no text or media as spacers (hidden on small screens)
    soup = BeautifulSoup(c, "html.parser")
    for col in soup.select("[grid-col]"):
        if not col.get_text(strip=True).replace("\xa0", "") and not col.find(["img", "iframe", "hr"]):
            col["class"] = (col.get("class") or []) + ["spacer"]
    # collapse runs of 3+ <br> that only added vertical gaps
    return re.sub(r"(?:<br\s*/?>\s*){3,}", "<br><br>", str(soup))

CSS = """
:root{--text:rgb(18,18,18);--head:#272727;--link:rgb(105,143,255);--muted:rgba(74,65,65,1)}
*{box-sizing:border-box}
html{font-size:clamp(9px, 0.62vw + 4px, 12px)}
body{margin:0;background:#fff;color:var(--text);font-family:"Work Sans",system-ui,sans-serif;font-size:1.5rem;line-height:1.3;-webkit-text-size-adjust:100%}
a{color:var(--link);text-decoration:none}
a:hover{opacity:.75}
b{font-weight:600}
h1{font-family:"Barlow Condensed","Arial Narrow",sans-serif;font-weight:700;font-size:5rem;line-height:1.05;color:var(--head);margin:0}
h1 a{color:rgba(0,0,0,.85)}
h2{font-family:"Work Sans",system-ui,sans-serif;font-weight:400;font-size:2.1rem;line-height:1.2;color:var(--head);margin:0}
h2 a{color:rgba(0,0,0,.85)}
small{display:inline-block;font-size:1rem;line-height:1.3;color:var(--muted)}
small a{color:#000}
hr{background:rgba(127,127,127,.2);border:0;height:1px;margin:0}
ul,ol{padding-left:1.4em}
img{display:block;max-width:100%;height:auto}
[grid-col] img{width:100%}
iframe{max-width:100%;border:0}
.nav{position:sticky;top:0;z-index:5;background:rgba(255,255,255,.92);backdrop-filter:blur(6px);text-align:center;padding:1rem;font-weight:600}
.nav a{color:var(--text)}
.content{padding:.9rem .9rem 4rem;max-width:1600px;margin:0 auto}

/* Cargo 12-column grid */
[grid-row]{display:flex;flex-wrap:wrap;align-items:flex-start;--g:0rem;margin:0 calc(var(--g) / -2)}
[grid-row][grid-gutter="2"]{--g:.4rem}[grid-row][grid-gutter="4"]{--g:.8rem}[grid-row][grid-gutter="6"]{--g:1.2rem}
[grid-row][grid-gutter="8"]{--g:1.6rem}[grid-row][grid-gutter="10"]{--g:2rem}
[grid-col]{padding:0 calc(var(--g) / 2);min-width:0}
[grid-col="1"]{width:8.333%}[grid-col="2"]{width:16.667%}[grid-col="3"]{width:25%}[grid-col="4"]{width:33.333%}
[grid-col="5"]{width:41.667%}[grid-col="6"]{width:50%}[grid-col="7"]{width:58.333%}[grid-col="8"]{width:66.667%}
[grid-col="10"]{width:83.333%}[grid-col="x12"],[grid-col="12"]{width:100%}

/* galleries */
.image-gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem;margin:1rem 0}
.image-gallery br{display:none}
.gallery-slideshow{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;gap:1rem;padding-bottom:.6rem}
.gallery-slideshow img{flex:0 0 100%;width:100%;scroll-snap-align:center;object-fit:contain}

/* tablet: drop the 1-column side gutters, widen content */
@media (max-width:1000px){
  [grid-col].spacer{display:none}
}
/* mobile: stack every column full width */
@media (max-width:700px){
  html{font-size:10px}
  body{font-size:1.7rem}
  h1{font-size:4.4rem}
  h2{font-size:2.2rem}
  [grid-row]{margin:0}
  [grid-col]{width:100% !important;padding:0}
  [grid-col]+[grid-col]{margin-top:1.2rem}
  iframe[src*="spline"]{height:420px !important}
  .content{padding:.9rem 1.2rem 3rem}
}
"""

def doc(title, body, slug):
    nav = "" if slug == "NavBar" else '<nav class="nav"><a href="Portfolio_Home.html">Dhruv Srivastava</a></nav>'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{html.escape(title)} · Dhruv Srivastava (archive)</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Work+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="archive.css">
</head><body>{nav}<main class="content">{body}</main></body></html>
"""

titles = {"Portfolio_Home": "Home", "Experiment-Dump": "Experiments", "Mibby": "Mibby",
          "Voice_Analytics_solution": "Voice Analytics", "The_Centrist": "The Centrist",
          "AmazeStudio": "Amaze Studio", "I_will_be_fine": "I will be fine",
          "Interning-Credit-Suisse": "Interning at Credit Suisse", "NavBar": "Nav"}

os.makedirs(out, exist_ok=True)
for f in os.listdir(out):
    if f.endswith(".html"):
        os.remove(os.path.join(out, f))
open(os.path.join(out, "archive.css"), "w").write(CSS.strip() + "\n")
for slug, p in pages.items():
    if slug == "NavBar":
        continue
    open(os.path.join(out, f"{slug}.html"), "w").write(doc(titles.get(slug, slug), fix(p["content"], p), slug))

redirect = """<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={u}"><link rel="canonical" href="{u}">
<title>Redirecting</title><a href="{u}">Go to the old portfolio</a>
"""
open(os.path.join(out, "index.html"), "w").write(redirect.format(u="Portfolio_Home.html"))
open(os.path.join(root, "index.html"), "w").write(redirect.format(u="pages/Portfolio_Home.html"))
print("built", sorted(f for f in os.listdir(out)))
