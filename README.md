# F1 Archive

A modular Flask project for exploring Formula 1 seasons, races and results.

## Open in PyCharm

1. Extract the ZIP.
2. In PyCharm choose **File → Open**.
3. Select the `f1_archive_v2` folder.
4. Create a Python virtual environment when prompted.
5. Install `requirements.txt`.
6. Run `app.py`.

## Terminal setup

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Then:

```bash
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Structure

```text
app.py                     Application factory and startup
config.py                  Project settings
routes/                    Flask URL routes
services/                  API and archive logic
models/                    Data structures
templates/                 Jinja HTML templates
static/                    CSS and future JavaScript/assets
data/circuits/             Future circuit SVG and corner data
data/editorial/            Future curated race events
database/                  Reserved for the later local database
```

## Homepage filters

The homepage supports:

```text
/?driver=alonso
/?constructor=ferrari
/?driver=alonso&constructor=ferrari
```

Selecting both filters performs a combined driver–constructor query. The
results therefore represent seasons in which the selected driver actually
raced for the selected constructor, rather than seasons where both happened
to participate independently.

## Current routes

- `/`
- `/season/<year>`
- `/season/<year>/race/<round>`

## Linked filters

Selecting a driver restricts the team autocomplete to constructors that driver represented. Selecting a team restricts the driver autocomplete to drivers who raced for that constructor. The relationship lists are loaded on demand through `/api/filter-options`.


## Season championship overview

Each season page now displays:

- the leading three drivers and constructors
- expandable full standings
- points and wins
- team-colour accents, with curated colours for major teams and stable fallback
  colours for historic constructors

When the homepage is filtered by a driver, every season card also shows that
driver's final championship position, points, wins and constructor(s).


## Experimental Australia 2026 race map

The 2026 Australian Grand Prix race page now contains an interactive Albert
Park prototype. Hovering identifies named track sections; clicking a section
shows its curated featured events. The initial dataset is intentionally not a
complete overtake census. It contains source-verified showcase events used to
test the map, interaction model and editorial schema.


## Albert Park geometry revision

The previous generic schematic has been replaced with a manually traced,
segmented SVG based on Formula 1's official 2026 Melbourne circuit diagram.
The geometry follows the recognisable 14-corner Albert Park layout and each
semantic race section is its own SVG path. It is a faithful display trace,
not an FIA-provided CAD file or survey-grade centreline.


## Race classification correction

Finisher totals and the non-finisher sidebar now use Jolpica's
`positionText` classification marker rather than inferring completion from
the result status. Numeric classifications count as finishers even when the
driver is one or more laps down. Retirement, withdrawal, disqualification
and exclusion markers remain outside the classified finishers.


## Race-page championship progression

Race pages now include the Drivers' Championship immediately before and after
the selected Grand Prix. The pre-race snapshot comes from the preceding
round's standings and the post-race snapshot comes from the selected round.
The top five are visible by default and the complete classifications can be
expanded. Position movement and points earned during the round are shown in
the post-race panel. Season openers display a pre-season state rather than an
arbitrary ordering of drivers tied on zero points.


## Current-calendar circuit geometry

All venues on the 2026 Formula 1 calendar now have circuit geometry on their
race pages. Australia retains its locally authored segmented interactive map.
Other venues display the correct detailed SVG layout with a notice that named
segments and event data have not yet been authored.

The layouts are sourced from Jules Roy's `f1-circuits-svg` project under
CC BY 4.0. Source and licence attribution are displayed beneath every map.
The integration currently maps the 2026 calendar and the two original
cancelled 2026 venues. Historical layout selection is the next extension:
the upstream archive already contains layout evolutions dating back to 1950.


## Experimental Australia race timeline

The interactive Australia 2026 map now includes a linked 58-lap timeline.
Every featured event appears as a coloured dot at its race lap and as a
chronological event card. Selecting a dot, card or map marker highlights the
corresponding circuit segment and opens the same event in the map detail
panel. Selecting a circuit segment filters the chronological list to events
at that location. The timeline can also be filtered by overtakes, incidents
and retirements.


## v14: completed 2026 race maps

Rounds 1–10 now have curated interactive timelines. Australia retains its
bespoke inline trace. China through Belgium use the licensed circuit SVG as
the exact visual geometry, with editorial segments applied by path-length
ranges. Timeline dots, event cards, segment chips and map markers are linked.

Some lap/location assignments are labelled approximate where the official
race report identifies the event but not an exact lap or corner.


## v15: unified premium map interaction

All completed 2026 race maps now follow the authored Australia interaction
model. Hovering a circuit segment fades the rest of the circuit, highlights
the selected section, reveals the segment name both on the map and in a
tooltip, and keeps the sidebar and timeline linked.

Every map now also includes timeline playback. The playhead advances through
the race lap by lap, pauses briefly at featured events, selects the matching
event card, highlights the circuit segment, and pulses the corresponding map
marker. Previous-event, next-event and 1x/2x/4x playback controls are shared
across all ten completed rounds.


## v16: clean single-path circuit interaction

Rounds 2–10 no longer use stacked transparent segment paths. Those paths
overlapped and caused the final segment to capture every hover. Each map now
uses one wide hit path and determines the nearest point on the circuit from
the pointer coordinates before mapping that position to the correct named
segment.

The external SVG is also reduced to its exact circuit geometry and redrawn
with the same clean track, shadow, highlight and event-marker visual language
as the authored Australia map. Source labels, duplicate paths and decorative
SVG elements are not shown.

Timeline playback no longer calls scrollIntoView. The page remains fixed on
the circuit while the selected segment, sidebar, timeline dot and event marker
continue to update.


## v17: one map implementation only

The separate imported-SVG map implementation has been deleted. Every completed
2026 race now renders through `_race_map.html`, `race_map.js`, and the same
`.track-underlay`, `.track-segments`, `.event-marker`, tooltip, sidebar and
timeline classes used by Australia.

Rounds 2–10 fetch only their source circuit path on the server, place it
directly inside the page's inline SVG, and render one semantic SVG path per
editorial segment. There is no `<object>`, no secondary map JavaScript file,
no nearest-coordinate hover engine and no overlapping whole-track hit layer.

Australia retains its manually traced path pieces. The other tracks use the
same path-per-segment interaction architecture with exact source geometry.


## v18: complete corner maps and automatic canvas fitting

Rounds 2–10 now define every numbered corner individually rather than grouping
large parts of a lap into a handful of broad editorial zones. Each circuit has
an explicit ordered turn-label dataset matching its official corner count:
Shanghai 16, Suzuka 18, Miami 19, Montreal 14, Monaco 19, Barcelona 14,
Spielberg 10, Silverstone 18 and Spa 19.

Turn numbers are no longer inferred from segment names. They are positioned
from each circuit's dedicated label data, while events are mapped onto the
specific corner or straight where they occurred.

Generated maps now calculate the rendered track bounding box in the browser
and replace the source SVG viewBox with a tightly padded one. This removes the
large unused margins that made the tracks appear substantially smaller than
Australia.


## v19: repository-authored detailed maps

Rounds 2–10 now preserve the complete detailed white-outline SVG from
julesr0y/f1-circuits-svg rather than extracting and redrawing only its longest
path. The repository's own track thickness, start/finish line and racing
direction graphic remain visible.

The interaction layer detects the source start/finish stroke and uses that as
0% of the editorial lap. Shanghai and Suzuka reverse the source path ordering
to match their racing direction. Inaccurate automatically generated corner
numbers have been removed: the detailed source is used for geometry and
official directional annotation rather than presenting inferred labels as
authoritative.

Australia remains the manually authored gold-standard map. Its pit entry
wording has been corrected from Turn 12 to Turn 13.


## v20: Australian visual styling for repository geometry

The repository SVG is no longer displayed with its own presentation styles.
Only its principal circuit geometry is used. Every non-Australia circuit is
redrawn with the exact visual hierarchy used by the Australia map: a black
31px underlay, a pale 15px circuit stroke, and an 18px salmon active segment.

A clean start/finish line, label and direction arrow are drawn as archive
elements rather than inheriting source SVG styles. This prevents the giant red
filled-track rendering and keeps event markers, hover states and line weights
consistent across every race page.


## v21: genuine Australia-style segmented paths

The dasharray-based repository implementation has been removed. It had placed
a complete copy of the circuit under every editorial segment, which is why a
selected segment could render as a glowing full circuit.

The source centreline is now sampled into genuinely separate SVG path data for
each segment. This matches the structural approach used by Australia: one dark
underlay and one standalone visible path per named section.

Every generated circuit is transformed into Australia's fixed 1024 × 576
canvas and fitted into the same 916 × 492 drawing area. The original Australia
CSS is used without a second visual theme; line widths are counter-scaled to
retain the exact 31-unit underlay, 15-unit circuit and 18-unit active-section
appearance after normalization.


## v23: F1 diagrams are references only

The v22 approach that displayed Formula 1's circuit diagrams directly has
been removed in full. The project again renders its own inline SVG circuit
maps, using the archive's original dark underlay, pale circuit stroke,
salmon interaction state, event markers and synchronized timeline.

Formula 1 circuit diagrams are not embedded, linked as visible images or
presented as archive artwork. They are to be used only during authoring to
verify factual geometry: corner numbering, start/finish location, racing
direction, pit entry, sector boundaries, DRS detection points and speed
trap placement.

Australia remains the visual reference implementation. Its pit-entry
annotation is corrected to Turn 13.

## Persistent live archive

The current season is served from a disk-backed live archive rather than from
Jolpica during every page request. Historical seasons continue to use
`data/archive/seasons/<year>`.

By default, current-season files are written to:

```text
data/live/seasons/<current-year>/
```

In production, set `LIVE_ARCHIVE_ROOT` to the mount path of the web service's
persistent disk. A typical configuration is:

```text
LIVE_ARCHIVE_ROOT=/var/data/f1-live
LIVE_ARCHIVE_TTL_SECONDS=3600
LIVE_ARCHIVE_CHECK_INTERVAL_SECONDS=300
LIVE_ARCHIVE_BACKGROUND_REFRESH=true
```

The web process checks every five minutes and refreshes once the successful
snapshot is at least one hour old. The first request after a cold start also
performs the same stale check, so the site does not rely solely on the
background thread. A disk lock prevents duplicate refreshes across Gunicorn
workers.

Render cron jobs cannot access a web service's persistent disk, so do not use a
separate Render Cron Job for this file-backed cache. The standalone command is
still useful locally or from a shell attached to the same filesystem:

```bash
python scripts/update_live_archive.py
```

The live season directory mirrors the historical archive shape:

```text
seasons/2026/
├── schedule.json
├── driver_standings.json
├── constructor_standings.json
├── metadata.json
└── races/
    └── 01/
        ├── results.json
        └── driver_standings.json
