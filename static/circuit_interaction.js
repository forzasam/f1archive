document.addEventListener("DOMContentLoaded", () => {
  const dataNode = document.getElementById("circuit-map-data");
  if (!dataNode) return;
  const data = JSON.parse(dataNode.textContent);
  const lookup = new Map((data.segments || []).map(item => [item.id, item]));
  const stage = dataNode.closest(".race-map-section").querySelector(".circuit-stage");
  const tooltip = stage.querySelector(".segment-tooltip");
  const title = document.getElementById("selected-segment-name");
  const kind = document.getElementById("selected-segment-kind");
  stage.querySelectorAll("#segment-hotspots path").forEach(path => {
    const segment = lookup.get(path.dataset.segment);
    if (!segment) return;
    const move = event => { const box = stage.getBoundingClientRect(); tooltip.style.left = `${event.clientX-box.left+12}px`; tooltip.style.top = `${event.clientY-box.top+12}px`; };
    path.addEventListener("mouseenter", event => { tooltip.hidden=false; tooltip.textContent=segment.name; move(event); });
    path.addEventListener("mousemove", move);
    path.addEventListener("mouseleave", () => { tooltip.hidden=true; });
    path.addEventListener("click", () => { stage.querySelectorAll("#segment-hotspots path").forEach(p=>p.classList.remove("active")); path.classList.add("active"); title.textContent=segment.name; kind.textContent=segment.kind === "corner" ? "Corner or corner complex" : "Named straight"; });
  });
});
