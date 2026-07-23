const mapData = JSON.parse(
    document.getElementById("race-map-data").textContent
);

const tooltip = document.getElementById("segment-tooltip");
const segmentName = document.getElementById("selected-segment-name");
const segmentKind = document.getElementById("selected-segment-kind");
const eventList = document.getElementById("segment-events");
const markerLayer = document.getElementById("event-markers");
const svg = document.querySelector(".circuit-map");

const timelineList = document.getElementById("timeline-list");
const timelineRail = document.getElementById("timeline-rail");
const timelineReset = document.getElementById("timeline-reset");
const timelineContext = document.getElementById("timeline-context");
const timelineFilters = document.querySelectorAll(".timeline-filter");

const segmentLookup = new Map(
    mapData.segments.map((segment) => [segment.id, segment])
);

const eventLookup = new Map(
    mapData.events.map((event) => [event.id, event])
);

const markerPositions = {
    "pit-straight": [625, 492],
    "turns-1-2": [365, 426],
    "jones-straight": [210, 382],
    "turn-3": [101, 365],
    "turn-4": [137, 316],
    "turn-5": [68, 252],
    "lakeside-drive": [74, 116],
    "turns-6-7": [154, 50],
    "turn-8": [375, 142],
    "turns-9-10": [631, 274],
    "back-straight": [801, 247],
    "turn-11": [945, 356],
    "turn-12": [869, 455],
    "turn-13": [768, 440],
    "turn-14": [792, 477],
    "pit-entry": [835, 468]
};

const generatedTrack = document.getElementById("generated-track-reference");

const repositoryMap = svg?.dataset.generatedMap === "true";
const repositoryReverse = svg?.dataset.reverseDirection === "true";
let repositoryStartPct = 0;

function authoredPercentage(rawPct) {
    const value = Number(rawPct);
    const directed = repositoryReverse ? 100 - value : value;
    return (repositoryStartPct + directed + 100) % 100;
}

function pointAtPercentage(pct) {
    const length = generatedTrack.getTotalLength();
    return generatedTrack.getPointAtLength(
        length * ((pct % 100 + 100) % 100) / 100
    );
}

function pathSection(startPct, endPct) {
    const totalLength = generatedTrack.getTotalLength();
    let start = authoredPercentage(startPct);
    let end = authoredPercentage(endPct);

    if (!repositoryReverse) {
        if (end <= start) end += 100;
    } else {
        /*
         * authoredPercentage reverses the path, so sample backwards.
         * Unwrap the endpoint to keep the requested section contiguous.
         */
        if (end >= start) end -= 100;
    }

    const span = Math.abs(end - start);
    const samples = Math.max(8, Math.ceil(span * 2.4));
    const points = [];

    for (let index = 0; index <= samples; index += 1) {
        const progress = index / samples;
        const pct = start + (end - start) * progress;
        points.push(pointAtPercentage(pct));
    }

    return points
        .map((point, index) =>
            `${index === 0 ? "M" : "L"}${point.x.toFixed(2)} ${point.y.toFixed(2)}`
        )
        .join(" ");
}

function buildAuthoredSegmentPaths() {
    if (!repositoryMap || !generatedTrack) return;

    const underlay = document.getElementById("generated-track-underlay");
    underlay.setAttribute("d", pathSection(0, 100));

    document
        .querySelectorAll("#segment-hotspots [data-segment]")
        .forEach((path) => {
            path.setAttribute(
                "d",
                pathSection(path.dataset.startPct, path.dataset.endPct)
            );
        });
}

