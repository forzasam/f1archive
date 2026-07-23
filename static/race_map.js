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

const markerPositions = mapData.marker_positions || {};

function markerPositionForSegment(segmentId) {
    return markerPositions[segmentId] || null;
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

        const offset = 9;
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