```

`metadata.json` records the last attempt, last successful update, completed
rounds, the latest completed round reported by Jolpica, consecutive failures
and the most recent error. Writes are atomic and protected by a refresh lock.
A failed refresh does not overwrite the previous working snapshot.

The refresher reconciles the local cache against
`current/last/results.json`, then downloads any completed rounds missing from
local storage through their individual round endpoints. The latest round is
refreshed on every successful cycle, and the season standings are requested
for that exact round. This avoids treating a temporarily lagging season-wide
aggregate response as a complete and healthy snapshot.

## Season stories

Season-page editorial copy lives in `data/editorial/seasons/<year>.json`.
Each file uses this structure:

```json
{
  "kicker": "The season in context",
  "title": "A short, distinctive headline",
  "paragraphs": [
    "First paragraph.",
    "Second paragraph.",
    "Further paragraphs appear in the expanded story panel."
  ]
}
```

The first two paragraphs form the compact season-page preview. If the file has
more than two paragraphs, the page automatically adds a **Read the full story**
button and opens the complete text in a scrollable overlay.

Homepage driver, constructor and season filtering is generated from the local
historical and live archive snapshots. Those interactions no longer call the
Jolpica API directly.


## Search appearance and legal pages

The shared page template now supplies canonical URLs, page descriptions, Open Graph metadata, favicon links and basic WebSite structured data. The app also exposes `/robots.txt` and `/sitemap.xml`. Legal information is available at `/privacy` and `/disclaimer`, with a short independence notice in the global footer. Review the privacy wording whenever analytics, advertising, accounts or additional third-party services are introduced.

## Upcoming current-season race pages

The live season schedule is stored locally in `data/live/seasons/<year>/schedule.json`, including rounds that have not yet taken place. Race URLs now use that schedule when a round has no local `results.json` file:

- scheduled future rounds render `templates/upcoming_race.html`;
- a recently completed round whose classification has not reached the cache yet shows a short "results are on their way" state;
- once the hourly live updater stores the round results, the same URL automatically renders the normal race archive page;
- rounds absent from the schedule still return a genuine 404.

No empty result files are created for future rounds. The schedule remains the source of truth for planned events, while `races/<round>/results.json` continues to mean that a completed classification is available.

## Archive Challenge: Who drove this season?

The footer links to `/archive-challenge`, a locally powered identification game built from the committed season archive.

- **Endless mode** selects progressively harder campaigns as the streak grows.
- **Daily mode** gives every visitor the same deterministic challenge for the calendar day.
- A correct driver-and-season answer is worth up to four points; every revealed hint removes one available point.
- Modern seasons from 2000 onward form the full pool. Earlier seasons are limited to race winners and top-three championship finishers.
- Challenge answers are verified server-side with signed question tokens. No external API request is needed during play.

The challenge pool is cached in-process and rebuilt when the application restarts. If the committed archive changes while the process remains running, call `build_challenge_pool.cache_clear()` before rebuilding it.