function normalizeGeneratedMapToAustraliaCanvas() {
    if (!repositoryMap || !generatedTrack) return;

    const root = document.getElementById("generated-track-root");
    if (!root) return;

    /*
     * Fit all generated circuits into the same visual area occupied by
     * Australia's manually authored trace. Stroke widths therefore use
     * precisely the same SVG units and scale consistently.
     */
    const box = generatedTrack.getBBox();
    const target = {
        x: 54,
        y: 24,
        width: 916,
        height: 492,
    };

    const scale = Math.min(
        target.width / Math.max(box.width, 1),
        target.height / Math.max(box.height, 1)
    );

    const renderedWidth = box.width * scale;
    const renderedHeight = box.height * scale;
    const x =
        target.x +
        (target.width - renderedWidth) / 2 -
        box.x * scale;
    const y =
        target.y +
        (target.height - renderedHeight) / 2 -
        box.y * scale;

    root.setAttribute(
        "transform",
        `translate(${x} ${y}) scale(${scale})`
    );

    /*
     * Counter-scale line widths so the final displayed weights exactly
     * match Australia's 31 / 15 / 18 SVG-unit hierarchy.
     */
    root.style.setProperty("--generated-map-scale", scale);
}

function positionRepositoryStartFinish() {
    if (!repositoryMap || !generatedTrack) return;

    const group = document.getElementById("repository-start-finish");
    const point = pointAtPercentage(authoredPercentage(0));
    const before = pointAtPercentage(authoredPercentage(99.8));
    const after = pointAtPercentage(authoredPercentage(0.2));

    let tx = after.x - before.x;
    let ty = after.y - before.y;
    const magnitude = Math.hypot(tx, ty) || 1;
    tx /= magnitude;
    ty /= magnitude;

    const nx = -ty;
    const ny = tx;
    const half = 18;

    const line = group.querySelector(".start-line");
    line.setAttribute("x1", point.x - nx * half);
    line.setAttribute("y1", point.y - ny * half);
    line.setAttribute("x2", point.x + nx * half);
    line.setAttribute("y2", point.y + ny * half);

    const label = group.querySelector(".map-label");
    label.setAttribute("x", point.x - nx * 30);
    label.setAttribute("y", point.y - ny * 30);
    label.setAttribute("text-anchor", "middle");
}

function markerPositionForSegment(segmentId) {
    if (!generatedTrack) {
        return markerPositions[segmentId] || null;
    }

    const segment = segmentLookup.get(segmentId);
    if (!segment) return null;

    const length = generatedTrack.getTotalLength();
    const midpointRaw =
        (Number(segment.start_pct) + Number(segment.end_pct)) / 2;
    const midpointPct = repositoryMap
        ? authoredPercentage(midpointRaw)
        : midpointRaw;
    const point = generatedTrack.getPointAtLength(
        length * midpointPct / 100
    );

    return [point.x, point.y];
}


const totalLaps = mapData.race.laps || Math.max(
    ...mapData.events.map((event) => event.lap)
);

let activeSegmentId = null;
let activeEventId = null;
let activeEventType = "all";

function eventsForSegment(segmentId) {
    return mapData.events
        .filter((event) => event.segment_id === segmentId)
        .sort((a, b) => a.lap - b.lap);
}

function eventColourClass(event) {
    return event.type.replaceAll("_", "-");
}

function createMapMarkers() {
    const counts = {};

    mapData.events.forEach((event) => {
        const position = markerPositionForSegment(event.segment_id);
        if (!position) return;

        const index = counts[event.segment_id] || 0;
        counts[event.segment_id] = index + 1;

        const circle = document.createElementNS(
            "http://www.w3.org/2000/svg",
            "circle"
        );

        const offset = generatedTrack ? 5 : 9;
        circle.setAttribute("cx", position[0] + index * offset);
        circle.setAttribute("cy", position[1] - index * offset);
        circle.setAttribute("r", "7");
        circle.classList.add(
            "event-marker",
            eventColourClass(event)
        );
        circle.dataset.segment = event.segment_id;
        circle.dataset.eventId = event.id;
        circle.setAttribute(
            "aria-label",
            `Lap ${event.lap}: ${event.title}`
        );

        circle.addEventListener("click", () => {
            selectEvent(event.id);
        });

        markerLayer.appendChild(circle);
    });
}

