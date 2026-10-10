# Godot crowd sound

Crowd audio for Godot 4.5+: a murmur bed, cheers, applause, "ooh"s, screams,
a kick-off surge, goal eruptions and chants. The voiced parts play short CC0
stadium recordings from Freesound (`addons/crowd_sound/samples`, 2.2 MB, sources
in its `CREDITS.md`); murmur and applause are synthesized at boot. Set
`use_samples = false` before adding the node for the old fully procedural
crowd. It started as the colosseum crowd in Growing Guns.

Two values drive the mix: `enthusiasm` (exciting play) and `fear` (the crowd
itself in danger). Reactions raise them; they decay on their own.

## How it was tuned

The murmur and applause were tuned with an audio AI as judge: the EfficientAT
AudioSet taggers score each bake. Murmur is scored by embedding similarity to
real multi-talker speech babble: 0.47 for the old noise-based walla, about 0.84
for the talker synthesis (real babble: 0.88). Applause is scored on the
Applause + Clapping labels: about 1.4 out of 2, where the old pats scored 0 and
read as rain. The scripts are in the GameNight project files
(`crowd-sound/ai-tools`).

Baking is time-sliced: synthesis yields to the next frame after 2.5 ms of work.

## Use it

Copy the addon into your game:

    python sync.py path/to/game

Then add the node and tell it when there is an audience:

```gdscript
var crowd = preload("res://addons/crowd_sound/crowd_sound.gd").new()
add_child(crowd)
crowd.set_bus(&"SFX")
crowd.active = true
crowd.kickoff()       # anticipation swell
crowd.hit()           # bump, sometimes an "ooh"
crowd.roar()          # big moment
crowd.celebrate()     # goal / win: eruption, applause, then a chant
crowd.excite(0.2)     # mood only
crowd.scare(0.3, pos) # screams
```

Extend the script to tune the mix (`murmur_db`, `cheer_db`, ...) or to hook into
your game: `_play_oneshot` routes reactions through your own mixer,
`_loudness_db` ducks the beds under loud action, `_chant_position` places chants
in 3D and `_suppressed` mutes reactions. The header of `crowd_sound.gd` explains
each.

## Used by

- Growing Guns (`scripts/crowd_audio.gd`: colosseum ring, SFX mixer, crowd shader)
- Ballkickers (`src/crowd_sound.gd`: football events and mix)

After changing the addon, run `sync.py` on each game and commit there too.
Open the game in Godot (or run `godot --headless --import`) once so the new
samples get imported.

## Samples

`tools/freesound_search.py` lists CC0 candidates from Freesound and
`tools/build_samples.py` cuts, fades, loops and loudness-matches them into
`samples/`. Each clip was chosen by an AudioSet tagger (EfficientAT) scoring 5 s
windows of the recordings for Crowd, Cheering, Screaming and Chant.
`python sync.py --check path/to/game` tells you whether a copy is current.
