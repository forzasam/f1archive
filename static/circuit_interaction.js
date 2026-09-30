document.addEventListener("DOMContentLoaded", () => {
  const dataNode = document.getElementById("circuit-map-data");
  if (!dataNode) return;

  const data = JSON.parse(dataNode.textContent);
  const section = dataNode.closest(".race-map-section");
  const stage = section.querySelector(".circuit-stage");
  const svg = stage.querySelector("#authored-circuit-svg");
  const canonical = svg && svg.querySelector("#canonical-track-path");
  const hotspotRoot = svg && svg.querySelector("#segment-hotspots");
  const labelRoot = svg && svg.querySelector("#authored-corner-labels");
  const sfRoot = svg && svg.querySelector("#authored-start-finish");
  const tooltip = stage.querySelector(".segment-tooltip");
  const title = section.querySelector("#selected-segment-name");
  const kind = section.querySelector("#selected-segment-kind");
  const NS = "http://www.w3.org/2000/svg";

  const source = data.source_path || {};
  const startFraction = Number(source.start_fraction || 0);
  const reverse = data.direction === "counterclockwise";

  function lapToSource(fraction) {
    const delta = reverse ? -fraction : fraction;
    return ((startFraction + delta) % 1 + 1) % 1;
  }

  function pointAtLap(fraction) {
    const length = canonical.getTotalLength();
    return canonical.getPointAtLength(lapToSource(fraction) * length);
  }

  function pathForRange(start, end) {
    let span = ((end - start) % 1 + 1) % 1;
    if (span === 0) span = 1;
    const steps = Math.max(8, Math.ceil(span * 320));
    const commands = [];
    for (let i = 0; i <= steps; i += 1) {
      const lap = (start + span * (i / steps)) % 1;
      const point = pointAtLap(lap);
      commands.push(`${i ? "L" : "M"}${point.x.toFixed(2)} ${point.y.toFixed(2)}`);
    }
    return commands.join(" ");
  }

  function addCornerLabel(root, fraction, text) {
    if (!root || !canonical) return;
    const p = pointAtLap(fraction);
    const label = document.createElementNS(NS, "text");
    label.setAttribute("class", "authored-corner-label");
    label.setAttribute("x", p.x + 7);
    label.setAttribute("y", p.y - 7);
    label.textContent = text;
    root.appendChild(label);
  }

  function addStartFinish(root) {
    if (!root || !canonical) return;
    const p = pointAtLap(0);
    const group = document.createElementNS(NS, "g");
    group.setAttribute("class", "authored-sf-marker");
    const circle = document.createElementNS(NS, "circle");
    circle.setAttribute("cx", p.x); circle.setAttribute("cy", p.y); circle.setAttribute("r", "4");
    const label = document.createElementNS(NS, "text");
    label.setAttribute("x", p.x + 8); label.setAttribute("y", p.y - 8); label.textContent = "S/F";
    group.append(circle, label); root.appendChild(group);
  }

  if (canonical && hotspotRoot) {
    (data.segments || []).forEach(segment => {
      const group = document.createElementNS(NS, "g");
      group.dataset.segment = segment.id;
      group.setAttribute("class", "segment-hotspot");
      const d = pathForRange(Number(segment.start), Number(segment.end));

      const highlight = document.createElementNS(NS, "path");
      highlight.setAttribute("class", "segment-highlight");
      highlight.setAttribute("d", d);
      highlight.setAttribute("aria-hidden", "true");

      const hit = document.createElementNS(NS, "path");
      hit.setAttribute("class", "segment-hit-target");
      hit.dataset.segment = segment.id;
      hit.setAttribute("d", d);
      hit.setAttribute("tabindex", "0");
      hit.setAttribute("role", "button");
      hit.setAttribute("aria-label", segment.name);
      hit.setAttribute("aria-pressed", "false");

      group.append(highlight, hit);
      hotspotRoot.appendChild(group);
    });
    (data.corners || []).forEach(corner => addCornerLabel(labelRoot, Number(corner.position), String(corner.number)));
    addStartFinish(sfRoot);
  }

  const lookup = new Map((data.segments || []).map(item => [item.id, item]));
  const paths = [...stage.querySelectorAll("#segment-hotspots .segment-hit-target")];
  let selectedPath = null;

  function moveTooltip(event) {
    if (!event.clientX && !event.clientY) return;
    const box = stage.getBoundingClientRect();
    tooltip.style.left = `${event.clientX - box.left + 12}px`;
    tooltip.style.top = `${event.clientY - box.top + 12}px`;
  }
  function hideTooltip() {
    tooltip.hidden = true;
    tooltip.style.display = "none";
  }

  function show(path, event) {
    const segment = lookup.get(path.dataset.segment);
    if (!segment) return;
    tooltip.hidden = false;
    tooltip.style.display = "";
    tooltip.textContent = segment.name;
    if (event) moveTooltip(event);
  }
  function resetPanel() {
    title.textContent = "Explore the circuit";
    kind.textContent = "Hover to preview a named section, or click to keep it selected.";
  }

  function setGroupState(path, className, enabled) {
    const group = path.closest(".segment-hotspot");
    if (group) group.classList.toggle(className, enabled);
  }

  function select(path) {
    const segment = lookup.get(path.dataset.segment);
    if (!segment) return;

    if (selectedPath === path) {
      setGroupState(path, "active", false);
      path.setAttribute("aria-pressed", "false");
      selectedPath = null;
      resetPanel();
      return;
    }

    if (selectedPath) {
      setGroupState(selectedPath, "active", false);
      selectedPath.setAttribute("aria-pressed", "false");
    }

    selectedPath = path;
    setGroupState(path, "active", true);
    path.setAttribute("aria-pressed", "true");
    title.textContent = segment.name;
    kind.textContent = segment.kind === "corner" ? "Corner" : segment.kind === "straight" ? "Straight" : "Track section";
  }

  paths.forEach(path => {
    path.addEventListener("mouseenter", event => {
      if (path.dataset.suppressHover === "true") return;
      setGroupState(path, "hovered", true);
      show(path, event);
    });
    path.addEventListener("mousemove", event => {
      if (path.dataset.suppressHover !== "true") moveTooltip(event);
    });
    path.addEventListener("mouseleave", () => {
      setGroupState(path, "hovered", false);
      hideTooltip();
      delete path.dataset.suppressHover;
    });
    path.addEventListener("click", () => {
      const wasSelected = selectedPath === path;
      select(path);

      // A second click is an explicit "close" action. Hide the hover nameplate
      // immediately even though the pointer is physically still over the segment.
      // It may appear again only after the pointer genuinely leaves and re-enters.
      if (wasSelected) {
        hideTooltip();
        setGroupState(path, "hovered", false);
        path.dataset.suppressHover = "true";
      }

      // Pointer clicks should not leave keyboard focus looking like a selection.
      if (document.activeElement === path) path.blur();
    });
    path.addEventListener("focus", () => { setGroupState(path, "hovered", true); show(path); });
    path.addEventListener("blur", () => { setGroupState(path, "hovered", false); hideTooltip(); });
    path.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); select(path); }
      else if (event.key === "Escape" && selectedPath === path) select(path);
    });
  });

  // Optional race-story layer. Circuit geometry remains the source of truth;
  // this layer only references normalized positions and authored segment IDs.
  const storyNode = document.getElementById("race-story-map-data");
  if (storyNode && canonical) {
    const story = JSON.parse(storyNode.textContent);
    const events = [...(story.events || [])].sort((a, b) => Number(a.order) - Number(b.order));
    const modeButtons = [...section.querySelectorAll(".circuit-mode")];
    const explorePanel = section.querySelector("#explore-panel-content");
    const storyPanel = section.querySelector("#story-panel-content");
    const markerLayer = section.querySelector("#race-story-markers");
    const rail = section.querySelector("#story-step-rail");
    const eventLabel = section.querySelector("#story-event-label");
    const eventLap = section.querySelector("#story-event-lap");
    const eventTitle = section.querySelector("#story-event-title");
    const eventDescription = section.querySelector("#story-event-description");
    const progressText = section.querySelector("#story-progress-text");
    const prevButton = section.querySelector("#story-prev");
    const nextButton = section.querySelector("#story-next");
    let storyIndex = -1;
    let storyMode = false;

    function clearStoryHighlight() {
      stage.classList.remove("story-whole-circuit");
      stage.querySelectorAll(".segment-hotspot.story-active").forEach(group => group.classList.remove("story-active"));
    }

    function clearExploreSelection() {
      if (selectedPath) {
        setGroupState(selectedPath, "active", false);
        selectedPath.setAttribute("aria-pressed", "false");
        selectedPath = null;
      }
      paths.forEach(path => setGroupState(path, "hovered", false));
      hideTooltip();
      resetPanel();
    }

    function eventLapText(event) {
      return `Lap ${event.lap}`;
    }

    function renderStoryEvent(index) {
      if (!events.length) return;
      storyIndex = Math.max(0, Math.min(index, events.length - 1));
      const event = events[storyIndex];
      clearStoryHighlight();

      if (event.scope === "whole_circuit") stage.classList.add("story-whole-circuit");
      (event.segments || []).forEach(id => {
        const group = stage.querySelector(`.segment-hotspot[data-segment="${CSS.escape(id)}"]`);
        if (group) group.classList.add("story-active");
      });

      eventLabel.textContent = event.label || "Race story";
      eventLap.textContent = eventLapText(event);
      eventTitle.textContent = event.title;
      eventDescription.textContent = event.description;
      progressText.textContent = `${storyIndex + 1} / ${events.length}`;
      prevButton.disabled = storyIndex === 0;
      nextButton.textContent = storyIndex === events.length - 1 ? "Finish story" : "Next moment →";

      markerLayer.querySelectorAll(".race-story-marker").forEach((marker, i) => {
        marker.classList.toggle("active", i === storyIndex);
        marker.classList.toggle("visited", i < storyIndex);
      });
      rail.querySelectorAll(".story-step").forEach((step, i) => step.classList.toggle("active", i === storyIndex));
    }

    function positionStoryMarkers() {
      const stageBox = stage.getBoundingClientRect();
      events.forEach((event, index) => {
        const marker = markerLayer.querySelector(`[data-story-index="${index}"]`);
        if (!marker) return;
        const point = pointAtLap(Number(event.position || 0));
        const svgPoint = svg.createSVGPoint();
        svgPoint.x = point.x; svgPoint.y = point.y;
        const screenPoint = svgPoint.matrixTransform(svg.getScreenCTM());
        marker.style.left = `${screenPoint.x - stageBox.left}px`;
        marker.style.top = `${screenPoint.y - stageBox.top}px`;
      });
    }

    events.forEach((event, index) => {
      const marker = document.createElement("button");
      marker.type = "button";
      marker.className = "circuit-story-marker";
      marker.dataset.storyIndex = String(index);
      marker.textContent = String(event.order || index + 1);
      marker.title = `${eventLapText(event)} — ${event.title}`;
      marker.setAttribute("aria-label", marker.title);
      marker.addEventListener("click", () => renderStoryEvent(index));
      markerLayer.appendChild(marker);

      const step = document.createElement("button");
      step.type = "button";
      step.className = "story-step";
      step.innerHTML = `<span>${eventLapText(event)}</span><strong>${event.label || event.title}</strong>`;
      step.addEventListener("click", () => renderStoryEvent(index));
      rail.appendChild(step);
    });

    function setMode(mode) {
      storyMode = mode === "story";
      section.classList.toggle("story-mode", storyMode);
      modeButtons.forEach(button => {
        const active = button.dataset.mapMode === mode;
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
      });
      explorePanel.hidden = storyMode;
      storyPanel.hidden = !storyMode;
      markerLayer.hidden = !storyMode;
      rail.hidden = !storyMode;

      if (storyMode) {
        clearExploreSelection();
        if (storyIndex < 0) {
          eventLabel.textContent = story.context || "Race story";
          eventLap.textContent = "";
          eventTitle.textContent = story.title;
          eventDescription.textContent = story.context || "Select Begin story to follow the featured moments.";
          progressText.textContent = `0 / ${events.length}`;
          prevButton.disabled = true;
          nextButton.textContent = "Begin story →";
        } else renderStoryEvent(storyIndex);
        requestAnimationFrame(positionStoryMarkers);
      } else {
        clearStoryHighlight();
        resetPanel();
      }
    }

    modeButtons.forEach(button => button.addEventListener("click", () => setMode(button.dataset.mapMode)));
    prevButton.addEventListener("click", () => { if (storyIndex > 0) renderStoryEvent(storyIndex - 1); });
    nextButton.addEventListener("click", () => {
      if (storyIndex < 0) renderStoryEvent(0);
      else if (storyIndex < events.length - 1) renderStoryEvent(storyIndex + 1);
      else setMode("explore");
    });
    window.addEventListener("resize", () => { if (storyMode) positionStoryMarkers(); });
  }

});
