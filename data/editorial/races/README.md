# Race-in-context stories

Store race stories by season and round:

```text
data/editorial/races/<season>/<round>.json
```

For example, the 2025 Australian Grand Prix (Round 1) is:

```text
data/editorial/races/2025/1.json
```

Each file follows the season-story schema:

```json
{
  "kicker": "The race in context",
  "title": "Story title",
  "author": "Author name",
  "paragraphs": [
    "First paragraph.",
    "Second paragraph.",
    "Additional paragraphs appear in the expanded story modal."
  ]
}
```

A missing file, invalid JSON, or an empty `paragraphs` array is treated as no
story. The race page and championship calendar will continue to render in their
standard layouts.
