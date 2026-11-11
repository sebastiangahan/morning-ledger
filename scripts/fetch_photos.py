"""Download free-licence photos for names in photos/wanted.txt.

Line format:  Name | hint | File:Optional_forced_pick.jpg
For each name we find the Wikidata item (its description must contain the hint), then look
through its Wikimedia Commons category (one level of subcategories, e.g. "X in 2025") and
score every free-licence photo: newer is better, candid shots (speaking, playing, performing,
landscape framing) beat posed portraits and headshots. The winner is saved as
photos/<slug>.jpg with its credit in photos/credits.json; the runners-up are listed there
too so a different one can be picked by hand. Entries made by an older picker are redone.
Runs in GitHub Actions (see .github/workflows/photos.yml)."""
import json, re, time, unicodedata, pathlib, urllib.parse, urllib.request, datetime

PICKER = 4
ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "photos"
UA = "MorningLedgerPhotoBot/1.1 (https://themorningledgerr.netlify.app)"
FREE = re.compile(r"^(cc0|cc[- ]by(-sa)?[- ]?[0-9.]*|public domain|pd.*|attribution.*)$", re.I)
YEAR = datetime.date.today().year
NEG = re.compile(r"portrait|official|headshot|head shot|crop|signature|logo|poster|card|flag|coat of arms|campaign photo|mugshot|graffiti|statue|wax|cartoon|drawing|painting|\bsign\b|banner|billboard|screenshot|quote|slogan|mural|caricature|vandal|turd|meme|protest sign|placard|tombstone|plaque|stamp|coin", re.I)
POS = re.compile(r"speak|speech|talk|at the|during|game|match|vs\.?|versus|playing|plays|rally|concert|perform|live|tour|festival|visit|meet|meeting|press|conference|announce|parade|ceremony|event|interview|stage|summit|warm[- ]?up|practice|celebrat", re.I)

def get(url, params=None):
    if params: url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=40) as r: return r.read()
        except Exception:
            if attempt == 3: raise
            time.sleep(3 + attempt * 4)

def api(url, **p): return json.loads(get(url, {**p, "format": "json"}))
WD, CM = "https://www.wikidata.org/w/api.php", "https://commons.wikimedia.org/w/api.php"
def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
def strip(h): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h or "")).strip()

def find_item(name, hint):
    for c in api(WD, action="wbsearchentities", search=name, language="en", limit=7, type="item")["search"]:
        if hint and hint.lower() not in (c.get("description") or "").lower(): continue
        claims = api(WD, action="wbgetentities", ids=c["id"], props="claims")["entities"][c["id"]].get("claims", {})
        val = lambda p: claims[p][0]["mainsnak"].get("datavalue", {}).get("value") if p in claims else None
        human = any(x["mainsnak"].get("datavalue", {}).get("value", {}).get("id") == "Q5" for x in claims.get("P31", []))
        c["human"] = human
        if val("P373") or val("P18"): return c, val("P373"), val("P18")
    return None, None, None

def category_files(cat, limit=900):
    files, cats, seen = [], ["Category:" + cat], set()
    for depth in range(2):
        nxt = []
        for c in cats:
            if c in seen: continue
            seen.add(c)
            cont = {}
            while True:
                r = api(CM, action="query", list="categorymembers", cmtitle=c, cmlimit=500, cmtype="file|subcat", **cont)
                for m in r["query"]["categorymembers"]:
                    if m["ns"] == 14: nxt.append(m["title"])
                    elif re.search(r"\.(jpe?g)$", m["title"], re.I): files.append(m["title"])
                if "continue" not in r or len(files) >= limit: break
                cont = {"cmcontinue": r["continue"]["cmcontinue"]}
            if len(files) >= limit: return files
        # only follow subcategories that look like "in 2024", "at ...", "speaking", "playing" etc., newest years first
        nxt = [x for x in nxt if re.search(r"(19|20)\d\d|\bat\b|\bin\b|speak|play|perform|concert|game|season", x, re.I)]
        nxt.sort(key=lambda x: max([int(y) for y in re.findall(r"(?:19|20)\d\d", x)] or [0]), reverse=True)
        cats = nxt[:40]
    return files

def depicting(qid, name, limit=200):
    titles = []
    for q in (f"haswbstatement:P180={qid} filetype:bitmap", f'intitle:"{name}" filetype:bitmap'):
        r = api(CM, action="query", list="search", srsearch=q, srnamespace=6, srlimit=100, srsort="create_timestamp_desc")
        titles += [x["title"] for x in r["query"]["search"] if re.search(r"\.jpe?g$", x["title"], re.I)]
    return list(dict.fromkeys(titles))[:limit]

def info(titles):
    out = []
    for i in range(0, len(titles), 50):
        r = api(CM, action="query", titles="|".join(titles[i:i+50]), prop="imageinfo", iiprop="url|size|extmetadata", iiurlwidth=1400)
        for p in r["query"]["pages"].values():
            if "imageinfo" in p: out.append((p["title"], p["imageinfo"][0]))
        time.sleep(0.5)
    return out

INSIDE = re.compile(r"interior|inside|locker|dressing|seats|seating|bowl|\btour\b|concourse|room|chamber|lobby|suite|court|rink|stage", re.I)
OUTSIDE = re.compile(r"exterior|outside|from |street|fa[cç]ade|front|entrance|aerial|skyline|view|plaza|square|night|dusk|sunset", re.I)
PAPARAZZI = re.compile(r"guests at|arrivals|arriving|red carpet|street style|spotted|paparazzi|backstage|fan photo|selfie|with fans", re.I)

