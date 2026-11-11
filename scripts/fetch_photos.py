"""Download free-licence photos for names in photos/wanted.txt.

For each name: find it on Wikidata, take its main image (property P18), check the
licence on Wikimedia Commons, and save a 1200px copy to photos/<slug>.jpg plus a
credit entry in photos/credits.json. Names already in credits.json are skipped.
Runs in GitHub Actions (see .github/workflows/photos.yml)."""
import json, re, sys, time, unicodedata, pathlib, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "photos"
UA = "MorningLedgerPhotoBot/1.0 (https://themorningledgerr.netlify.app)"
FREE = re.compile(r"^(cc0|cc[- ]by(-sa)?[- ]?[0-9.]*|public domain|pd.*|attribution.*)$", re.I)

def get(url, params=None):
    if params: url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r: return r.read()
        except Exception as e:
            if attempt == 2: raise
            time.sleep(2 + attempt * 3)

def api(url, **p): return json.loads(get(url, {**p, "format": "json"}))
def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
def strip(h): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h or "")).strip()

def find(name, hint):
    res = api("https://www.wikidata.org/w/api.php", action="wbsearchentities", search=name, language="en", limit=7, type="item")["search"]
    for c in res:
        if hint and hint.lower() not in (c.get("description") or "").lower(): continue
        ent = api("https://www.wikidata.org/w/api.php", action="wbgetentities", ids=c["id"], props="claims")["entities"][c["id"]]
        p18 = ent.get("claims", {}).get("P18")
        if p18: return c, p18[0]["mainsnak"]["datavalue"]["value"]
    return None, None

def main():
    credits_path = DIR / "credits.json"
    credits = json.loads(credits_path.read_text()) if credits_path.exists() else {}
    lines = [l.strip() for l in (DIR / "wanted.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]
    missing = []
    for line in lines:
        name, _, hint = (x.strip() for x in line.partition("|"))
        key = slug(name)
        if key in credits: continue
        try:
            item, fname = find(name, hint)
            if not fname: missing.append(f"{name}: no free photo found"); continue
            info = api("https://commons.wikimedia.org/w/api.php", action="query", titles="File:" + fname,
                       prop="imageinfo", iiprop="url|extmetadata", iiurlwidth=1200)
            ii = next(iter(info["query"]["pages"].values()))["imageinfo"][0]
            md = ii.get("extmetadata", {})
            lic = strip(md.get("LicenseShortName", {}).get("value"))
            if not FREE.match(lic): missing.append(f"{name}: licence '{lic}' not free"); continue
            (DIR / f"{key}.jpg").write_bytes(get(ii.get("thumburl") or ii["url"]))
            credits[key] = {"name": name, "file": f"{key}.jpg", "wikidata": item["id"], "description": item.get("description", ""),
                            "author": strip(md.get("Artist", {}).get("value")) or "Unknown", "license": lic,
                            "license_url": md.get("LicenseUrl", {}).get("value", ""), "source": ii["descriptionurl"]}
            print(f"OK  {name} -> {key}.jpg ({lic}, {credits[key]['author']})")
            time.sleep(1)
        except Exception as e:
            missing.append(f"{name}: error {e}")
    credits_path.write_text(json.dumps(credits, indent=2, ensure_ascii=False) + "\n")
    (DIR / "missing.txt").write_text("\n".join(missing) + ("\n" if missing else ""))
    for m in missing: print("MISS", m)

if __name__ == "__main__": main()
