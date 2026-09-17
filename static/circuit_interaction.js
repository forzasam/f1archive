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
});
