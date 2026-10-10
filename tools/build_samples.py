"""Cut CC0 Freesound previews into the crowd_sound sample set (OGG, 32 kHz stereo).

    python tools/freesound_search.py cands.json "football crowd" "crowd scream" ...
    # download each candidate's `ogg` preview to raw/<id>.ogg, then:
    python tools/build_samples.py raw cands.json addons/crowd_sound/samples

Needs numpy, librosa and soundfile. The clips were picked by scoring 5 s windows
of every candidate with EfficientAT AudioSet taggers (Crowd, Cheering,
Screaming, Chant up; Music, Speech, Vehicle, noise down) and checking that each
source is CC0 on its Freesound page.
"""
import json, numpy as np, librosa, soundfile as sf, os, sys
RAW, CANDS, OUT = sys.argv[1:4]; SR = 32000
os.makedirs(OUT, exist_ok=True)
# name: (freesound id, start s, end s, fade-in s, fade-out s, kind)
CUTS = {
 "cheer_loop":  (829456, 0.5, 12.5, 0, 0, "loop"),
 "panic_loop":  (249671, 3.0, 11.0, 0, 0, "loop"),
 "roar_1":      (25304, 11.0, 18.0, .05, 2.0, "shot"),
 "roar_2":      (385920, 0.0, 6.0, .05, 1.5, "shot"),
 "roar_3":      (829453, 33.6, 41.0, .05, 2.0, "shot"),
 "roar_4":      (829453, 7.1, 12.5, .05, 1.5, "shot"),
 "surge":       (829453, 47.7, 56.5, .8, 2.5, "shot"),
 "goal_1":      (829455, 0.1, 11.0, .02, 3.0, "shot"),
 "goal_2":      (829455, 15.2, 26.0, .02, 3.0, "shot"),
 "goal_3":      (829455, 37.9, 49.0, .02, 3.0, "shot"),
 "goal_4":      (25304, 0.7, 11.5, .02, 3.0, "shot"),
 "ooh_1":       (494362, 2.0, 7.0, .3, 1.5, "shot"),
 "scream_1":    (249671, 1.4, 4.6, .01, .8, "shot"),
 "scream_2":    (438438, 106.0, 110.5, .05, 1.0, "shot"),
 "scream_3":    (438438, 111.5, 116.5, .05, 1.2, "shot"),
 "scream_4":    (491405, 9.5, 13.5, .05, 1.0, "shot"),
 "chant_1":     (133833, 0.2, 17.0, .05, 2.5, "shot"),
 "chant_2":     (528799, 43.0, 60.5, .8, 2.5, "shot"),
 "chant_3":     (612131, 28.0, 40.5, .5, 2.5, "shot"),
 "chant_4":     (829456, 84.0, 100.0, .8, 2.5, "shot"),
}
SEAM = 0.6
def rms_top(y, sr):  # loudness of the loudest second
    w = sr; e = [np.sqrt(np.mean(y[i:i + w] ** 2)) for i in range(0, max(1, len(y) - w), w // 4)]
    return max(e)
meta = json.load(open(CANDS)); meta = {m["id"]: m for m in meta}
credits = {}
for name, (sid, a, b, fi, fo, kind) in CUTS.items():
    y, _ = librosa.load(f"{RAW}/{sid}.ogg", sr=SR, mono=False)
    if y.ndim == 1: y = np.stack([y, y])
    extra = SEAM if kind == "loop" else 0
    x = y[:, int(a * SR): int((b + extra) * SR)].copy(); n = x.shape[1]
    if kind == "loop":
        s = int(SEAM * SR); body = n - s; w = np.linspace(0, 1, s)
        w = np.sin(w * np.pi / 2) ** 2  # equal-ish power
        x[:, :s] = x[:, :s] * np.sqrt(w) + x[:, body:] * np.sqrt(1 - w)
        x = x[:, :body]
    else:
        if fi: k = int(fi * SR); x[:, :k] *= np.linspace(0, 1, k) ** 2
        k = int(fo * SR); x[:, -k:] *= np.linspace(1, 0, k) ** 2
    x *= 0.1 / max(rms_top(x.mean(0), SR), 1e-6)   # loudest second at -20 dBFS, like the old synth
    pk = np.abs(x).max()
    if pk > 0.97: x *= 0.97 / pk
    sf.write(f"{OUT}/{name}.ogg", x.T, SR, format="OGG", subtype="VORBIS")
    m = meta[sid]; credits[name] = dict(id=sid, user=m["user"], title=m["title"], url=f"https://freesound.org/people/{m['user']}/sounds/{sid}/", seconds=[a, b])
lines = ["# Crowd samples", "", "Cut from Freesound recordings released under CC0 (public domain): no attribution is required, but here is where each clip comes from. Previews were trimmed, faded, loudness-matched and re-encoded as 32 kHz OGG by `tools/build_samples.py`.", "", "| Clip | Seconds | Freesound recording |", "|---|---|---|"]
lines += [f"| {k} | {v['seconds'][0]:g}-{v['seconds'][1]:g} | [{v['title']}]({v['url']}) by {v['user']} |" for k, v in credits.items()]
open(f"{OUT}/CREDITS.md", "w").write("\n".join(lines) + "\n")
tot = sum(os.path.getsize(f"{OUT}/{f}") for f in os.listdir(OUT) if f.endswith(".ogg"))
print("total KB", tot // 1024)
