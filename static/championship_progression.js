(() => {
    "use strict";

    const root = document.querySelector("[data-position-progression]");
    const dataElement = document.getElementById("position-progression-data");
    if (!root || !dataElement) return;

    let model;
    try {
        model = JSON.parse(dataElement.textContent);
    } catch (error) {
        console.error("Could not parse championship progression data", error);
        return;
    }

    const svg = root.querySelector("[data-progression-chart]");
    const legend = root.querySelector("[data-progression-legend]");
    const tooltip = root.querySelector("[data-progression-tooltip]");
    const resetButton = root.querySelector("[data-progression-reset]");
    const collapseButton = document.querySelector("[data-progression-collapse]");
    const selected = new Set(model.default_driver_ids || []);
    const SVG_NS = "http://www.w3.org/2000/svg";

    const createSvg = (name, attributes = {}) => {
        const element = document.createElementNS(SVG_NS, name);
        Object.entries(attributes).forEach(([key, value]) => {
            element.setAttribute(key, String(value));
        });
        return element;
    };

    const ordinal = (value) => {
        const number = Number(value);
        const mod100 = number % 100;
        if (mod100 >= 11 && mod100 <= 13) return `${number}th`;
        if (number % 10 === 1) return `${number}st`;
        if (number % 10 === 2) return `${number}nd`;
        if (number % 10 === 3) return `${number}rd`;
        return `${number}th`;
    };

    const renderLegend = () => {
        legend.replaceChildren();
        model.drivers.forEach((driver) => {
            const label = document.createElement("label");
            label.className = "progression-driver-toggle";
            label.style.setProperty("--driver-colour", driver.team_colour);

            const input = document.createElement("input");
            input.type = "checkbox";
            input.checked = selected.has(driver.driver_id);
            input.value = driver.driver_id;
            input.addEventListener("change", () => {
                if (input.checked) selected.add(driver.driver_id);
                else selected.delete(driver.driver_id);
                renderChart();
            });

            const swatch = document.createElement("span");
            swatch.className = "progression-driver-swatch";
            swatch.setAttribute("aria-hidden", "true");

            const text = document.createElement("span");
            text.textContent = `${driver.driver_code} · ${driver.driver_name}`;

            label.append(input, swatch, text);
            legend.append(label);
        });
    };

    const showTooltip = (event, driver, round, position, points) => {
        tooltip.hidden = false;
        tooltip.innerHTML = `
            <strong>${driver.driver_name}</strong>
            <span>${round.race_name}</span>
            <span>${ordinal(position)} in championship · ${points} pts</span>
        `;

        const rootRect = root.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        let left = event.clientX - rootRect.left + 14;
        let top = event.clientY - rootRect.top + 14;
        left = Math.min(left, rootRect.width - tooltipRect.width - 12);
        top = Math.min(top, rootRect.height - tooltipRect.height - 12);
        tooltip.style.left = `${Math.max(12, left)}px`;
        tooltip.style.top = `${Math.max(12, top)}px`;
    };

    const hideTooltip = () => {
        tooltip.hidden = true;
    };

    const renderChart = () => {
        const containerWidth = svg.parentElement.clientWidth || 900;
        const width = Math.max(720, containerWidth);
        const height = Math.max(520, Math.min(700, model.max_position * 25 + 150));
        const margin = { top: 30, right: 38, bottom: 92, left: 54 };
        const plotWidth = width - margin.left - margin.right;
        const plotHeight = height - margin.top - margin.bottom;
        const rounds = model.rounds || [];
        const maxPosition = Math.max(1, model.max_position || 1);

        svg.replaceChildren();
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        svg.setAttribute("height", String(height));

        const x = (index) => margin.left + (
            rounds.length <= 1 ? plotWidth / 2 : index * plotWidth / (rounds.length - 1)
        );
        const y = (position) => margin.top + (
            maxPosition <= 1 ? 0 : (position - 1) * plotHeight / (maxPosition - 1)
        );

        const grid = createSvg("g", { class: "progression-grid" });
        const tickStep = maxPosition > 15 ? 2 : 1;
        for (let position = 1; position <= maxPosition; position += tickStep) {
            const rowY = y(position);
            grid.append(createSvg("line", {
                x1: margin.left,
                y1: rowY,
                x2: width - margin.right,
                y2: rowY,
            }));
            const label = createSvg("text", {
                x: margin.left - 14,
                y: rowY + 4,
                "text-anchor": "end",
            });
            label.textContent = position;
            grid.append(label);
        }
        svg.append(grid);

        const axis = createSvg("g", { class: "progression-axis" });
        const labelFrequency = width < 900 ? Math.ceil(rounds.length / 10) : Math.ceil(rounds.length / 16);
        rounds.forEach((round, index) => {
            const columnX = x(index);
            axis.append(createSvg("line", {
                x1: columnX,
                y1: margin.top,
                x2: columnX,
                y2: height - margin.bottom,
            }));
            if (index % Math.max(1, labelFrequency) === 0 || index === rounds.length - 1) {
                const label = createSvg("text", {
                    x: columnX,
                    y: height - margin.bottom + 20,
                    transform: `rotate(-38 ${columnX} ${height - margin.bottom + 20})`,
                    "text-anchor": "end",
                });
                label.textContent = round.short_name;
                axis.append(label);
            }
        });
        svg.append(axis);

        const activeDrivers = model.drivers.filter((driver) => selected.has(driver.driver_id));
        activeDrivers.slice().reverse().forEach((driver) => {
            const points = rounds.map((round, index) => {
                const position = driver.positions[String(round.round)];
                if (!position || position >= 999) return null;
                return {
                    x: x(index),
                    y: y(position),
                    position,
                    round,
                    points: driver.points[String(round.round)] ?? 0,
                };
            });

            let segment = [];
            const flushSegment = () => {
                if (segment.length < 2) {
                    segment = [];
                    return;
                }
                const d = segment.map((point, index) => (
                    `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`
                )).join(" ");
                const path = createSvg("path", {
                    d,
                    class: "progression-line",
                    stroke: driver.team_colour,
                    "data-driver-id": driver.driver_id,
                });
                svg.append(path);
                segment = [];
            };

            points.forEach((point) => {
                if (point) segment.push(point);
                else flushSegment();
            });
            flushSegment();

            points.forEach((point) => {
                if (!point) return;
                const circle = createSvg("circle", {
                    cx: point.x,
                    cy: point.y,
                    r: 5,
                    fill: driver.team_colour,
                    class: "progression-point",
                    tabindex: 0,
                    role: "button",
                    "aria-label": `${driver.driver_name}, ${point.round.race_name}, ${ordinal(point.position)}, ${point.points} points`,
                });
                circle.addEventListener("pointerenter", (event) => {
                    showTooltip(event, driver, point.round, point.position, point.points);
                });
                circle.addEventListener("pointermove", (event) => {
                    showTooltip(event, driver, point.round, point.position, point.points);
                });
                circle.addEventListener("pointerleave", hideTooltip);
                circle.addEventListener("focus", () => {
                    const rect = circle.getBoundingClientRect();
                    showTooltip(
                        { clientX: rect.left + rect.width / 2, clientY: rect.top },
                        driver,
                        point.round,
                        point.position,
                        point.points,
                    );
                });
                circle.addEventListener("blur", hideTooltip);
                svg.append(circle);
            });
        });

        if (!activeDrivers.length) {
            const empty = createSvg("text", {
                x: width / 2,
                y: height / 2,
                class: "progression-empty",
                "text-anchor": "middle",
            });
            empty.textContent = "Select at least one driver below";
            svg.append(empty);
        }
    };


    collapseButton?.addEventListener("click", () => {
        const willCollapse = !root.hidden;
        root.hidden = willCollapse;
        collapseButton.setAttribute("aria-expanded", String(!willCollapse));
        collapseButton.textContent = willCollapse ? "Expand" : "Minimise";

        if (!willCollapse) {
            window.requestAnimationFrame(renderChart);
        } else {
            hideTooltip();
        }
    });

    resetButton?.addEventListener("click", () => {
        selected.clear();
        (model.default_driver_ids || []).forEach((id) => selected.add(id));
        renderLegend();
        renderChart();
    });

    let resizeTimer;
    window.addEventListener("resize", () => {
        window.clearTimeout(resizeTimer);
        resizeTimer = window.setTimeout(renderChart, 120);
    });

    renderLegend();
    renderChart();
})();
