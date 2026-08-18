# UI

The ground control interface for İTÜ CEZERİ's 2026 competitions.

**One PyQt6 app, three competitions.** It starts on a selection screen; the
competition picked there decides which interface opens, and everything after
that comes from that competition's folder.

```bash
cd UI
pip install -r requirements.txt
python main.py
```

The interface talks to the ground station over MQTT and to nothing else. It
never reaches an aircraft directly: everything an operator sees arrives because
a ground station published it, and every button sends a command back the same
way. Start the broker and the ground station first — detections and telemetry
are published live and not retained, so anything sent while the interface is
still on its selection screen is gone.

## The three competitions

| Selection | Folder | What it is |
|---|---|---|
| **ULUSLARARASI** | `competitions/international_uav/` | TEKNOFEST Uluslararası İHA — Serbest Görev. The Pasifik VTOL flies a scan, the operator approves what it found, the swarm delivers a package to each approved coordinate. Map, mission bar, detection review, target pool, link health. |
| **SÜRÜ İHA** | `competitions/swarm_uav/` | TEKNOFEST Sürü İHA. The swarm formation mission. |
| **SUAS** | `competitions/suas/` | SUAS. Offline map, mission clock, laps and the safety path. |

The selection screen also asks how many drones and VTOLs the competition flies
with; the count must match the ground station's configuration.

## Layout

```
main.py              selection dialog, then hands over to a competition
config.py, config/   settings every competition needs (broker, logging, design tokens)
theme/               the design system: tokens, stylesheet, motion, elevation
windows/             the shared selection dialog
widgets/             competition-agnostic widgets — Card, Readout, StatusPill, StatusDot
  detection_review/  the approve / deny browser — shared by Uluslararası İHA and SUAS
mqtt/                transport only, no UI knowledge
designer/            shared .ui files
competitions/
  __init__.py        the only place a competition key appears
  international_uav/
  swarm_uav/
  suas/
```

Each competition folder is its own small app — `config.py` + `config/`,
`controller/`, `models/`, `widgets/`, `windows/`, `designer/` — behind an
`__init__.py` that exposes one start function.

## The rules that keep the three apart

1. Nothing in `theme/`, `widgets/`, `mqtt/`, `windows/` or `config/` at the root
   may name a competition. A shared widget that needs to vary takes a parameter
   or a hook, and the stylesheet selects on generic properties, so there is no
   rule anywhere in `theme/sheets/` that only one competition could match.
2. A competition-specific need never becomes a flag on a shared widget. Either
   it generalizes for all three, or it lives in that competition's folder.
3. **Changing shared code means starting the other two competitions
   afterwards.** That check is part of the change, not a follow-up.

## How it is configured

No literal colour, size or address appears in the code. `config/` at the root
holds what every competition needs — the broker address and log level in
`general.toml`, the design tokens in `theme.toml`, the selection screen in
`selection.toml` — and each competition's `config/` holds its own topics,
limits and labels. Sections deep-merge, so a key lives in exactly one file.

`config/general.toml` is the file to edit between bench sessions:
`broker_address` is `localhost` because the interface and the ground station
normally run side by side on the same laptop.

## Two things about SUAS that are not preferences

1. **The map is never covered and never tabbed away.** Rule 3.0.6 requires a
   display the judges can always see, showing the flight boundaries and the
   aircraft with ground speed in knots and altitude in feet AGL. No map, no
   takeoff; if the judge loses sight of it mid-mission the aircraft is recalled.
   That is why `competitions/suas/` has no dialogs, and why the safety controls
   are held rather than confirmed in a modal.
2. **The map reads tiles from a local MBTiles file and has no network code.**
   Appendix B and rule 5.3.5 forbid a safety-critical function from depending on
   the public internet. `competitions/suas/assets/tiles/` is deliberately empty
   here — the real tiles are cut before travelling and copied in on the day.
   Until one is there the map says `MAP TILES MISSING` over the mission, and it
   says the same when a file opens but holds no tiles at the zoom level on
   screen.

## Requirements

Python 3.10 or newer, and `requirements.txt`: PyQt6, paho-mqtt, colorlog
(`tomli` as well, below Python 3.11). An MQTT broker — Mosquitto is what we use
— runs alongside, and is installed separately.

## Documents

Kept local rather than tracked, next to the code they describe.

| File | What it is |
|---|---|
| `docs/DESIGN_SYSTEM.md` | How every screen in every competition is allowed to look. Read it before touching anything visible. |
| `docs/INTERNATIONAL_UAV_UI.md` | What the Uluslararası İHA interface must show and do: module layout, topic bindings, work items. |
| `docs/SUAS_UI.md` | The same for SUAS. |
| `../RULES.md` | The coding rules every change complies with. |
| `../International-UAV/docs/TASKS.md` | The vehicle and ground-station work this interface talks to. |
| `../SUAS/docs/COMPETITION_RULES.md` | Why the SUAS interface looks the way it does; §4 lists what a judge checks before takeoff. |