function mapEventCard(event) {
    const selected = event.id === activeEventId ? " selected" : "";
    const matchup = event.defender
        ? `<p class="map-event-matchup">
               <strong>${event.attacker}</strong> over ${event.defender}
           </p>`
        : `<p class="map-event-matchup">
               <strong>${event.attacker || event.title}</strong>
           </p>`;

    return `
        <button
            type="button"
            class="map-event-card ${eventColourClass(event)}${selected}"
            data-event-id="${event.id}"
        >
            <span class="map-event-meta">
                <span>Lap ${event.lap}</span>
                <span>${event.type_label || event.type}</span>
            </span>
            <strong class="map-event-title">${event.title}</strong>
            ${matchup}
            <span class="map-event-description">${event.description}</span>
        </button>
    `;
}

function renderSegment(segmentId, selectedEventId = null) {
    activeSegmentId = segmentId;
    activeEventId = selectedEventId;

    const segment = segmentLookup.get(segmentId);
    const events = eventsForSegment(segmentId);

    document.querySelectorAll("#segment-hotspots path").forEach((path) => {
        path.classList.toggle(
            "active",
            path.dataset.segment === segmentId
        );
    });

    document.querySelectorAll(".event-marker").forEach((marker) => {
        marker.classList.toggle(
            "selected",
            marker.dataset.eventId === activeEventId
        );
        marker.classList.toggle(
            "muted",
            marker.dataset.segment !== segmentId
        );
    });

    segmentName.textContent = segment.name;
    segmentKind.textContent =
        `${segment.kind === "corner" ? "Corner complex" : "Named straight or section"} · ` +
        `${events.length} featured ${events.length === 1 ? "event" : "events"}`;

    if (!events.length) {
        eventList.innerHTML = `
            <div class="segment-empty">
                No featured event has been assigned to this section yet.
            </div>
        `;
    } else {
        eventList.innerHTML = events.map(mapEventCard).join("");

        eventList.querySelectorAll(".map-event-card").forEach((button) => {
            button.addEventListener("click", () => {
                selectEvent(button.dataset.eventId);
            });
        });
    }
}

function timelineEvents() {
    return mapData.events
        .filter(
            (event) =>
                !activeSegmentId ||
                event.segment_id === activeSegmentId
        )
        .filter(
            (event) =>
                activeEventType === "all" ||
                event.type === activeEventType
        )
        .sort((a, b) => a.lap - b.lap);
}

function createTimelineDot(event) {
    const dot = document.createElement("button");
    dot.type = "button";
    dot.className =
        `timeline-dot ${eventColourClass(event)}`;
    dot.style.left =
        `${((event.lap - 1) / Math.max(totalLaps - 1, 1)) * 100}%`;
    dot.dataset.eventId = event.id;
    dot.dataset.segment = event.segment_id;
    dot.title = `Lap ${event.lap}: ${event.title}`;
    dot.setAttribute(
        "aria-label",
        `Lap ${event.lap}: ${event.title}`
    );

    if (event.id === activeEventId) {
        dot.classList.add("selected");
    }

    const hiddenBySegment =
        activeSegmentId && event.segment_id !== activeSegmentId;
    const hiddenByType =
        activeEventType !== "all" &&
        event.type !== activeEventType;

    if (hiddenBySegment || hiddenByType) {
        dot.classList.add("muted");
    }

    dot.addEventListener("click", () => selectEvent(event.id));
    return dot;
}

function timelineCard(event) {
    const segment = segmentLookup.get(event.segment_id);
    const selected = event.id === activeEventId ? " selected" : "";
    const matchup = event.defender
        ? `<span class="timeline-matchup">
               <strong>${event.attacker}</strong> over ${event.defender}
           </span>`
        : `<span class="timeline-matchup">
               <strong>${event.attacker || event.title}</strong>
           </span>`;

    return `
        <button
            type="button"
            class="timeline-event ${eventColourClass(event)}${selected}"
            data-event-id="${event.id}"
        >
            <span class="timeline-lap">
                <small>Lap</small>
                <strong>${event.lap}</strong>
            </span>

            <span class="timeline-card-dot" aria-hidden="true"></span>

            <span class="timeline-event-copy">
                <span class="timeline-event-topline">
                    <strong>${event.title}</strong>
                    <em>${event.type_label || event.type}</em>
                </span>
                <span class="timeline-location">${segment.name}</span>
                ${matchup}
                <span class="timeline-description">
                    ${event.description}
                </span>
            </span>
        </button>
    `;
}

