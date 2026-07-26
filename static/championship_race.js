(() => {
    "use strict";

    const root = document.querySelector("[data-championship-race]");
    const dataElement = document.getElementById("position-progression-data");
    if (!root || !dataElement) return;

    let model;
    try {
        model = JSON.parse(dataElement.textContent);
    } catch (error) {
        console.error("Could not parse championship race data", error);
        return;
    }

    const svg = root.querySelector("[data-points-chart]");
    const podium = root.querySelector("[data-live-podium]");
    const roundName = root.querySelector("[data-current-round-name]");
    const roundCounter = root.querySelector("[data-current-round-counter]");
    const playButton = root.querySelector("[data-race-play]");
    const resetButton = root.querySelector("[data-race-reset]");
    const progress = root.querySelector("[data-race-progress]");
    const tooltip = root.querySelector("[data-points-tooltip]");
    const SVG_NS = "http://www.w3.org/2000/svg";

    const completedRounds = model.rounds || [];
    const drivers = model.drivers || [];
    if (!completedRounds.length || !drivers.length) return;

    // Render the complete championship field. The previous implementation
    // deliberately capped this at the top eight final finishers, which meant
    // lower-ranked, substitute and part-season drivers were missing.
    const shownDrivers = drivers
        .slice()
        .sort((a, b) => (a.final_position - b.final_position) ||
            a.driver_name.localeCompare(b.driver_name));

    let displayRound = completedRounds.length - 1;
    let settledRound = completedRounds.length - 1;
    let segmentProgress = 1;
    let playing = false;
    let animationFrame = null;
    let pinnedDriverId = null;
    let pinnedConstructorId = null;
    let hoveredDriverId = null;
    let resultPulseRound = null;
    let resultPulseTimer = null;
    let lastLeaderId = null;

    const SEGMENT_DURATION_MS = 1650;
    const SETTLE_DURATION_MS = 900;

    const createSvg = (name, attributes = {}) => {
        const element = document.createElementNS(SVG_NS, name);
        Object.entries(attributes).forEach(([key, value]) => {
            element.setAttribute(key, String(value));
        });
        return element;
    };

    const pointsAt = (driver, roundIndex) => {
        if (roundIndex < 0) return 0;
        const round = completedRounds[Math.min(roundIndex, completedRounds.length - 1)];
        return Number(driver.points?.[String(round.round)] ?? 0);
    };

    const scaleForPoints = (points) => Math.max(
        50,
        Math.ceil(Math.max(0, Number(points) || 0) / 50) * 50
    );

    // Calculate the required ceiling only after pointsAt exists. The ceiling
    // starts at 50 and grows monotonically as the leading score increases.
    const roundScaleMaxima = completedRounds.reduce((scales, _round, index) => {
        const leaderPoints = Math.max(
            0,
            ...shownDrivers.map((driver) => pointsAt(driver, index))
        );
        const previousScale = index > 0 ? scales[index - 1] : 50;
        scales.push(Math.max(previousScale, scaleForPoints(leaderPoints)));
        return scales;
    }, []);

    const liveScaleMax = () => {
        if (displayRound <= 0) return roundScaleMaxima[0] || 50;
        const fromScale = roundScaleMaxima[displayRound - 1] || 50;
        const toScale = roundScaleMaxima[displayRound] || fromScale;
        return fromScale + (toScale - fromScale) * segmentProgress;
    };

    const positionAt = (driver, roundIndex) => {
        if (roundIndex < 0) return 999;
        const round = completedRounds[Math.min(roundIndex, completedRounds.length - 1)];
        return Number(driver.positions?.[String(round.round)] ?? 999);
    };

    const outcomeAt = (driver, roundIndex) => {
        const round = completedRounds[roundIndex];
        return round ? driver.finish_outcomes?.[String(round.round)] || null : null;
    };

    const finishAt = (driver, roundIndex) => {
        const round = completedRounds[roundIndex];
        return round ? Number(driver.finishes?.[String(round.round)] ?? 999) : 999;
    };

    const easeInOutCubic = (value) => (
        value < 0.5
            ? 4 * value * value * value
            : 1 - Math.pow(-2 * value + 2, 3) / 2
    );

    const teamKeyFor = (driver) => (
        driver.constructor_id
        || driver.constructor_name
        || `driver:${driver.driver_id}`
    );

    const driverIsFocused = (driver) => {
        if (pinnedConstructorId) return teamKeyFor(driver) === pinnedConstructorId;
        if (pinnedDriverId) return driver.driver_id === pinnedDriverId;
        if (hoveredDriverId) return driver.driver_id === hoveredDriverId;
        return true;
    };

    const focusActive = () => Boolean(
        pinnedDriverId || pinnedConstructorId || hoveredDriverId
    );

    const driverIsPinned = (driver) => (
        pinnedConstructorId
            ? teamKeyFor(driver) === pinnedConstructorId
            : pinnedDriverId === driver.driver_id
    );

    const resultLabelFor = (driver, roundIndex) => {
        const outcome = outcomeAt(driver, roundIndex);
        const finish = finishAt(driver, roundIndex);
        if (outcome?.kind === "dnf") return { text: "DNF", kind: "dnf" };
        if (outcome && outcome.kind !== "finish") {
            return { text: outcome.label || outcome.status, kind: outcome.kind };
        }
        if (!Number.isFinite(finish) || finish >= 999) return null;
        return {
            text: `P${finish}`,
            kind: finish <= 3 ? `podium-${finish}` : "finish"
        };
    };

    const applyFocus = () => {
        const active = focusActive();
        root.querySelectorAll("[data-driver-id]").forEach((element) => {
            const driver = shownDrivers.find(
                (candidate) => candidate.driver_id === element.dataset.driverId
            );
            if (!driver) return;
            const focused = driverIsFocused(driver);
            element.classList.toggle("is-focused", active && focused);
            element.classList.toggle("is-faded", active && !focused);
        });
    };

    const setPinned = (driver, teammates = false) => {
        if (playing) return;

        if (teammates) {
            const teamKey = teamKeyFor(driver);
            pinnedConstructorId = pinnedConstructorId === teamKey
                ? null
                : teamKey;
            pinnedDriverId = null;
        } else {
            pinnedDriverId = pinnedDriverId === driver.driver_id
                ? null
                : driver.driver_id;
            pinnedConstructorId = null;
        }

        // The element that received the click is replaced during rendering.
        // Clear its stale hover state first so teammate focus is not immediately
        // overridden by a pointerleave event from the old SVG element.
        hoveredDriverId = null;
        hideTooltip();

        // Result annotations are created during chart rendering, so redraw the
        // chart whenever the pinned selection changes. Shift-click teammate
        // focus remains visual-only; race-by-race labels are reserved for a
        // single selected driver to keep the graph readable.
        renderChart();
        applyFocus();
    };

    const showTooltip = (event, driver, roundIndex, points) => {
        const round = completedRounds[roundIndex];
        const outcome = outcomeAt(driver, roundIndex);
        const finish = finishAt(driver, roundIndex);
        const result = outcome
            ? `${outcome.label} · ${outcome.status}`
            : Number.isFinite(finish) && finish < 999
                ? `P${finish}`
                : "Result unavailable";

        tooltip.hidden = false;
        tooltip.innerHTML = `
            <strong>${driver.driver_name}</strong>
            <span>${round.race_name}</span>
            <span>${points.toFixed(points % 1 ? 1 : 0)} points · ${result}</span>
            <span class="points-tooltip-hint">Click to pin · Shift-click for teammates</span>
        `;

        const bounds = root.getBoundingClientRect();
        const left = Math.min(event.clientX - bounds.left + 12, bounds.width - 230);
        const top = Math.min(event.clientY - bounds.top + 12, bounds.height - 120);
        tooltip.style.left = `${Math.max(12, left)}px`;
        tooltip.style.top = `${Math.max(12, top)}px`;
    };

    const hideTooltip = () => {
        tooltip.hidden = true;
    };

    const attachDriverInteractions = (element, driver, roundIndex = null, points = null) => {
        element.dataset.driverId = driver.driver_id;
        element.addEventListener("pointerenter", (event) => {
            if (playing) return;
            hoveredDriverId = driver.driver_id;
            applyFocus();
            if (roundIndex !== null) showTooltip(event, driver, roundIndex, points);
        });
        element.addEventListener("pointermove", (event) => {
            if (roundIndex !== null) showTooltip(event, driver, roundIndex, points);
        });
        element.addEventListener("pointerleave", () => {
            if (playing) return;
            hoveredDriverId = null;
            hideTooltip();
            applyFocus();
        });
        element.addEventListener("click", (event) => {
            // Prevent Shift-click from triggering browser text selection or
            // native focus flashes on SVG elements.
            event.preventDefault();
            event.stopPropagation();
            setPinned(driver, event.shiftKey);
        });
    };

    const renderChart = () => {
        svg.replaceChildren();
        const width = 1120;
        const height = 470;
        const margin = { top: 34, right: 118, bottom: 62, left: 62 };
        const plotWidth = width - margin.left - margin.right;
        const plotHeight = height - margin.top - margin.bottom;
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

        const xFor = (index) => margin.left + (
            completedRounds.length === 1
                ? 0
                : (index / (completedRounds.length - 1)) * plotWidth
        );
        const yMax = Math.max(50, liveScaleMax());
        const yFor = (points) => margin.top + plotHeight - (points / yMax) * plotHeight;

        const defs = createSvg("defs");
        const gradient = createSvg("linearGradient", {
            id: "points-grid-fade",
            x1: "0",
            y1: "0",
            x2: "1",
            y2: "0"
        });
        gradient.append(
            createSvg("stop", { offset: "0%", "stop-color": "#ffffff", "stop-opacity": ".03" }),
            createSvg("stop", { offset: "100%", "stop-color": "#ffffff", "stop-opacity": ".09" })
        );
        defs.append(gradient);
        svg.append(defs);

        const grid = createSvg("g", { class: "points-grid" });
        const tickCount = 5;
        for (let index = 0; index <= tickCount; index += 1) {
            const value = Math.round((yMax / tickCount) * index);
            const y = yFor(value);
            grid.append(createSvg("line", {
                x1: margin.left,
                y1: y,
                x2: width - margin.right,
                y2: y
            }));
            const label = createSvg("text", {
                x: margin.left - 14,
                y: y + 4,
                "text-anchor": "end"
            });
            label.textContent = value;
            grid.append(label);
        }
        svg.append(grid);

        const previousRound = Math.max(0, displayRound - 1);
        const completedX = displayRound === 0
            ? xFor(0)
            : xFor(previousRound) + (xFor(displayRound) - xFor(previousRound)) * segmentProgress;

        svg.append(createSvg("rect", {
            x: margin.left,
            y: margin.top,
            width: Math.max(0, completedX - margin.left),
            height: plotHeight,
            class: "points-completed-wash"
        }));

        completedRounds.forEach((round, index) => {
            const x = xFor(index);
            const axis = createSvg("line", {
                x1: x,
                y1: margin.top,
                x2: x,
                y2: margin.top + plotHeight,
                class: "points-round-axis"
            });
            axis.classList.toggle("is-future", index > displayRound);
            svg.append(axis);

            if (
                index === 0 ||
                index === completedRounds.length - 1 ||
                index % Math.ceil(completedRounds.length / 8) === 0
            ) {
                const label = createSvg("text", {
                    x,
                    y: height - 24,
                    "text-anchor": "middle",
                    class: "points-round-label"
                });
                label.textContent = round.short_name;
                label.classList.toggle("is-future", index > displayRound);
                svg.append(label);
            }
        });

        shownDrivers.slice().reverse().forEach((driver) => {
            const pathPoints = [];
            const completedThrough = displayRound === 0 ? 0 : displayRound - 1;

            for (let index = 0; index <= completedThrough; index += 1) {
                pathPoints.push({
                    x: xFor(index),
                    y: yFor(pointsAt(driver, index)),
                    points: pointsAt(driver, index),
                    roundIndex: index,
                    transient: false
                });
            }

            if (displayRound > 0) {
                const startPoints = pointsAt(driver, displayRound - 1);
                const endPoints = pointsAt(driver, displayRound);
                const livePoints = startPoints + (endPoints - startPoints) * segmentProgress;
                pathPoints.push({
                    x: xFor(displayRound - 1) + (xFor(displayRound) - xFor(displayRound - 1)) * segmentProgress,
                    y: yFor(livePoints),
                    points: livePoints,
                    roundIndex: displayRound,
                    transient: segmentProgress < 1
                });
            } else if (!pathPoints.length) {
                pathPoints.push({
                    x: xFor(0),
                    y: yFor(pointsAt(driver, 0)),
                    points: pointsAt(driver, 0),
                    roundIndex: 0,
                    transient: false
                });
            }

            if (!pathPoints.length) return;

            const d = pathPoints.map((point, index) => (
                `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`
            )).join(" ");

            const line = createSvg("path", {
                d,
                class: "points-driver-line",
                stroke: driver.team_colour,
                tabindex: playing ? -1 : 0,
                role: "button",
                "aria-label": `${driver.driver_name}. Click to focus; shift-click to focus teammates.`
            });
            attachDriverInteractions(line, driver);
            svg.append(line);

            pathPoints.forEach((point) => {
                if (point.transient) return;

                const outcome = outcomeAt(driver, point.roundIndex);
                const finish = finishAt(driver, point.roundIndex);
                const isWinner = outcome?.kind === "finish" && finish === 1;
                const isDnf = outcome?.kind === "dnf";
                const isDsq = outcome?.kind === "dsq";
                const isCurrentResult = point.roundIndex === resultPulseRound;
                const pointClass = [
                    "points-driver-point",
                    isWinner ? "is-win" : "",
                    isDnf ? "is-dnf" : "",
                    isDsq ? "is-dsq" : "",
                    isCurrentResult && isWinner ? "is-result-pulse-win" : "",
                    isCurrentResult && isDnf ? "is-result-pulse-dnf" : "",
                    isCurrentResult && isDsq ? "is-result-pulse-dsq" : ""
                ].filter(Boolean).join(" ");

                const circle = createSvg("circle", {
                    cx: point.x,
                    cy: point.y,
                    r: isWinner ? 6.3 : isDnf ? 5.7 : isDsq ? 6.1 : 3.8,
                    fill: isDnf ? "var(--panel)" : isDsq ? "#050608" : driver.team_colour,
                    class: pointClass,
                    style: isDsq ? `--driver-colour: ${driver.team_colour}` : "",
                    tabindex: playing ? -1 : 0,
                    role: "button",
                    "aria-label": `${driver.driver_name}, ${completedRounds[point.roundIndex].race_name}, ${outcome?.label || "result"}, ${point.points} points`
                });
                attachDriverInteractions(circle, driver, point.roundIndex, point.points);
                svg.append(circle);

                if (isWinner) {
                    const winnerRing = createSvg("circle", {
                        cx: point.x,
                        cy: point.y,
                        r: 9.5,
                        class: `points-result-ring points-result-ring--win${
                            isCurrentResult ? " is-result-pulse-win" : ""
                        }`
                    });
                    winnerRing.dataset.driverId = driver.driver_id;
                    svg.append(winnerRing);
                }

                if (isDnf) {
                    const cross = createSvg("g", {
                        class: `points-dnf-mark${
                            isCurrentResult ? " is-result-pulse-dnf" : ""
                        }`,
                        "data-driver-id": driver.driver_id
                    });
                    cross.append(
                        createSvg("line", {
                            x1: point.x - 3,
                            y1: point.y - 3,
                            x2: point.x + 3,
                            y2: point.y + 3
                        }),
                        createSvg("line", {
                            x1: point.x + 3,
                            y1: point.y - 3,
                            x2: point.x - 3,
                            y2: point.y + 3
                        })
                    );
                    svg.append(cross);
                }

                if (isDsq) {
                    const dsqRing = createSvg("circle", {
                        cx: point.x,
                        cy: point.y,
                        r: 9.2,
                        stroke: driver.team_colour,
                        class: `points-result-ring points-result-ring--dsq${
                            isCurrentResult ? " is-result-pulse-dsq" : ""
                        }`,
                        "data-driver-id": driver.driver_id
                    });
                    svg.append(dsqRing);

                    const dsqMark = createSvg("g", {
                        class: `points-dsq-mark${
                            isCurrentResult ? " is-result-pulse-dsq" : ""
                        }`,
                        "data-driver-id": driver.driver_id
                    });
                    dsqMark.append(
                        createSvg("line", {
                            x1: point.x - 2.8,
                            y1: point.y - 2.8,
                            x2: point.x + 2.8,
                            y2: point.y + 2.8
                        }),
                        createSvg("line", {
                            x1: point.x + 2.8,
                            y1: point.y - 2.8,
                            x2: point.x - 2.8,
                            y2: point.y + 2.8
                        })
                    );
                    svg.append(dsqMark);
                }

                if (pinnedDriverId === driver.driver_id) {
                    const resultLabel = resultLabelFor(driver, point.roundIndex);
                    if (resultLabel) {
                        const label = createSvg("text", {
                            x: point.x,
                            y: point.y - (isWinner || isDnf || isDsq ? 15 : 11),
                            "text-anchor": "middle",
                            class: `points-result-label is-${resultLabel.kind}`,
                            "data-driver-id": driver.driver_id
                        });
                        label.textContent = resultLabel.text;
                        svg.append(label);
                    }
                }
            });

            const end = pathPoints[pathPoints.length - 1];
            const endLabel = createSvg("text", {
                x: end.x + 12,
                y: end.y + 4,
                fill: driver.team_colour,
                class: "points-driver-label",
                "data-driver-id": driver.driver_id
            });
            endLabel.textContent = `${driver.driver_code} ${Math.round(end.points)}`;
            attachDriverInteractions(endLabel, driver);
            svg.append(endLabel);
        });

        svg.append(createSvg("line", {
            x1: completedX,
            x2: completedX,
            y1: margin.top - 8,
            y2: margin.top + plotHeight + 8,
            class: "points-playhead"
        }));

        applyFocus();
    };

    const standingsAt = (roundIndex) => shownDrivers
        .map((driver) => ({
            ...driver,
            pointsNow: pointsAt(driver, roundIndex),
            positionNow: positionAt(driver, roundIndex)
        }))
        .sort((a, b) => {
            if (a.positionNow !== b.positionNow) return a.positionNow - b.positionNow;
            return b.pointsNow - a.pointsNow;
        });

    const formatPoints = (value) => {
        const rounded = Math.round(value * 10) / 10;
        return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
    };

    const quantizeAnimatedPoints = (previousPoints, currentPoints, progress) => {
        if (progress <= 0) return previousPoints;
        if (progress >= 1) return currentPoints;

        const interpolated = previousPoints
            + (currentPoints - previousPoints) * progress;
        const direction = Math.sign(currentPoints - previousPoints) || 1;

        // Animate in one-point steps from the real previous total. This keeps
        // integer scores integer, while an existing half-point score advances
        // naturally as 1.5, 2.5, 3.5, etc. A newly earned half point only
        // appears when the animation reaches the real final total.
        const stepped = previousPoints
            + direction * Math.floor(Math.abs(interpolated - previousPoints));

        if (direction > 0) {
            return Math.min(stepped, currentPoints);
        }
        return Math.max(stepped, currentPoints);
    };

    const animatedPointsAt = (driver) => {
        if (displayRound <= 0) return pointsAt(driver, 0);
        const previousPoints = pointsAt(driver, displayRound - 1);
        const currentPoints = pointsAt(driver, displayRound);
        return quantizeAnimatedPoints(
            previousPoints,
            currentPoints,
            segmentProgress
        );
    };

    const updatePodiumScores = () => {
        [...podium.children].forEach((card) => {
            const driver = shownDrivers.find(
                (candidate) => candidate.driver_id === card.dataset.driverId
            );
            const score = card.querySelector('.live-podium-score strong');
            if (!driver || !score) return;
            score.textContent = formatPoints(animatedPointsAt(driver));
        });
    };

    const renderPodium = () => {
        const standings = standingsAt(settledRound).slice(0, 3);
        const currentLeaderId = standings[0]?.driver_id || null;
        const leaderChanged = Boolean(lastLeaderId && currentLeaderId && lastLeaderId !== currentLeaderId);
        const oldRects = new Map(
            [...podium.children].map((card) => [
                card.dataset.driverId,
                card.getBoundingClientRect()
            ])
        );
        const existing = new Map(
            [...podium.children].map((card) => [card.dataset.driverId, card])
        );

        standings.forEach((driver, index) => {
            let card = existing.get(driver.driver_id);
            const isNew = !card;
            if (!card) {
                card = document.createElement("article");
                card.dataset.driverId = driver.driver_id;
                attachDriverInteractions(card, driver);
            }

            card.className = `live-podium-card live-podium-card--${index + 1}`;
            card.style.setProperty("--driver-colour", driver.team_colour);
            card.innerHTML = `
                <span class="live-podium-position">P${index + 1}</span>
                <div class="live-podium-identity">
                    <strong>${driver.driver_name}</strong>
                    <small>${driver.constructor_name}</small>
                </div>
                <div class="live-podium-score">
                    <strong>${formatPoints(driver.pointsNow)}</strong>
                    <small>points</small>
                </div>
                <span class="live-podium-movement">${driver.driver_code}</span>
            `;
            podium.append(card);

            if (isNew) card.classList.add("is-entering");
            if (index === 0 && leaderChanged) card.classList.add("is-new-leader");
        });

        lastLeaderId = currentLeaderId;

        [...podium.children].forEach((card) => {
            if (!standings.some((driver) => driver.driver_id === card.dataset.driverId)) {
                card.classList.add("is-leaving");
                card.addEventListener("animationend", () => card.remove(), { once: true });
            }
        });

        requestAnimationFrame(() => {
            [...podium.children].forEach((card) => {
                const oldRect = oldRects.get(card.dataset.driverId);
                if (!oldRect || card.classList.contains("is-leaving")) return;
                const newRect = card.getBoundingClientRect();
                const deltaX = oldRect.left - newRect.left;
                const deltaY = oldRect.top - newRect.top;
                if (Math.abs(deltaX) < 1 && Math.abs(deltaY) < 1) return;
                card.animate(
                    [
                        { transform: `translate(${deltaX}px, ${deltaY}px) scale(.985)` },
                        { transform: "translate(0, 0) scale(1)" }
                    ],
                    { duration: 520, easing: "cubic-bezier(.2,.8,.2,1)" }
                );
            });
        });

        applyFocus();
    };

    const renderMeta = () => {
        const round = completedRounds[displayRound];
        roundName.textContent = round.race_name;
        roundCounter.textContent = `Round ${displayRound + 1} of ${completedRounds.length}`;
        const previous = Math.max(0, displayRound - 1);
        const continuousRound = displayRound === 0
            ? 0
            : previous + segmentProgress;
        const progressValue = completedRounds.length === 1
            ? 100
            : (continuousRound / (completedRounds.length - 1)) * 100;
        progress.style.setProperty("--race-progress", `${progressValue}%`);
    };

    const render = ({ podiumToo = false } = {}) => {
        renderChart();
        renderMeta();
        if (podiumToo) {
            renderPodium();
        } else {
            updatePodiumScores();
        }
    };

    const stop = () => {
        playing = false;
        if (animationFrame) cancelAnimationFrame(animationFrame);
        animationFrame = null;
        playButton.classList.remove("is-playing");
        playButton.textContent = displayRound >= completedRounds.length - 1 && segmentProgress >= 1
            ? "Replay season"
            : "Continue replay";
    };

    const wait = (duration) => new Promise((resolve) => {
        window.setTimeout(resolve, duration);
    });

    const animateSegment = (toRound) => new Promise((resolve) => {
        const started = performance.now();
        displayRound = toRound;
        segmentProgress = 0;

        const tick = (now) => {
            if (!playing) {
                resolve(false);
                return;
            }
            const raw = Math.min(1, (now - started) / SEGMENT_DURATION_MS);
            segmentProgress = easeInOutCubic(raw);
            render();

            if (raw < 1) {
                animationFrame = requestAnimationFrame(tick);
            } else {
                animationFrame = null;
                settledRound = toRound;
                resultPulseRound = toRound;
                if (resultPulseTimer) window.clearTimeout(resultPulseTimer);
                render({ podiumToo: true });
                resultPulseTimer = window.setTimeout(() => {
                    resultPulseRound = null;
                }, 900);
                resolve(true);
            }
        };
        animationFrame = requestAnimationFrame(tick);
    });

    const play = async () => {
        if (playing) {
            stop();
            return;
        }

        if (displayRound >= completedRounds.length - 1 && segmentProgress >= 1) {
            displayRound = 0;
            settledRound = 0;
            segmentProgress = 1;
            pinnedDriverId = null;
            pinnedConstructorId = null;
            hoveredDriverId = null;
            render({ podiumToo: true });
            await wait(SETTLE_DURATION_MS);
        }

        playing = true;
        playButton.classList.add("is-playing");
        playButton.textContent = "Pause";

        for (let next = displayRound + 1; next < completedRounds.length; next += 1) {
            const completed = await animateSegment(next);
            if (!completed || !playing) return;
            await wait(SETTLE_DURATION_MS);
        }
        stop();
    };

    playButton.addEventListener("click", play);
    resetButton.addEventListener("click", () => {
        stop();
        displayRound = completedRounds.length - 1;
        settledRound = completedRounds.length - 1;
        segmentProgress = 1;
        render({ podiumToo: true });
    });

    render({ podiumToo: true });
})();
