"""Cut CC0 Freesound previews into the crowd_sound sample set (OGG, 32 kHz stereo).

    python tools/freesound_search.py cands.json "football crowd" "crowd scream" ...
    # download each candidate's `ogg` preview to raw/<id>.ogg, then:
    python tools/build_samples.py raw cands.json addons/crowd_sound/samples

Needs numpy, scipy, librosa and soundfile. The clips were picked by scoring 5 s
windows of every candidate with EfficientAT AudioSet taggers (Crowd, Cheering,
Screaming, Chant up; Music, Speech, Vehicle, noise down) and checking that each
source is CC0 on its Freesound page.

Screams are not single cuts: a recording of a "screaming crowd" is really one
or two people near the microphone. They are rebuilt as groups: dozens of
scream snippets from several recordings, each repitched (another person),
offset, panned and darkened by distance, at near-equal levels so no voice
leads. The group parameters were tuned by the same tagger (Screaming x Crowd)
plus spectral flatness from 300-4000 Hz, which rises as the harmonics of single
voices smear into a group. Roars and goals come only from one big stadium
(Millerntor, Hamburg): smaller-crowd recordings had loud voices near the
microphone (low flatness), and layering more stadium takes under a take did
not raise flatness but made the tagger hear buzz.
"""
import json, numpy as np, librosa, soundfile as sf, os, sys
from fractions import Fraction
from scipy.signal import butter, sosfilt, resample_poly
RAW, CANDS, OUT = sys.argv[1:4]; SR = 32000
os.makedirs(OUT, exist_ok=True)
# Plain cuts. name: (freesound id, start s, end s, fade-in s, fade-out s, kind)
CUTS = {
 "cheer_loop":  (829456, 0.5, 12.5, 0, 0, "loop"),
 "surge":       (829453, 47.7, 56.5, .8, 2.5, "shot"),
 "roar_1":      (829453, 33.6, 40.6, .05, 2.0, "shot"),
 "roar_2":      (829453, 22.1, 28.0, .05, 1.5, "shot"),
 "roar_3":      (829453, 0.4, 5.3, .05, 1.2, "shot"),
 "roar_4":      (829453, 7.1, 12.5, .05, 1.5, "shot"),
 "goal_1":      (829455, 0.1, 11.0, .02, 3.0, "shot"),
 "goal_2":      (829455, 15.2, 26.0, .02, 3.0, "shot"),
 "goal_3":      (829455, 37.9, 49.0, .02, 3.0, "shot"),
 "goal_4":      (829455, 58.6, 67.4, .02, 3.0, "shot"),
 "ooh_1":       (494362, 2.0, 7.0, .3, 1.5, "shot"),
 "chant_1":     (133833, 0.2, 17.0, .05, 2.5, "shot"),
 "chant_2":     (528799, 43.0, 60.5, .8, 2.5, "shot"),
 "chant_3":     (612131, 28.0, 40.5, .5, 2.5, "shot"),
 "chant_4":     (829456, 84.0, 100.0, .8, 2.5, "shot"),
}
# 2 s windows the tagger heard as screaming (Screaming + Yell > 0.25, little music).
SCREAM_WINDOWS = {249671: [1, 6, 7, 9], 438438: [108, 109, 112, 115],
                  491405: [0, 10, 12, 13, 21, 22, 23, 24, 36], 124022: [0, 10, 11, 12, 13],
                  173945: [0, 16, 18, 19, 25, 29]}
# Tuned group: ~28 voices, +-2 semitones, onsets over 0.5 s, levels within 4 dB.
SCREAM = dict(n=28, semis=1.94, spread=0.5, gain_db=2.0, dark=(3900, 10100), piece=(1.09, 2.62))
SCREAMS = {"scream_1": 11, "scream_2": 12, "scream_3": 13, "scream_4": 14}  # name: seed
SEAM = 0.6
_raw = {}
def raw(sid):
    if sid not in _raw:
        y, _ = librosa.load(f"{RAW}/{sid}.ogg", sr=SR, mono=False)
        _raw[sid] = np.stack([y, y]) if y.ndim == 1 else y
    return _raw[sid]
def repitch(x, semis):
    fr = Fraction(2 ** (-semis / 12)).limit_denominator(60)
    return resample_poly(x, fr.numerator, fr.denominator, axis=-1)
def lp(x, hz):
    return sosfilt(butter(2, hz, fs=SR, output="sos"), x, axis=-1)
def rms(x):
    return np.sqrt(np.mean(x ** 2)) + 1e-9
