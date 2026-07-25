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
// Editorial race-story playback.
// ---------------------------------------------------------------------
const authoredPlayButton = document.getElementById("timeline-play");
const authoredPreviousButton = document.getElementById("timeline-previous");
const authoredNextButton = document.getElementById("timeline-next");
const authoredCurrentLap = document.getElementById("timeline-current-lap");
const authoredPhaseLabel = document.getElementById("timeline-phase-label");
const authoredSpeed = document.getElementById("timeline-speed");
const storyOverlay = document.getElementById("story-event-overlay");
const storyLap = document.getElementById("story-event-lap");
const storyCategory = document.getElementById("story-event-category");
const storyTitle = document.getElementById("story-event-title");
const storyBody = document.getElementById("story-event-body");
const storyFrameCaption = document.getElementById("story-frame-caption");
const storyContinue = document.getElementById("story-continue");

const DRIVER_COLOURS = [
    "#ff3b30", "#5ac8fa", "#ffcc00", "#34c759", "#af52de",
    "#ff9500", "#64d2ff", "#ff6482", "#30d158", "#bf5af2"
];

const authoredEvents = [...mapData.events].sort((a, b) => {
    const lapDifference = Number(a.lap || 0) - Number(b.lap || 0);
    return lapDifference || String(a.id).localeCompare(String(b.id));
});

const storySequence = [];
if (mapData.pre_race) {
    storySequence.push({
        ...mapData.pre_race,
        id: mapData.pre_race.id || "pre-race",
        phase: "pre-race",
        lap: 0,
        type_label: mapData.pre_race.type_label || "Pre-race"
    });
}
storySequence.push(...authoredEvents);

let authoredLap = 0;
let authoredPlaying = false;
let authoredTimer = null;
let authoredCursor = -1;
let storyPausedAtEvent = false;
let activeFrameTimers = [];
let storyMarkerLayer = null;

function safeText(value) {
    return value == null ? "" : String(value);
}

function driverColour(driver, marker, index) {
    if (marker?.colour) return marker.colour;
    const driverColours = mapData.driver_colours || {};
    if (driver && driverColours[driver]) return driverColours[driver];
    let hash = 0;
    for (const character of safeText(driver)) {
        hash = ((hash << 5) - hash) + character.charCodeAt(0);
        hash |= 0;
    }
    return DRIVER_COLOURS[Math.abs(hash || index) % DRIVER_COLOURS.length];
}

function ensureStoryMarkerLayer() {
    if (storyMarkerLayer?.isConnected) return storyMarkerLayer;
    storyMarkerLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    storyMarkerLayer.id = "story-markers";
    storyMarkerLayer.setAttribute("aria-hidden", "true");
    svg.appendChild(storyMarkerLayer);
    return storyMarkerLayer;
}

function clearFrameTimers() {
    activeFrameTimers.forEach((timer) => window.clearTimeout(timer));
    activeFrameTimers = [];
}

function clearStoryMarkers() {
    clearFrameTimers();
    ensureStoryMarkerLayer().replaceChildren();
}

function markerBasePosition(marker, event) {
    if (Number.isFinite(Number(marker.x)) && Number.isFinite(Number(marker.y))) {
        return [Number(marker.x), Number(marker.y)];
    }
    const segmentId = marker.segment_id || event.segment_id;
    const base = markerPositionForSegment(segmentId) || [512, 288];
    return [
        base[0] + Number(marker.dx || 0),
        base[1] + Number(marker.dy || 0)
    ];
}

function fallbackMarkers(event) {
    const drivers = [event.attacker, event.defender].filter(Boolean);
    if (!drivers.length) {
        return [{ driver: event.title, segment_id: event.segment_id }];
    }
    return drivers.map((driver, index) => ({
        driver,
        segment_id: event.segment_id,
        dx: index * 24 - ((drivers.length - 1) * 12),
        dy: index % 2 ? -12 : 10
    }));
}

function eventFrames(event) {
    if (Array.isArray(event.frames) && event.frames.length) return event.frames;
    if (Array.isArray(event.markers) && event.markers.length) {
        return [{ markers: event.markers, caption: event.frame_caption }];
    }
    return [{ markers: fallbackMarkers(event) }];
}

function renderStoryFrame(event, frame) {
    const layer = ensureStoryMarkerLayer();
    layer.replaceChildren();
    const markers = Array.isArray(frame.markers) ? frame.markers : [];

    markers.forEach((marker, index) => {
        const [x, y] = markerBasePosition(marker, event);
        const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
        group.classList.add("story-driver-marker", "map-marker-pulse");
        group.style.setProperty("--driver-colour", driverColour(marker.driver, marker, index));
        group.setAttribute("transform", `translate(${x} ${y})`);

        const halo = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        halo.setAttribute("r", "15");
        halo.classList.add("story-driver-halo");

        const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        dot.setAttribute("r", "9");
        dot.classList.add("story-driver-dot");

        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", "14");
        label.setAttribute("y", "4");
        label.classList.add("story-driver-label");
        label.textContent = marker.label || marker.code || safeText(marker.driver).split(" ").pop();

        group.append(halo, dot, label);
        layer.appendChild(group);
    });

    const caption = frame.caption || "";
    storyFrameCaption.textContent = caption;
    storyFrameCaption.hidden = !caption;
}