function renderTimeline() {
    const events = timelineEvents();
    const segment = activeSegmentId
        ? segmentLookup.get(activeSegmentId)
        : null;

    timelineRail.innerHTML = "";
    mapData.events.forEach((event) => {
        timelineRail.appendChild(createTimelineDot(event));
    });

    timelineReset.hidden = !activeSegmentId && activeEventType === "all";

    if (segment) {
        timelineContext.textContent =
            `Showing events at ${segment.name}`;
    } else if (activeEventType !== "all") {
        const activeButton = document.querySelector(
            `.timeline-filter[data-event-type="${activeEventType}"]`
        );
        timelineContext.textContent =
            `Showing ${activeButton.textContent.trim().toLowerCase()}`;
    } else {
        timelineContext.textContent =
            "Showing all featured race events";
    }

    if (!events.length) {
        timelineList.innerHTML = `
            <div class="timeline-empty">
                No matching events are recorded.
            </div>
        `;
        return;
    }

    timelineList.innerHTML = events.map(timelineCard).join("");

    timelineList.querySelectorAll(".timeline-event").forEach((button) => {
        button.addEventListener("click", () => {
            selectEvent(button.dataset.eventId);
        });
    });
}

function selectEvent(eventId) {
    const event = eventLookup.get(eventId);
    if (!event) return;

    activeEventId = eventId;
    renderSegment(event.segment_id, eventId);
    renderTimeline();
}

function resetTimeline() {
    activeSegmentId = null;
    activeEventId = null;
    activeEventType = "all";

    document.querySelectorAll("#segment-hotspots path").forEach((path) => {
        path.classList.remove("active");
    });

    document.querySelectorAll(".event-marker").forEach((marker) => {
        marker.classList.remove("selected", "muted");
    });

    timelineFilters.forEach((button) => {
        button.classList.toggle(
            "active",
            button.dataset.eventType === "all"
        );
    });

    segmentName.textContent = "Choose a section";
    segmentKind.textContent =
        "Hover or click anywhere along the circuit.";
    eventList.innerHTML = `
        <div class="segment-empty">
            Event details will appear here.
        </div>
    `;

    renderTimeline();
}

document.querySelectorAll("#segment-hotspots path").forEach((path) => {
    const segment = segmentLookup.get(path.dataset.segment);

    function positionTooltip(event) {
        const stage = svg.closest(".circuit-stage");
        const bounds = stage.getBoundingClientRect();
        tooltip.style.left = `${event.clientX - bounds.left + 12}px`;
        tooltip.style.top = `${event.clientY - bounds.top + 12}px`;
    }

    path.addEventListener("mouseenter", (event) => {
        tooltip.hidden = false;
        tooltip.textContent = segment.name;
        positionTooltip(event);
    });

    path.addEventListener("mousemove", positionTooltip);

    path.addEventListener("mouseleave", () => {
        tooltip.hidden = true;
    });

    path.addEventListener("click", () => {
        activeEventId = null;
        renderSegment(path.dataset.segment);
        renderTimeline();
    });
});

svg.addEventListener("mouseleave", () => {
    tooltip.hidden = true;
});

timelineFilters.forEach((button) => {
    button.addEventListener("click", () => {
        activeEventType = button.dataset.eventType;
        activeEventId = null;

        timelineFilters.forEach((item) => {
            item.classList.toggle("active", item === button);
        });

        renderTimeline();
    });
});

timelineReset.addEventListener("click", resetTimeline);