def place(out, x, t, pan):
    x = x[: max(0, out.shape[1] - t)]
    out[0, t:t + len(x)] += x * np.sqrt(1 - pan); out[1, t:t + len(x)] += x * np.sqrt(pan)
def scream_group(seconds, rng, n, semis, spread, gain_db, dark, piece, uniform=False):
    """n scream snippets: repitched, offset, panned, quieter ones darker (further away)."""
    windows = [(sid, t) for sid, ts in SCREAM_WINDOWS.items() for t in ts]
    out = np.zeros((2, int(seconds * SR))); used = set()
    for _ in range(n):
        sid, a = windows[rng.integers(len(windows))]; used.add(sid)
        L = rng.uniform(*piece); s0 = rng.uniform(a, a + max(0.0, 2.0 - L))
        x = raw(sid).mean(0)[int(s0 * SR): int((s0 + L) * SR)].copy()
        x = repitch(x, rng.uniform(-semis, semis))
        f = int(0.04 * SR); x[:f] *= np.linspace(0, 1, f); x[-3 * f:] *= np.linspace(1, 0, 3 * f)
        g_db = -rng.uniform(0, 2 * gain_db)
        x = lp(x, np.interp(g_db, [-2 * gain_db, 0], dark)) * 10 ** (g_db / 20) / rms(x)
        top = seconds - len(x) / SR if uniform else spread
        place(out, x, int(rng.uniform(0, max(0.01, top)) * SR), rng.uniform(0.1, 0.9))
    return out, sorted(used)
def loop_seam(x):
    s = int(SEAM * SR); body = x.shape[1] - s; w = np.sin(np.linspace(0, 1, s) * np.pi / 2) ** 2
    x[:, :s] = x[:, :s] * np.sqrt(w) + x[:, body:] * np.sqrt(1 - w)
    return x[:, :body]
def fades(x, fi, fo):
    if fi: k = int(fi * SR); x[:, :k] *= np.linspace(0, 1, k) ** 2
    k = int(fo * SR); x[:, -k:] *= np.linspace(1, 0, k) ** 2
    return x
def rms_top(y):  # loudness of the loudest second
    return max(np.sqrt(np.mean(y[i:i + SR] ** 2)) for i in range(0, max(1, len(y) - SR), SR // 4))

clips = {}  # name: (stereo buffer, credit sources, credit note)
for name, (sid, a, b, fi, fo, kind) in CUTS.items():
    extra = SEAM if kind == "loop" else 0
    x = raw(sid)[:, int(a * SR): int((b + extra) * SR)].copy()
    clips[name] = (loop_seam(x) if kind == "loop" else fades(x, fi, fo), [sid], f"{a:g}-{b:g} s")
for name, seed in SCREAMS.items():
    x, used = scream_group(3.0, np.random.default_rng(seed), **SCREAM)
    clips[name] = (fades(x, .02, 1.0), used, f"group of {SCREAM['n']} voices")
x, used = scream_group(8.0 + SEAM, np.random.default_rng(41), **dict(SCREAM, n=32), uniform=True)
clips["panic_loop"] = (loop_seam(x), used, "group of 32 voices, looped")

meta = json.load(open(CANDS)); meta = {m["id"]: m for m in meta}
link = lambda sid: f"[{meta[sid]['title']}](https://freesound.org/people/{meta[sid]['user']}/sounds/{sid}/) by {meta[sid]['user']}"
lines = ["# Crowd samples", "",
         "Built from Freesound recordings released under CC0 (public domain): no attribution is required, but here is where each clip comes from. Previews were trimmed, layered, faded, loudness-matched and re-encoded as 32 kHz OGG by `tools/build_samples.py`.",
         "", "| Clip | How | Freesound recordings |", "|---|---|---|"]
for name in sorted(clips):
    x, used, how = clips[name]
    x *= 0.1 / max(rms_top(x.mean(0)), 1e-6)   # loudest second at -20 dBFS, like the old synth
    pk = np.abs(x).max()
    if pk > 0.97: x *= 0.97 / pk
    sf.write(f"{OUT}/{name}.ogg", x.T, SR, format="OGG", subtype="VORBIS")
    lines.append(f"| {name} | {how} | {'<br>'.join(link(s) for s in used)} |")
open(f"{OUT}/CREDITS.md", "w").write("\n".join(lines) + "\n")
tot = sum(os.path.getsize(f"{OUT}/{f}") for f in os.listdir(OUT) if f.endswith(".ogg"))
print("total KB", tot // 1024)