def score(title, ii, human=True):
    md = ii.get("extmetadata", {})
    lic = strip(md.get("LicenseShortName", {}).get("value"))
    if not FREE.match(lic): return None
    w, h = ii.get("width", 0), ii.get("height", 0)
    if w < 1000 or h < 700: return None
    text = title + " " + strip(md.get("ImageDescription", {}).get("value")) + " " + strip(md.get("ObjectName", {}).get("value"))
    yrs = [int(y) for y in re.findall(r"(?:19|20)\d\d", strip(md.get("DateTimeOriginal", {}).get("value")) or strip(md.get("DateTime", {}).get("value")))]
    year = min(yrs) if yrs else 2000
    year = min(year, YEAR)
    s = -2.5 * (YEAR - year)            # each year older costs 2.5 points
    s += 4 if w > h * 1.15 else (-3 if h > w * 1.1 else 0)  # landscape framing tends to be candid
    if human:
        s += 4 * min(2, len(POS.findall(text)))
        s -= 7 * min(1, len(PAPARAZZI.findall(text)))
    else:
        s += 5 * min(2, len(OUTSIDE.findall(text)))
        s -= 9 * min(1, len(INSIDE.findall(text)))
        s += 2.5 * (YEAR - year) * 0.6   # landmarks change slowly: age matters less
    s -= 8 * min(2, len(NEG.findall(text)))
    if re.search(r"\(cropped\)|cropped", title, re.I): s -= 6
    others = len(re.findall(r",| and | & ", title))
    s -= 3 * max(0, others - 1)        # crowded group shots make weak lead photos
    return s, year, lic, md

def credit(name, item, title, ii, lic, md, year, alts):
    return {"name": name, "wikidata": item["id"] if item else "", "description": item.get("description", "") if item else "",
            "photo_year": year, "author": strip(md.get("Artist", {}).get("value")) or "Unknown", "license": lic,
            "license_url": md.get("LicenseUrl", {}).get("value", ""), "source": ii["descriptionurl"], "picker": PICKER,
            "alternatives": alts}

def main():
    cp = DIR / "credits.json"
    credits = json.loads(cp.read_text()) if cp.exists() else {}
    lines = [l.strip() for l in (DIR / "wanted.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]
    missing = []
    for line in lines:
        parts = [x.strip() for x in line.split("|")] + ["", ""]
        name, hint, forced = parts[0], parts[1], parts[2]
        key = slug(name)
        old = credits.get(key, {})
        if old.get("picker") == PICKER and (not forced or old.get("source", "").endswith(urllib.parse.quote(forced.replace(" ", "_"), safe=":"))):
            continue
        try:
            item, cat, p18 = find_item(name, hint)
            if forced:
                cands = info([forced if forced.startswith("File:") else "File:" + forced])
                ranked = [(score(t, ii) or (0, 0, "", ii.get("extmetadata", {})), t, ii) for t, ii in cands]
            else:
                titles = depicting(item["id"], name) if item else []
                if len(titles) < 8 and cat: titles += [x for x in category_files(cat) if name.split()[-1].lower() in x.lower()]
                if p18: titles.append("File:" + p18)
                titles = list(dict.fromkeys(titles))
                ranked = [(sc, t, ii) for t, ii in info(titles) if (sc := score(t, ii, (item or {}).get("human", True)))]
                ranked.sort(key=lambda x: x[0][0], reverse=True)
            if not ranked: missing.append(f"{name}: no free photo found"); continue
            (sc, year, lic, md), title, ii = ranked[0]
            if forced and not FREE.match(lic or ""): missing.append(f"{name}: forced file is not free ({lic})"); continue
            (DIR / f"{key}.jpg").write_bytes(get(ii.get("thumburl") or ii["url"]))
            alts = [t for _, t, _ in ranked[1:6]]
            cdir = DIR / "candidates" / key
            if not forced and cdir.exists():
                for f in cdir.glob("*"): f.unlink()
            cdir.mkdir(parents=True, exist_ok=True)
            for n, (_, t2, ii2) in enumerate([] if forced else ranked[:12]):
                try:
                    small = api(CM, action="query", titles=t2, prop="imageinfo", iiprop="url", iiurlwidth=480)
                    u = next(iter(small["query"]["pages"].values()))["imageinfo"][0]["thumburl"]
                    (cdir / f"{n}.jpg").write_bytes(get(u))
                except Exception: pass
            if not forced: (cdir / "list.json").write_text(json.dumps([t2 for _, t2, _ in ranked[:12]], indent=1, ensure_ascii=False))
            credits[key] = credit(name, item, title, ii, lic, md, year, alts)
            print(f"OK  {name}: {title} ({year}, score {sc:.1f}, {len(ranked)} candidates)")
            for (s2, y2, *_), t2, _ in ranked[1:6]: print(f"    alt {t2} ({y2}, {s2:.1f})")
        except Exception as e:
            missing.append(f"{name}: error {e}")
    cp.write_text(json.dumps(credits, indent=2, ensure_ascii=False) + "\n")
    (DIR / "missing.txt").write_text("\n".join(missing) + ("\n" if missing else ""))
    for m in missing: print("MISS", m)

if __name__ == "__main__": main()