if (repositoryMap) {
    buildAuthoredSegmentPaths();
    normalizeGeneratedMapToAustraliaCanvas();
    positionRepositoryStartFinish();
}
createMapMarkers();
renderTimeline();


// ---------------------------------------------------------------------
// Shared lap-by-lap playback for the authored Albert Park map.
// ---------------------------------------------------------------------
const authoredPlayButton = document.getElementById("timeline-play");
const authoredPreviousButton = document.getElementById("timeline-previous");
const authoredNextButton = document.getElementById("timeline-next");
const authoredCurrentLap = document.getElementById("timeline-current-lap");
const authoredSpeed = document.getElementById("timeline-speed");

const authoredEvents = [...mapData.events].sort(
    (a, b) => Number(a.lap) - Number(b.lap)
);

let authoredLap = 1;
let authoredPlaying = false;
let authoredTimer = null;
let authoredCursor = -1;

function authoredUpdatePlayButton() {
    authoredPlayButton.classList.toggle("playing", authoredPlaying);
    authoredPlayButton.querySelector(".play-icon").textContent =
        authoredPlaying ? "❚❚" : "▶";
    authoredPlayButton.querySelector(".play-label").textContent =
        authoredPlaying ? "Pause timeline" : "Play timeline";
}

function authoredPause() {
    if (authoredTimer) {
        window.clearTimeout(authoredTimer);
        authoredTimer = null;
    }
    authoredPlaying = false;
    authoredUpdatePlayButton();
}

function authoredMovePlayhead() {
    let playhead = document.querySelector(
        "#timeline-rail .timeline-playhead"
    );

    if (!playhead) {
        playhead = document.createElement("span");
        playhead.className = "timeline-playhead";
        document.getElementById("timeline-rail").appendChild(playhead);
    }

    playhead.style.left =
        `${((authoredLap - 1) / Math.max(totalLaps - 1, 1)) * 100}%`;
    authoredCurrentLap.textContent = authoredLap;
}

function authoredAdvance() {
    if (!authoredPlaying) return;

    if (authoredLap >= totalLaps) {
        authoredPause();
        return;
    }

    authoredLap += 1;
    const event = authoredEvents.find(
        (item) => Number(item.lap) === authoredLap
    );

    if (event) {
        authoredCursor = authoredEvents.findIndex(
            (candidate) => candidate.id === event.id
        );
        selectEvent(event.id);

        const mapMarker = document.querySelector(
            `.event-marker[data-event-id="${event.id}"]`
        );
        mapMarker?.classList.add("map-marker-pulse");
        window.setTimeout(
            () => mapMarker?.classList.remove("map-marker-pulse"),
            1200
        );
    }

    authoredMovePlayhead();

    const speed = Number(authoredSpeed.value || 1);
    authoredTimer = window.setTimeout(
        authoredAdvance,
        (event ? 1150 : 210) / speed
    );
}

function authoredStart() {
    if (authoredLap >= totalLaps) {
        authoredLap = 1;
        authoredCursor = -1;
        resetTimeline();
    }

    authoredPlaying = true;
    authoredUpdatePlayButton();
    authoredTimer = window.setTimeout(authoredAdvance, 100);
}

function authoredStep(direction) {
    authoredPause();

    if (direction > 0) {
        authoredCursor = Math.min(
            authoredCursor + 1,
            authoredEvents.length - 1
        );
    } else {
        authoredCursor = authoredCursor <= 0
            ? 0
            : authoredCursor - 1;
    }

    const event = authoredEvents[authoredCursor];
    authoredLap = Number(event.lap);
    selectEvent(event.id);
    authoredMovePlayhead();
}

authoredPlayButton.addEventListener("click", () => {
    if (authoredPlaying) {
        authoredPause();
    } else {
        authoredStart();
    }
});

authoredPreviousButton.addEventListener(
    "click",
    () => authoredStep(-1)
);

authoredNextButton.addEventListener(
    "click",
    () => authoredStep(1)
);

authoredMovePlayhead();
authoredUpdatePlayButton();
