#!/usr/bin/env python3
"""Build the public Morning Ledger site from editions/YYYY-MM-DD.html into public/.
Usage: python3 build.py   (run from this folder). Netlify publishes public/."""
import re, json, html, os, shutil, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
SRC, OUT = ROOT / "editions", ROOT / "public"
CLARITY_ID = (ROOT / "clarity_id.txt").read_text().strip() if (ROOT / "clarity_id.txt").exists() else ""

def clarity():
    if not CLARITY_ID: return ""
    return ('<script>(function(c,l,a,r,i,t,y){c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};'
            't=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;y=l.getElementsByTagName(r)[0];'
            'y.parentNode.insertBefore(t,y);})(window,document,"clarity","script","%s");</script>' % CLARITY_ID)

def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()

NAV_CSS = """<style>
.sitebar{max-width:1140px;margin:0 auto;padding:10px max(16px,env(safe-area-inset-left,0px)) 0;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;
 font-family:"IBM Plex Sans Condensed","Arial Narrow",Arial,sans-serif;text-transform:uppercase;letter-spacing:.09em;font-size:12px;font-weight:600}
.sitebar a{color:#000;text-decoration:none;border-bottom:1px solid #bdbdbd}.sitebar a:hover{border-color:#000}
.sitebar nav{display:flex;gap:16px}
.sitefoot{max-width:1140px;margin:0 auto 40px;padding:0 max(16px,env(safe-area-inset-left,0px));font-size:14.5px;color:#444;font-family:Georgia,serif}
</style>"""

def nav(date_label):
    return ('<div class="sitebar"><span>%s</span><nav><a href="/">Today</a><a href="/archive/">Archive &amp; search</a></nav></div>' % date_label)

FOOT = ('<p class="sitefoot">The Morning Ledger is written with AI assistance and checked against reporting from outlets across the '
        'political spectrum. Every story links to its sources. Free to read. <a href="/archive/">Browse past editions</a>.</p>')

def page(title, desc, body, extra_head=""):
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
            f"<title>{html.escape(title)}</title><meta name=\"description\" content=\"{html.escape(desc)}\">"
            f"<meta property=\"og:title\" content=\"{html.escape(title)}\"><meta property=\"og:description\" content=\"{html.escape(desc)}\">"
            f"{extra_head}{NAV_CSS}{clarity()}</head><body style=\"margin:0;background:#fff;color:#000\">{body}</body></html>")

def build():
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    files = sorted(SRC.glob("*.html"))
    index = []
    for f in files:
        date = f.stem
        raw = f.read_text()
        raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)          # drop private editorial notes
        raw = re.sub(r"<title>.*?</title>|<meta name=\"claude:[^>]*>", "", raw, flags=re.S)
        head = "".join(re.findall(r"<link[^>]+>|<style>.*?</style>", raw, flags=re.S))
        m = re.search(r'<div class="page".*</div>', raw, flags=re.S)
        body = m.group(0) if m else raw
        dl = re.search(r'class="dateline[^"]*"><span>(.*?)</span>', body, flags=re.S)
        label = text(dl.group(1)) if dl else date
        heads = [text(h) for h in re.findall(r"<h3>(.*?)</h3>", body, flags=re.S)]
        scan = [text(s) for s in re.findall(r"<li><span>(.*?)</span></li>", body, flags=re.S)]
        decks = [text(d) for d in re.findall(r'<p class="deck">(.*?)</p>', body, flags=re.S)]
        lead = heads[0] if heads else "The Morning Ledger"
        index.append({"date": date, "label": label, "lead": lead, "headlines": heads, "scan": scan,
                      "q": " ".join(heads + decks + scan).lower()})
        doc = page(f"{lead} | The Morning Ledger, {label}", " ".join(scan[:2])[:200], nav(label) + body + FOOT, head)
        (OUT / date).mkdir()
        (OUT / date / "index.html").write_text(doc)
    if index:
        shutil.copy(OUT / index[-1]["date"] / "index.html", OUT / "index.html")
    index.reverse()
    (OUT / "editions.json").write_text(json.dumps(index, ensure_ascii=False))
    (OUT / "archive").mkdir()
    (OUT / "archive" / "index.html").write_text(page("Archive | The Morning Ledger",
        "Every edition of The Morning Ledger, searchable by date or story.", nav("Archive") + ARCHIVE, FONTS))
    print(f"built {len(index)} editions into {OUT}")

