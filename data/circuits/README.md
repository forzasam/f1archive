# Circuit packages

Every supported race map is made from exactly three authored files sharing the same slug:

- `templates/circuits/<slug>.svg` — complete visible SVG, semantic hotspot paths, labels and start/finish artwork.
- `data/circuits/<slug>.json` — renderer metadata, event-marker coordinates and optional archive `circuit_ids`.
- `data/editorial/<season>-<slug>.json` — race-specific segments and events, including `race.season`, `race.round` and `race.slug`.

No Python or JavaScript registry needs editing. The race service discovers the editorial file from its season and round metadata, reads its slug, then loads the matching circuit JSON and SVG automatically.

Australia is currently the only authored package.
