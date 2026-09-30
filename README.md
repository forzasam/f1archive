# F1 Archive

**An interactive archive for exploring the history and stories of Formula 1.**

F1 Archive is an independent web application built to make Formula 1 history easier to explore. It combines historical race and championship data with curated editorial storytelling and interactive visualisations, aiming to bridge the gap between a statistical database and a traditional written history of the sport.

Rather than treating races and seasons as isolated tables of results, F1 Archive places them in context: how a championship developed, what was at stake entering a race, where decisive moments happened on the circuit, and how those moments affected the wider season.

The project is built and maintained as a personal software-development project using Python, Flask and JavaScript.

> **Live site:** [f1archive.net](https://f1archive.net)

---

## What F1 Archive does

The archive is organised around Formula 1 seasons and races, with historical data presented alongside original editorial content and interactive features.

### Season archive

Season pages provide an overview of each championship, including:

- Drivers' and Constructors' Championship standings
- race calendars and results
- points, wins and championship statistics
- driver and constructor filtering
- curated **Season Stories** explaining the wider championship narrative
- optional **Setting the Stakes** introductions and **Aftermath** retrospectives surrounding the race-by-race story

The aim is for a visitor to be able to follow a championship chronologically rather than simply looking up individual results.

### Race pages

Individual Grands Prix combine classification data with the wider championship context.

Features include:

- complete race classifications
- non-finisher and retirement information
- championship standings before and after the race
- championship position and points changes
- chronological navigation between races in a season
- editorial race context and stories
- circuit visualisations where authored data is available

### Interactive circuits

F1 Archive uses SVG circuit geometry combined with structured circuit metadata to create interactive track maps.

Circuit definitions can contain:

- individual corners
- named track sections
- straights and complexes
- start/finish position
- racing direction
- sector boundaries
- pit entry and exit locations

Circuit geometry is kept separate from race-specific editorial data, allowing the same circuit definition to be reused across multiple Grands Prix and seasons.

### Race Stories

Race Stories are designed to explain important events spatially as well as chronologically.

Events can be associated with particular sections of a circuit and connected to an interactive race timeline, allowing the reader to see both **when** something happened and **where** it happened.

The longer-term goal is to develop these into animated race replays for important moments such as overtakes, incidents, pit-stop sequences and championship-deciding events.

### Archive Challenge

F1 Archive also includes **Archive Challenge: Who drove this season?**, an identification game generated entirely from the historical archive.

It includes:

- endless and daily modes
- progressively harder questions
- a points-based hint system
- server-side answer verification
- questions spanning both modern and historic Formula 1

---

## Editorial storytelling

Statistics provide the foundation of the archive, but the project is intended to tell the stories behind them.

Editorial content exists at several levels:

**Season Stories** provide the overarching narrative of a championship.

**Setting the Stakes** introduces the drivers, teams and circumstances before the opening round.

**Race Stories** focus on significant individual Grands Prix and the events that shaped them.

**Aftermath** provides space to reflect on a championship after its conclusion.

Together, these are intended to make it possible to experience a season from beginning to end as a connected story.

---

## Authoring tools

A significant part of the project is the development of custom tools for producing interactive content without hard-coding individual races.

### Track Editor

The Track Editor converts existing SVG circuit geometry into reusable semantic circuit definitions.

It allows circuit features such as corners, segments, sectors, direction and pit-lane locations to be visually authored and exported as structured JSON.

### Event Sequencer

The Event Sequencer is being developed as the authoring environment for animated Race Stories.

It combines a circuit SVG and its semantic circuit definition with:

- scenes
- camera positioning
- story-specific actors/drivers
- chained actor movements
- animation timing
- scene descriptions
- full-story playback

The resulting JSON can describe a race sequence independently of the renderer used on the website.

This separation between **geometry**, **circuit semantics**, **race data** and **editorial animation** is intended to make the system reusable across the archive.

---

## Data architecture

F1 Archive uses a file-backed archive rather than relying on external API calls during normal page rendering.

Historical seasons are stored locally, while the current championship uses a persistent live archive that is periodically refreshed.

A simplified view of the project is:

```text
Historical / live race data
            │
            ▼
     Local archive layer
            │
      ┌─────┴─────┐
      ▼           ▼
 Statistics    Editorial data
      │           │
      └─────┬─────┘
            ▼
      Flask services
            │
            ▼
     Jinja templates
            │
            ▼
 Interactive archive
```

This architecture reduces dependence on external services during requests and allows historical data, editorial content and interactive features to evolve independently.

---

## Technology

F1 Archive is primarily built with:

- **Python**
- **Flask**
- **Jinja**
- **JavaScript**
- **HTML / CSS**
- **SVG**
- **JSON**

The project also includes automated data auditing and validation tools used to check the consistency of historical championship and race data.

---

## Project structure

```text
app.py              Flask application
routes/              Application routes
services/            Archive and application logic
templates/           Jinja templates
static/              CSS, JavaScript and frontend assets
data/
├── archive/         Historical Formula 1 data
├── live/            Current-season archive
├── circuits/        Circuit definitions
└── editorial/       Season and race storytelling
scripts/             Data maintenance and auditing tools
tests/               Automated tests
```

---

## Roadmap

F1 Archive is under active development. Major planned areas include:

- expanding editorial coverage across landmark Formula 1 seasons
- completing interactive circuit definitions for historical layouts
- richer race timelines and event visualisation
- animated Race Stories using the Event Sequencer
- driver-focused historical stories
- improved navigation between related seasons, races and stories
- continued expansion and auditing of the historical dataset

The long-term objective is to make F1 Archive a place where Formula 1 history can be **explored as both data and narrative**.

---

## Running locally

For development:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

The application is then available at `http://127.0.0.1:5000`.

---

## Data, attribution and independence

F1 Archive is an independent project and is not affiliated with Formula 1, the FIA, Formula One Management or any Formula 1 team.

Third-party datasets and circuit geometry are used in accordance with their respective licences and attribution requirements. See the live site's disclaimer and relevant in-app attribution for further information.

---

## Status

F1 Archive is actively developed. Historical data coverage is substantially broader than the current editorial and interactive coverage, so some seasons currently function primarily as statistical archive pages while others contain richer stories and interactive features.

The repository reflects ongoing development toward the full archive experience.