FONTS = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bodoni+Moda:opsz,wght@6..96,900&family=Playfair+Display:wght@800&family=Newsreader:opsz,wght@6..72,400&family=IBM+Plex+Sans+Condensed:wght@600;700&display=swap">'

ARCHIVE = r"""<style>
.arc{max-width:900px;margin:0 auto;padding:18px max(16px,env(safe-area-inset-left,0px)) 48px;font-family:Newsreader,Georgia,serif;font-size:17px;line-height:1.45}
.arc h1{font-family:"Bodoni Moda",serif;font-weight:900;text-transform:uppercase;text-align:center;font-size:clamp(30px,7vw,64px);line-height:1;padding:8px 0 12px;border-bottom:4px solid #000}
.arc .tools{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0 6px}
.arc input{font:inherit;font-size:17px;border:2px solid #000;padding:8px 10px;border-radius:0;background:#fff;color:#000;min-width:0}
.arc input[type=search]{flex:1 1 260px}
.arc .count{font-family:"IBM Plex Sans Condensed",Arial,sans-serif;text-transform:uppercase;letter-spacing:.08em;font-size:12px;font-weight:600;color:#444;margin:6px 0 10px}
.arc ol{list-style:none;padding:0;margin:0}
.arc li{border-top:1px solid #000;padding:14px 0}
.arc li a{color:#000;text-decoration:none;display:block}
.arc .d{font-family:"IBM Plex Sans Condensed",Arial,sans-serif;text-transform:uppercase;letter-spacing:.08em;font-size:12px;font-weight:700}
.arc .h{font-family:"Playfair Display",Georgia,serif;font-weight:800;font-size:22px;line-height:1.15;margin:3px 0}
.arc .m{color:#444;font-size:15.5px}
.arc mark{background:#000;color:#fff;padding:0 2px}
</style>
<main class="arc"><h1>The Morning Ledger</h1>
<div class="tools"><input type="search" id="q" placeholder="Search a story, person or place" aria-label="Search editions"><input type="date" id="d" aria-label="Jump to a date"></div>
<p class="count" id="c"></p><ol id="list"></ol></main>
<script>
const esc=s=>s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let all=[];
function hit(e,q){if(!q)return e.headlines.slice(1,4).join(' · ');
 const lines=e.headlines.concat(e.scan).filter(l=>l.toLowerCase().includes(q));
 const re=new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'gi');
 return lines.slice(0,3).map(l=>esc(l).replace(re,m=>'<mark>'+m+'</mark>')).join(' · ');}
function render(){const q=document.getElementById('q').value.trim().toLowerCase(),d=document.getElementById('d').value;
 const rows=all.filter(e=>(!q||e.q.includes(q))&&(!d||e.date===d));
 document.getElementById('c').textContent=rows.length+(rows.length===1?' edition':' editions');
 document.getElementById('list').innerHTML=rows.map(e=>`<li><a href="/${e.date}/"><span class="d">${esc(e.label)}</span><div class="h">${esc(e.lead)}</div><div class="m">${q?hit(e,q):esc(hit(e,''))}</div></a></li>`).join('');}
fetch('/editions.json').then(r=>r.json()).then(j=>{all=j;const p=new URLSearchParams(location.search).get('q');if(p)document.getElementById('q').value=p;render();});
document.getElementById('q').addEventListener('input',render);document.getElementById('d').addEventListener('input',render);
</script>"""

if __name__ == "__main__":
    build()