function playStoryFrames(event) {
    clearFrameTimers();
    const frames = eventFrames(event);
    const speed = Number(authoredSpeed.value || 1);
    let elapsed = 0;

    frames.forEach((frame, index) => {
        const timer = window.setTimeout(() => {
            renderStoryFrame(event, frame);
        }, elapsed);
        activeFrameTimers.push(timer);
        const duration = Number(frame.duration_ms || 1400) / speed;
        if (index < frames.length - 1) elapsed += Math.max(duration, 350);
    });
}

function showStoryCard(event) {
    storyLap.textContent = event.phase === "pre-race"
        ? "Pre-race"
        : `Lap ${event.lap}`;
    storyCategory.textContent = event.type_label || event.type || "Race story";
    storyTitle.textContent = event.title || "The race begins";
    storyBody.textContent = event.body || event.description || "";
    storyFrameCaption.hidden = true;
    storyOverlay.hidden = false;
    window.requestAnimationFrame(() => storyOverlay.classList.add("visible"));
    document.querySelectorAll(".event-marker").forEach((marker) => {
        marker.classList.add("story-hidden");
    });
    playStoryFrames(event);
}

function hideStoryCard({ clearMarkers = true } = {}) {
    storyOverlay.classList.remove("visible");
    const timer = window.setTimeout(() => {
        storyOverlay.hidden = true;
    }, 220);
    activeFrameTimers.push(timer);
    if (clearMarkers) clearStoryMarkers();
    document.querySelectorAll(".event-marker").forEach((marker) => {
        marker.classList.remove("story-hidden");
    });
}

function authoredUpdatePlayButton() {
    authoredPlayButton.classList.toggle("playing", authoredPlaying);
    const icon = authoredPlayButton.querySelector(".play-icon");
    const label = authoredPlayButton.querySelector(".play-label");

    if (storyPausedAtEvent) {
        icon.textContent = "▶";
        label.textContent = "Continue story";
    } else if (authoredPlaying) {
        icon.textContent = "❚❚";
        label.textContent = "Pause timeline";
    } else if (authoredLap === 0 && authoredCursor < 0) {
        icon.textContent = "▶";
        label.textContent = "Begin story";
    } else {
        icon.textContent = "▶";
        label.textContent = "Resume timeline";
    }
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
    let playhead = document.querySelector("#timeline-rail .timeline-playhead");
    if (!playhead) {
        playhead = document.createElement("span");
        playhead.className = "timeline-playhead";
        timelineRail.appendChild(playhead);
    }
    const displayLap = Math.max(authoredLap, 1);
    playhead.style.left = `${((displayLap - 1) / Math.max(totalLaps - 1, 1)) * 100}%`;
    authoredCurrentLap.textContent = authoredLap;
    authoredPhaseLabel.textContent = authoredLap === 0 ? "Race phase" : "Current lap";
    if (authoredLap === 0) authoredCurrentLap.textContent = "Pre-race";
}

function pauseForStoryEvent(event, cursor) {
    authoredCursor = cursor;
    authoredLap = Number(event.lap || 0);
    storyPausedAtEvent = true;
    authoredPlaying = false;
    if (event.phase !== "pre-race" && event.segment_id) selectEvent(event.id);
    showStoryCard(event);
    authoredMovePlayhead();
    authoredUpdatePlayButton();
}

function nextStoryIndexAfter(lap, cursor) {
    for (let index = cursor + 1; index < storySequence.length; index += 1) {
        if (Number(storySequence[index].lap || 0) <= lap) return index;
        break;
    }
    return -1;
}

function authoredAdvance() {
    if (!authoredPlaying) return;

    const eventIndex = nextStoryIndexAfter(authoredLap, authoredCursor);
    if (eventIndex >= 0) {
        pauseForStoryEvent(storySequence[eventIndex], eventIndex);
        return;
    }

    if (authoredLap >= totalLaps) {
        authoredPause();
        authoredPlayButton.querySelector(".play-label").textContent = "Replay story";
        return;
    }

    authoredLap += 1;
    authoredMovePlayhead();

    const speed = Number(authoredSpeed.value || 1);
    authoredTimer = window.setTimeout(authoredAdvance, 260 / speed);
}

function authoredStart() {
    if (storyPausedAtEvent) {
        storyPausedAtEvent = false;
        hideStoryCard();
    }

    if (authoredLap >= totalLaps) {
        authoredLap = 0;
        authoredCursor = -1;
        resetTimeline();
    }

    authoredPlaying = true;
    authoredUpdatePlayButton();
    authoredTimer = window.setTimeout(authoredAdvance, 120);
}

function authoredStep(direction) {
    authoredPause();
    hideStoryCard();
    storyPausedAtEvent = false;

    if (!storySequence.length) return;
    if (direction > 0) {
        authoredCursor = Math.min(authoredCursor + 1, storySequence.length - 1);
    } else {
        authoredCursor = authoredCursor <= 0 ? 0 : authoredCursor - 1;
    }

    const event = storySequence[authoredCursor];
    pauseForStoryEvent(event, authoredCursor);
}

authoredPlayButton.addEventListener("click", () => {
    if (authoredPlaying) authoredPause();
    else authoredStart();
});

storyContinue.addEventListener("click", authoredStart);
authoredPreviousButton.addEventListener("click", () => authoredStep(-1));
authoredNextButton.addEventListener("click", () => authoredStep(1));

document.addEventListener("keydown", (event) => {
    if (event.key === " " && document.activeElement?.tagName !== "SELECT") {
        event.preventDefault();
        if (authoredPlaying) authoredPause();
        else authoredStart();
    }
});

authoredMovePlayhead();
authoredUpdatePlayButton();
