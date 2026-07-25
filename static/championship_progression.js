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
    const replayButton = root.querySelector("[data-progression-replay]");
    const collapseButton = document.querySelector("[data-progression-collapse]");
    const selected = new Set(model.default_driver_ids || []);
    const SVG_NS = "http://www.w3.org/2000/svg";

    let pinnedDriverId = null;
    let pinnedConstructorId = null;
    let hoveredDriverId = null;

    let replayFrame = null;
    let replayRunning = false;
    let replayRoundIndex = null;
    let replayProgress = 0;
    let replayWinnerDriverId = null;

    const REPLAY_DRAW_MS = 720;
    const REPLAY_WINNER_MS = 480;
    const REPLAY_HOLD_MS = 520;

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

    const easeInOutCubic = (value) => (
        value < 0.5
            ? 4 * value * value * value
            : 1 - Math.pow(-2 * value + 2, 3) / 2
    );

    const driverIsFocused = (driver) => {
        if (pinnedConstructorId) return driver.constructor_id === pinnedConstructorId;
        if (pinnedDriverId) return driver.driver_id === pinnedDriverId;
        if (hoveredDriverId) return driver.driver_id === hoveredDriverId;
        return true;
    };

    const hasFocus = () => Boolean(
        pinnedDriverId || pinnedConstructorId || hoveredDriverId
    );

    const applyHoverFocus = () => {
        const focusActive = hasFocus();
        svg.querySelectorAll("[data-driver-id]").forEach((element) => {
            const driver = model.drivers.find(
                (item) => item.driver_id === element.dataset.driverId
            );
            if (!driver) return;

            const focused = driverIsFocused(driver);
            element.classList.toggle("is-focused", focusActive && focused);
            element.classList.toggle("is-faded", focusActive && !focused);
        });
    };

    const setPinned = (driver, teammates = false) => {
        if (replayRunning) return;

        if (teammates) {
            const same = pinnedConstructorId === driver.constructor_id;
            pinnedConstructorId = same ? null : driver.constructor_id;
            pinnedDriverId = null;
        } else {
            const same = pinnedDriverId === driver.driver_id;
            pinnedDriverId = same ? null : driver.driver_id;
            pinnedConstructorId = null;
        }

        renderLegend();
        renderChart();
    };

    const renderLegend = () => {
        legend.replaceChildren();

        model.drivers.forEach((driver) => {
            const label = document.createElement("label");
            label.className = "progression-driver-toggle";

            if (
                pinnedDriverId === driver.driver_id ||
                (
                    pinnedConstructorId &&
                    pinnedConstructorId === driver.constructor_id
                )
            ) {
                label.classList.add("is-pinned");
            }

            label.style.setProperty("--driver-colour", driver.team_colour);

            const input = document.createElement("input");
            input.type = "checkbox";
            input.checked = selected.has(driver.driver_id);
            input.value = driver.driver_id;
            input.disabled = replayRunning;
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
            label.title = (
                "Click the graph line to pin this driver; " +
                "Shift-click to compare teammates"
            );
            legend.append(label);
        });
    };

    const showTooltip = (event, html) => {
        if (replayRunning) return;

        tooltip.hidden = false;
        tooltip.innerHTML = html;

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

    const driverTooltip = (
        event,
        driver,
        round,
        position,
        points
    ) => showTooltip(event, `
        <strong>${driver.driver_name}</strong>
        <span>${round.race_name}</span>
        <span>${ordinal(position)} in championship · ${points} pts</span>
        <span class="progression-tooltip-hint">
            Click to pin · Shift-click for teammates
        </span>
    `);

    const roundTooltip = (event, round) => {
        const standings = model.drivers
            .filter((driver) => (
                selected.has(driver.driver_id) &&
                driver.positions[String(round.round)] < 999
            ))
            .sort((a, b) => (
                a.positions[String(round.round)] -
                b.positions[String(round.round)]
            ))
            .slice(0, 8);

        const rows = standings.map((driver) => `
            <span>
                <b>${driver.driver_code}</b>
                P${driver.positions[String(round.round)]}
                · ${driver.points[String(round.round)] ?? 0} pts
            </span>
        `).join("");

        showTooltip(
            event,
            `<strong>${round.race_name}</strong>` +
            `<span>Championship snapshot</span>${rows}`
        );
    };

    const cancelReplayFrame = () => {
        if (replayFrame !== null) {
            window.cancelAnimationFrame(replayFrame);
            replayFrame = null;
        }
    };

    const stopReplay = ({ keepPosition = false } = {}) => {
        cancelReplayFrame();
        replayRunning = false;
        replayWinnerDriverId = null;

        if (!keepPosition) {
            replayRoundIndex = null;
            replayProgress = 0;
        }

        if (replayButton) {
            replayButton.textContent = keepPosition
                ? "Replay again"
                : "Relive the championship";
            replayButton.classList.remove("is-playing");
        }

        renderLegend();
    };

    const winnerForRound = (roundIndex) => {
        const round = model.rounds?.[roundIndex];
        if (!round) return null;

        return model.drivers.find((driver) => (
            selected.has(driver.driver_id) &&
            driver.finishes?.[String(round.round)] === 1
        )) || null;
    };

    const animatePhase = (duration, update) => new Promise((resolve) => {
        const started = performance.now();

        const tick = (now) => {
            if (!replayRunning) {
                resolve(false);
                return;
            }

            const raw = Math.min(1, (now - started) / duration);
            update(raw);

            if (raw < 1) {
                replayFrame = window.requestAnimationFrame(tick);
            } else {
                replayFrame = null;
                resolve(true);
            }
        };

        replayFrame = window.requestAnimationFrame(tick);
    });

    const waitDuringReplay = (duration) => animatePhase(duration, () => {});

    const runReplay = async () => {
        const rounds = model.rounds || [];
        if (!rounds.length) return;

        replayRoundIndex = 0;
        replayProgress = 0;
        replayWinnerDriverId = null;
        renderChart();

        const openingWinner = winnerForRound(0);
        if (openingWinner) {
            replayWinnerDriverId = openingWinner.driver_id;
            renderChart();
            await waitDuringReplay(REPLAY_WINNER_MS);
            replayWinnerDriverId = null;
            renderChart();
        }

        await waitDuringReplay(REPLAY_HOLD_MS);

        for (let nextRoundIndex = 1; nextRoundIndex < rounds.length; nextRoundIndex += 1) {
            if (!replayRunning) return;

            replayRoundIndex = nextRoundIndex - 1;
            replayProgress = 0;
            replayWinnerDriverId = null;

            const completedDraw = await animatePhase(
                REPLAY_DRAW_MS,
                (rawProgress) => {
                    replayProgress = easeInOutCubic(rawProgress);
                    renderChart();
                }
            );

            if (!completedDraw || !replayRunning) return;

            replayRoundIndex = nextRoundIndex;
            replayProgress = 0;

            const winner = winnerForRound(nextRoundIndex);
            replayWinnerDriverId = winner?.driver_id || null;
            renderChart();

            if (winner) {
                await waitDuringReplay(REPLAY_WINNER_MS);
            }

            replayWinnerDriverId = null;
            renderChart();

            if (nextRoundIndex < rounds.length - 1) {
                await waitDuringReplay(REPLAY_HOLD_MS);
            }
        }

        replayRunning = false;
        replayWinnerDriverId = null;

        if (replayButton) {
            replayButton.textContent = "Replay again";
            replayButton.classList.remove("is-playing");
        }

        renderLegend();
        renderChart();
    };

    const startReplay = () => {
        if (!model.is_complete || !model.rounds?.length) return;

        if (replayRunning) {
            stopReplay();
            renderChart();
            return;
        }

        pinnedDriverId = null;
        pinnedConstructorId = null;
        hoveredDriverId = null;
        hideTooltip();

        replayRunning = true;
        replayRoundIndex = 0;
        replayProgress = 0;

        if (replayButton) {
            replayButton.textContent = "Stop replay";
            replayButton.classList.add("is-playing");
        }

        renderLegend();
        runReplay();
    };

    const renderChart = () => {
        const containerWidth = svg.parentElement.clientWidth || 900;
        const width = Math.max(760, containerWidth);
        const height = Math.max(
            520,
            Math.min(700, model.max_position * 25 + 150)
        );
        const margin = { top: 42, right: 88, bottom: 92, left: 54 };
        const plotWidth = width - margin.left - margin.right;
        const plotHeight = height - margin.top - margin.bottom;
        const rounds = model.rounds || [];
        const maxPosition = Math.max(1, model.max_position || 1);

        const replayCurrentIndex = replayRoundIndex === null
            ? rounds.length - 1
            : replayRoundIndex;

        const replayNextIndex = (
            replayRunning &&
            replayProgress > 0 &&
            replayCurrentIndex < rounds.length - 1
        )
            ? replayCurrentIndex + 1
            : replayCurrentIndex;

        const visibleEnd = replayNextIndex;

        svg.replaceChildren();
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
        svg.setAttribute("height", String(height));
        svg.classList.toggle("is-replaying", replayRunning);

        const x = (index) => (
            margin.left +
            (
                rounds.length <= 1
                    ? plotWidth / 2
                    : index * plotWidth / (rounds.length - 1)
            )
        );

        const y = (position) => (
            margin.top +
            (
                maxPosition <= 1
                    ? 0
                    : (position - 1) * plotHeight / (maxPosition - 1)
            )
        );

        const grid = createSvg("g", { class: "progression-grid" });
        const tickStep = maxPosition > 15 ? 2 : 1;

        for (let position = 1; position <= maxPosition; position += tickStep) {
            const rowY = y(position);

            grid.append(createSvg("line", {
                x1: margin.left,
                y1: rowY,
                x2: width - margin.right,
                y2: rowY
            }));

            const label = createSvg("text", {
                x: margin.left - 14,
                y: rowY + 4,
                "text-anchor": "end"
            });
            label.textContent = position;
            grid.append(label);
        }

        svg.append(grid);

        const axis = createSvg("g", { class: "progression-axis" });
        const labelFrequency = width < 900
            ? Math.ceil(rounds.length / 10)
            : Math.ceil(rounds.length / 16);

        rounds.forEach((round, index) => {
            const columnX = x(index);
            const axisState = replayRoundIndex === null
                ? ""
                : (
                    index < replayNextIndex
                        ? " is-complete"
                        : (
                            index === replayNextIndex
                                ? " is-current"
                                : " is-upcoming"
                        )
                );

            const axisLine = createSvg("line", {
                x1: columnX,
                y1: margin.top,
                x2: columnX,
                y2: height - margin.bottom,
                class: `progression-round-axis${axisState}`
            });
            axis.append(axisLine);

            if (
                index % Math.max(1, labelFrequency) === 0 ||
                index === rounds.length - 1
            ) {
                const label = createSvg("text", {
                    x: columnX,
                    y: height - margin.bottom + 20,
                    transform: (
                        `rotate(-38 ${columnX} ` +
                        `${height - margin.bottom + 20})`
                    ),
                    "text-anchor": "end",
                    class: `progression-round-label${axisState}`
                });
                label.textContent = round.short_name;
                axis.append(label);
            }

            const hover = createSvg("rect", {
                x: (
                    columnX -
                    Math.max(
                        10,
                        plotWidth / Math.max(2, rounds.length) / 2
                    )
                ),
                y: margin.top,
                width: Math.max(
                    20,
                    plotWidth / Math.max(1, rounds.length)
                ),
                height: plotHeight,
                class: "progression-round-hit"
            });

            hover.addEventListener(
                "pointerenter",
                (event) => roundTooltip(event, round)
            );
            hover.addEventListener(
                "pointermove",
                (event) => roundTooltip(event, round)
            );
            hover.addEventListener("pointerleave", hideTooltip);
            axis.append(hover);
        });

        svg.append(axis);

        const activeDrivers = model.drivers.filter(
            (driver) => selected.has(driver.driver_id)
        );

        const previousLeader = { id: null };
        rounds.forEach((round, index) => {
            if (index > replayCurrentIndex) return;

            const leader = activeDrivers.find(
                (driver) => driver.positions[String(round.round)] === 1
            );

            if (leader && leader.driver_id !== previousLeader.id) {
                const trophy = createSvg("text", {
                    x: x(index),
                    y: margin.top - 16,
                    class: "progression-leader-marker",
                    "text-anchor": "middle"
                });
                trophy.textContent = "◆";

                const title = createSvg("title");
                title.textContent = (
                    `${leader.driver_name} takes the championship lead ` +
                    `after ${round.race_name}`
                );
                trophy.append(title);
                svg.append(trophy);
                previousLeader.id = leader.driver_id;
            }
        });

        activeDrivers.slice().reverse().forEach((driver) => {
            const focused = driverIsFocused(driver);
            const faded = hasFocus() && !focused;
            const points = [];

            rounds.forEach((round, index) => {
                if (index > visibleEnd) return;

                const position = driver.positions[String(round.round)];
                if (!position || position >= 999) return;

                points.push({
                    x: x(index),
                    y: y(position),
                    position,
                    round,
                    points: driver.points[String(round.round)] ?? 0,
                    finish: driver.finishes?.[String(round.round)],
                    index,
                    transient: false
                });
            });

            if (
                replayRunning &&
                replayProgress > 0 &&
                replayCurrentIndex < rounds.length - 1
            ) {
                const currentRound = rounds[replayCurrentIndex];
                const nextRound = rounds[replayCurrentIndex + 1];
                const currentPosition = driver.positions[
                    String(currentRound.round)
                ];
                const nextPosition = driver.positions[String(nextRound.round)];

                if (
                    currentPosition &&
                    currentPosition < 999 &&
                    nextPosition &&
                    nextPosition < 999
                ) {
                    const lastPoint = points.find(
                        (point) => point.index === replayCurrentIndex + 1
                    );

                    if (lastPoint) {
                        lastPoint.x = (
                            x(replayCurrentIndex) +
                            (
                                x(replayCurrentIndex + 1) -
                                x(replayCurrentIndex)
                            ) * replayProgress
                        );
                        lastPoint.y = (
                            y(currentPosition) +
                            (
                                y(nextPosition) -
                                y(currentPosition)
                            ) * replayProgress
                        );
                        lastPoint.position = nextPosition;
                        lastPoint.transient = true;
                    }
                }
            }

            let segment = [];

            const flush = () => {
                if (segment.length >= 2) {
                    const d = segment.map((point, index) => (
                        `${index ? "L" : "M"} ` +
                        `${point.x.toFixed(2)} ${point.y.toFixed(2)}`
                    )).join(" ");

                    const path = createSvg("path", {
                        d,
                        class: (
                            `progression-line` +
                            (
                                focused && hasFocus()
                                    ? " is-focused"
                                    : ""
                            ) +
                            (faded ? " is-faded" : "")
                        ),
                        stroke: driver.team_colour,
                        "data-driver-id": driver.driver_id
                    });

                    path.addEventListener("pointerenter", () => {
                        if (replayRunning) return;
                        hoveredDriverId = driver.driver_id;
                        applyHoverFocus();
                    });
                    path.addEventListener("pointerleave", () => {
                        if (replayRunning) return;
                        hoveredDriverId = null;
                        applyHoverFocus();
                    });
                    path.addEventListener(
                        "click",
                        (event) => setPinned(driver, event.shiftKey)
                    );

                    svg.append(path);
                }
                segment = [];
            };

            points.forEach((point) => {
                if (point) segment.push(point);
                else flush();
            });
            flush();

            points.forEach((point) => {
                const isMovingTip = (
                    replayRunning &&
                    point.transient
                );
                const isWinner = point.finish === 1;
                const winnerCelebration = (
                    replayWinnerDriverId === driver.driver_id &&
                    point.index === replayCurrentIndex
                );

                const circle = createSvg("circle", {
                    cx: point.x,
                    cy: point.y,
                    r: isWinner ? 6 : 5,
                    fill: driver.team_colour,
                    class: (
                        `progression-point` +
                        (isWinner ? " is-win" : "") +
                        (faded ? " is-faded" : "") +
                        (isMovingTip ? " is-moving-tip" : "") +
                        (
                            winnerCelebration
                                ? " is-replay-winner"
                                : ""
                        )
                    ),
                    "data-driver-id": driver.driver_id,
                    tabindex: replayRunning ? -1 : 0,
                    role: "button",
                    "aria-label": (
                        `${driver.driver_name}, ${point.round.race_name}, ` +
                        `${ordinal(point.position)}, ${point.points} points`
                    )
                });

                circle.addEventListener("pointerenter", (event) => {
                    if (replayRunning) return;
                    hoveredDriverId = driver.driver_id;
                    applyHoverFocus();
                    driverTooltip(
                        event,
                        driver,
                        point.round,
                        point.position,
                        point.points
                    );
                });
                circle.addEventListener(
                    "pointermove",
                    (event) => driverTooltip(
                        event,
                        driver,
                        point.round,
                        point.position,
                        point.points
                    )
                );
                circle.addEventListener("pointerleave", () => {
                    if (replayRunning) return;
                    hoveredDriverId = null;
                    hideTooltip();
                    applyHoverFocus();
                });
                circle.addEventListener(
                    "click",
                    (event) => setPinned(driver, event.shiftKey)
                );

                svg.append(circle);

                if (winnerCelebration) {
                    const ring = createSvg("circle", {
                        cx: point.x,
                        cy: point.y,
                        r: 8,
                        class: "progression-winner-ring",
                        "data-driver-id": driver.driver_id
                    });
                    svg.append(ring);
                }

                if (
                    pinnedDriverId === driver.driver_id &&
                    !point.transient
                ) {
                    const finish = (
                        point.finish &&
                        point.finish < 999
                    )
                        ? `P${point.finish}`
                        : "—";

                    const text = createSvg("text", {
                        x: point.x,
                        y: point.y - 11,
                        class: "progression-finish-label",
                        "text-anchor": "middle"
                    });
                    text.textContent = finish;
                    svg.append(text);
                }
            });
        });

        const labelRoundIndex = replayNextIndex;
        const labelRound = rounds[Math.max(0, labelRoundIndex)];

        if (labelRound) {
            const labels = activeDrivers
                .filter((driver) => (
                    driver.positions[String(labelRound.round)] < 999
                ))
                .sort((a, b) => (
                    a.positions[String(labelRound.round)] -
                    b.positions[String(labelRound.round)]
                ));

            labels.forEach((driver) => {
                let position = driver.positions[String(labelRound.round)];

                if (
                    replayRunning &&
                    replayProgress > 0 &&
                    replayCurrentIndex < rounds.length - 1
                ) {
                    const currentRound = rounds[replayCurrentIndex];
                    const nextRound = rounds[replayCurrentIndex + 1];
                    const currentPosition = driver.positions[
                        String(currentRound.round)
                    ];
                    const nextPosition = driver.positions[
                        String(nextRound.round)
                    ];

                    if (
                        currentPosition &&
                        currentPosition < 999 &&
                        nextPosition &&
                        nextPosition < 999
                    ) {
                        position = (
                            currentPosition +
                            (
                                nextPosition - currentPosition
                            ) * replayProgress
                        );
                    }
                }

                const label = createSvg("text", {
                    x: width - margin.right + 12,
                    y: y(position) + 4,
                    class: (
                        `progression-end-label` +
                        (
                            hasFocus() && !driverIsFocused(driver)
                                ? " is-faded"
                                : ""
                        ) +
                        (replayRunning ? " is-replay-label" : "")
                    ),
                    fill: driver.team_colour,
                    "data-driver-id": driver.driver_id
                });

                label.textContent = driver.driver_code;
                label.addEventListener(
                    "click",
                    (event) => setPinned(driver, event.shiftKey)
                );
                label.addEventListener("pointerenter", () => {
                    if (replayRunning) return;
                    hoveredDriverId = driver.driver_id;
                    applyHoverFocus();
                });
                label.addEventListener("pointerleave", () => {
                    if (replayRunning) return;
                    hoveredDriverId = null;
                    applyHoverFocus();
                });
                svg.append(label);
            });
        }

        if (!activeDrivers.length) {
            const empty = createSvg("text", {
                x: width / 2,
                y: height / 2,
                class: "progression-empty",
                "text-anchor": "middle"
            });
            empty.textContent = "Select at least one driver below";
            svg.append(empty);
        }
    };

    collapseButton?.addEventListener("click", () => {
        const willCollapse = !root.hidden;
        root.hidden = willCollapse;
        collapseButton.setAttribute(
            "aria-expanded",
            String(!willCollapse)
        );
        collapseButton.textContent = willCollapse
            ? "Expand"
            : "Minimise";

        if (!willCollapse) {
            window.requestAnimationFrame(renderChart);
        } else {
            hideTooltip();
            stopReplay();
        }
    });

    resetButton?.addEventListener("click", () => {
        stopReplay();
        pinnedDriverId = null;
        pinnedConstructorId = null;
        selected.clear();
        (model.default_driver_ids || []).forEach(
            (driverId) => selected.add(driverId)
        );
        renderLegend();
        renderChart();
    });

    replayButton?.addEventListener("click", startReplay);

    let resizeTimer;
    window.addEventListener("resize", () => {
        window.clearTimeout(resizeTimer);
        resizeTimer = window.setTimeout(renderChart, 120);
    });

    renderLegend();
    renderChart();
})();
