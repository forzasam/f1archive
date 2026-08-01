# Author profiles

Author profile files live in this folder. The profile's `slug` must exactly match
its filename (without `.json`).

For example, `data/editorial/authors/jane_smith.json`:

```json
{
  "slug": "jane_smith",
  "name": "Jane Smith",
  "description": "A short biography or description of the eras and subjects the author covers.",
  "social_links": [
    {
      "label": "Website",
      "url": "https://example.com"
    }
  ],
  "featured_stories": [
    {
      "type": "season",
      "season": 1988
    },
    {
      "type": "race",
      "season": 2021,
      "round": 22
    }
  ]
}
```

Season and race story files attach an author using that exact slug:

```json
{
  "slug": "jane_smith"
}
```

The visible author name always comes from the matching profile's `name` field.
If the slug is missing, or no matching valid profile exists, no author credit is
shown. Article totals and publication lists are calculated automatically from
story files. Up to three featured stories can be selected; invalid references
are ignored.
