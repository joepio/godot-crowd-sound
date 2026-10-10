"""Scrape Freesound search (CC0 only, no API key) -> JSON list of {id, user, title, dur, ogg preview URL}."""
import sys, re, json, html, subprocess, urllib.parse
def search(q, pages=2):
    out = []
    for page in range(1, pages + 1):
        url = "https://freesound.org/search/?" + urllib.parse.urlencode({"q": q, "f": 'license:"Creative Commons 0"', "page": page, "s": "Downloads (most first)"})
        t = subprocess.run(["curl", "-sS", "-A", "Mozilla/5.0", url], capture_output=True, text=True).stdout
        for blk in t.split('data-sound-id="')[1:]:
            g = lambda k: (re.search(k + r'="([^"]*)"', blk) or [None, ""])[1]
            sid = blk.split('"')[0]
            out.append(dict(id=int(sid), user=html.unescape(g("data-username")), title=html.unescape(g("data-title")),
                            dur=float(g("data-duration") or 0), dl=g("data-num-downloads"), sr=g("data-samplerate"),
                            ogg=g("data-ogg").replace("-lq.", "-hq."), q=q))
    return out
if __name__ == "__main__":
    allr = {}
    for q in sys.argv[2:]:
        for r in search(q):
            allr.setdefault(r["id"], r)
    json.dump(list(allr.values()), open(sys.argv[1], "w"), indent=1)
    for r in allr.values(): print(r["id"], r["dur"], r["dl"], r["user"], "|", r["title"], "|", r["q"])
