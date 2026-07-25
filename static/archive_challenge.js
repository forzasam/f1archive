(() => {
    "use strict";

    const root = document.querySelector("[data-archive-challenge]");
    if (!root) return;

    const svg = root.querySelector("[data-challenge-chart]");
    const loading = root.querySelector("[data-loading]");
    const driverInput = root.querySelector("[data-driver-guess]");
    const seasonInput = root.querySelector("[data-season-guess]");
    const submitButton = root.querySelector("[data-submit-guess]");
    const hintButton = root.querySelector("[data-use-hint]");
    const hintList = root.querySelector("[data-hint-list]");
    const feedback = root.querySelector("[data-feedback]");
    const reveal = root.querySelector("[data-reveal]");
    const answerTitle = root.querySelector("[data-answer-title]");
    const answerSummary = root.querySelector("[data-answer-summary]");
    const revealKicker = root.querySelector("[data-reveal-kicker]");
    const viewSeason = root.querySelector("[data-view-season]");
    const nextButton = root.querySelector("[data-next-question]");
    const newRunButton = root.querySelector("[data-new-run]");
    const title = root.querySelector("[data-round-title]");
    const kicker = root.querySelector("[data-round-kicker]");

    const chartWrap = svg.closest(".challenge-chart-wrap");
    const dotTooltip = document.createElement("div");
    dotTooltip.className = "challenge-dot-tooltip";
    dotTooltip.hidden = true;
    dotTooltip.setAttribute("role", "tooltip");
    chartWrap?.append(dotTooltip);

    const SVG_NS = "http://www.w3.org/2000/svg";
    const state = {
        mode: "endless",
        question: null,
        hintsUsed: 0,
        streak: 0,
        score: 0,
        bestStreak: Number(localStorage.getItem("f1archive-best-streak") || 0),
        usedIds: [],
        resolved: false,
        pinnedSeries: null,
        hoveredSeries: null,
    };

    const createSvg = (name, attrs = {}) => {
        const element = document.createElementNS(SVG_NS, name);
        Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, String(value)));
        return element;
    };

    const setControlsEnabled = (enabled) => {
        driverInput.disabled = !enabled;
        seasonInput.disabled = !enabled;
        submitButton.disabled = !enabled;
        hintButton.disabled = !enabled || state.hintsUsed >= 4;
    };

    const updateStats = () => {
        root.querySelector("[data-streak]").textContent = String(state.streak);
        root.querySelector("[data-score]").textContent = String(state.score);
        root.querySelector("[data-points]").textContent = String(Math.max(1, 5 - state.hintsUsed));
        root.querySelector("[data-best-streak]").textContent = String(state.bestStreak);
    };

    const dailyStorageKey = () => `f1archive-daily-${root.dataset.dailyKey}`;

    const setLoadingVisible = (visible, message = "Opening the archive…") => {
        if (!loading) return;

        loading.textContent = message;
        loading.hidden = !visible;
        loading.setAttribute("aria-hidden", String(!visible));

        if (visible) {
            loading.style.removeProperty("display");
            loading.classList.add("is-visible");
        } else {
            /*
             * Some challenge styles explicitly set a display value on the
             * loading overlay, which can override the browser's [hidden]
             * presentation. Force it off after the chart has loaded.
             */
            loading.style.setProperty("display", "none", "important");
            loading.classList.remove("is-visible");
        }
    };

    const showDotTooltip = (event, round, series) => {
        if (!dotTooltip || !chartWrap) return;

        const isFinish = series === "finish";
        const position = isFinish ? round.finish : round.standing;
        const heading = round.race_name || round.label || "Grand Prix";

        let resultLine;
        if (isFinish && round.did_not_participate) {
            resultLine = "Did not participate";
        } else if (isFinish) {
            resultLine = `Finished P${position}`;
            if (round.dnf) {
                resultLine = `Classified P${position} · DNF`;
            }
        } else {
            resultLine = `Championship position: P${position}`;
        }

        dotTooltip.replaceChildren();

        const strong = document.createElement("strong");
        strong.textContent = heading;

        const positionText = document.createElement("span");
        positionText.textContent = resultLine;

        dotTooltip.append(strong, positionText);

        if (isFinish) {
            const status = document.createElement("span");

            if (round.did_not_participate) {
                status.className = "challenge-tooltip-status is-dnp";
                status.textContent = "DNP";
            } else {
                status.className = round.dnf
                    ? "challenge-tooltip-status is-dnf"
                    : "challenge-tooltip-status";
                status.textContent = round.dnf
                    ? `DNF · ${round.status || "Retired"}`
                    : (
                        round.status
                            ? (
                                round.status !== "Finished"
                                    ? `Classified · ${round.status}`
                                    : "Finished"
                            )
                            : "Finish status unavailable"
                    );
            }

            dotTooltip.append(status);
        }

        dotTooltip.hidden = false;

        const wrapRect = chartWrap.getBoundingClientRect();
        const tooltipRect = dotTooltip.getBoundingClientRect();

        let left = event.clientX - wrapRect.left + chartWrap.scrollLeft + 14;
        let top = event.clientY - wrapRect.top + chartWrap.scrollTop + 14;

        left = Math.min(
            left,
            chartWrap.scrollLeft + chartWrap.clientWidth - tooltipRect.width - 12,
        );
        top = Math.min(
            top,
            chartWrap.scrollTop + chartWrap.clientHeight - tooltipRect.height - 12,
        );

        dotTooltip.style.left = `${Math.max(chartWrap.scrollLeft + 12, left)}px`;
        dotTooltip.style.top = `${Math.max(chartWrap.scrollTop + 12, top)}px`;
    };

    const hideDotTooltip = () => {
        if (dotTooltip) dotTooltip.hidden = true;
    };

    const drawChart = (rounds, maxPosition) => {
        const width = 940;
        const height = 510;
        const margin = { top: 34, right: 28, bottom: 116, left: 48 };
        const plotWidth = width - margin.left - margin.right;
        const plotHeight = height - margin.top - margin.bottom;
        const maxY = Math.max(10, Math.min(30, maxPosition || 20));
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
            ((position - 1) * plotHeight / Math.max(1, maxY - 1))
        );
        const dnpY = height - margin.bottom + 24;

        const seriesLabel = {
            standing: "Championship position",
            finish: "Race finish",
        };

        const focusSeries = (series) => {
            state.hoveredSeries = series;
            const active = state.pinnedSeries || state.hoveredSeries;

            svg.querySelectorAll("[data-challenge-series]").forEach((element) => {
                const matches = element.dataset.challengeSeries === active;
                element.classList.toggle("is-highlighted", Boolean(active && matches));
                element.classList.toggle("is-muted", Boolean(active && !matches));
            });
        };

        const clearSeriesHover = () => {
            state.hoveredSeries = null;
            focusSeries(null);
        };

        const toggleSeries = (series) => {
            state.pinnedSeries = state.pinnedSeries === series ? null : series;
            state.hoveredSeries = null;
            drawChart(rounds, maxPosition);
        };

        hideDotTooltip();
        svg.replaceChildren();
        svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

        const grid = createSvg("g", { class: "challenge-grid" });
        const step = maxY > 16 ? 2 : 1;

        for (let position = 1; position <= maxY; position += step) {
            const rowY = y(position);
            grid.append(createSvg("line", {
                x1: margin.left,
                y1: rowY,
                x2: width - margin.right,
                y2: rowY,
            }));

            const text = createSvg("text", {
                x: margin.left - 12,
                y: rowY + 4,
                "text-anchor": "end",
            });
            text.textContent = `P${position}`;
            grid.append(text);
        }
        const dnpLine = createSvg("line", {
            x1: margin.left,
            y1: dnpY,
            x2: width - margin.right,
            y2: dnpY,
            class: "challenge-dnp-grid-line",
        });
        grid.append(dnpLine);

        const dnpLabel = createSvg("text", {
            x: margin.left - 12,
            y: dnpY + 4,
            "text-anchor": "end",
            class: "challenge-dnp-axis-label",
        });
        dnpLabel.textContent = "DNP";
        grid.append(dnpLabel);

        svg.append(grid);

        const axis = createSvg("g", { class: "challenge-axis" });
        const frequency = Math.max(1, Math.ceil(rounds.length / 14));

        rounds.forEach((round, index) => {
            const columnX = x(index);
            axis.append(createSvg("line", {
                x1: columnX,
                y1: margin.top,
                x2: columnX,
                y2: dnpY,
            }));

            if (index % frequency === 0 || index === rounds.length - 1) {
                const label = createSvg("text", {
                    x: columnX,
                    y: dnpY + 36,
                    transform: (
                        `rotate(-38 ${columnX} ` +
                        `${dnpY + 36})`
                    ),
                    "text-anchor": "end",
                });
                label.textContent = round.label;
                axis.append(label);
            }
        });
        svg.append(axis);

        const makePath = (key, cssClass) => {
            const segments = [];
            let current = [];

            rounds.forEach((round, sourceIndex) => {
                const hasValue = Number.isInteger(round[key]);
                const breaksFinish = (
                    key === "finish" &&
                    round.did_not_participate
                );

                if (hasValue && !breaksFinish) {
                    current.push({ round, sourceIndex });
                    return;
                }

                if (current.length) {
                    segments.push(current);
                    current = [];
                }
            });

            if (current.length) segments.push(current);

            segments.forEach((points) => {
                if (!points.length) return;

                const d = points.map(({ round, sourceIndex }, index) => (
                    `${index ? "L" : "M"} ` +
                    `${x(sourceIndex).toFixed(2)} ${y(round[key]).toFixed(2)}`
                )).join(" ");

                const path = createSvg("path", {
                    d,
                    class: (
                        `${cssClass} challenge-interactive-series` +
                        (
                            state.pinnedSeries === key
                                ? " is-highlighted is-pinned"
                                : ""
                        ) +
                        (
                            state.pinnedSeries && state.pinnedSeries !== key
                                ? " is-muted"
                                : ""
                        )
                    ),
                    "data-challenge-series": key,
                    role: "button",
                    tabindex: 0,
                    "aria-label": (
                        `${seriesLabel[key]}. ` +
                        "Click to show exact positions for every round."
                    ),
                });

                path.addEventListener("pointerenter", () => focusSeries(key));
                path.addEventListener("pointerleave", clearSeriesHover);
                path.addEventListener("click", () => toggleSeries(key));
                path.addEventListener("keydown", (event) => {
                    if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        toggleSeries(key);
                    }
                });

                const titleElement = createSvg("title");
                titleElement.textContent = (
                    `${seriesLabel[key]} — click to show exact positions`
                );
                path.append(titleElement);
                svg.append(path);
            });
        };

        makePath("standing", "challenge-standing-line");
        makePath("finish", "challenge-finish-line");

        rounds.forEach((round, index) => {
            if (round.did_not_participate) {
                const point = createSvg("rect", {
                    x: x(index) - 5,
                    y: dnpY - 5,
                    width: 10,
                    height: 10,
                    rx: 2,
                    class: (
                        "challenge-dnp-point " +
                        "challenge-interactive-series" +
                        (
                            state.pinnedSeries === "finish"
                                ? " is-highlighted is-pinned"
                                : ""
                        ) +
                        (
                            state.pinnedSeries &&
                            state.pinnedSeries !== "finish"
                                ? " is-muted"
                                : ""
                        )
                    ),
                    "data-challenge-series": "finish",
                });

                point.addEventListener(
                    "pointerenter",
                    (event) => {
                        focusSeries("finish");
                        showDotTooltip(event, round, "finish");
                    }
                );
                point.addEventListener(
                    "pointermove",
                    (event) => showDotTooltip(event, round, "finish")
                );
                point.addEventListener(
                    "pointerleave",
                    () => {
                        clearSeriesHover();
                        hideDotTooltip();
                    }
                );
                point.addEventListener(
                    "click",
                    () => toggleSeries("finish")
                );
                svg.append(point);
            } else if (Number.isInteger(round.finish)) {
                const point = createSvg("circle", {
                    cx: x(index),
                    cy: y(round.finish),
                    r: 5,
                    class: (
                        round.finish === 1
                            ? "challenge-finish-point is-win"
                            : "challenge-finish-point"
                    ) +
                    " challenge-interactive-series" +
                    (
                        state.pinnedSeries === "finish"
                            ? " is-highlighted is-pinned"
                            : ""
                    ) +
                    (
                        state.pinnedSeries &&
                        state.pinnedSeries !== "finish"
                            ? " is-muted"
                            : ""
                    ),
                    "data-challenge-series": "finish",
                });

                point.addEventListener(
                    "pointerenter",
                    (event) => {
                        focusSeries("finish");
                        showDotTooltip(event, round, "finish");
                    }
                );
                point.addEventListener(
                    "pointermove",
                    (event) => showDotTooltip(event, round, "finish")
                );
                point.addEventListener(
                    "pointerleave",
                    () => {
                        clearSeriesHover();
                        hideDotTooltip();
                    }
                );
                point.addEventListener(
                    "click",
                    () => toggleSeries("finish")
                );
                svg.append(point);
            }

            if (Number.isInteger(round.standing)) {
                const point = createSvg("circle", {
                    cx: x(index),
                    cy: y(round.standing),
                    r: 4,
                    class: (
                        "challenge-standing-point " +
                        "challenge-interactive-series" +
                        (
                            state.pinnedSeries === "standing"
                                ? " is-highlighted is-pinned"
                                : ""
                        ) +
                        (
                            state.pinnedSeries &&
                            state.pinnedSeries !== "standing"
                                ? " is-muted"
                                : ""
                        )
                    ),
                    "data-challenge-series": "standing",
                });

                point.addEventListener(
                    "pointerenter",
                    (event) => {
                        focusSeries("standing");
                        showDotTooltip(event, round, "standing");
                    }
                );
                point.addEventListener(
                    "pointermove",
                    (event) => showDotTooltip(event, round, "standing")
                );
                point.addEventListener(
                    "pointerleave",
                    () => {
                        clearSeriesHover();
                        hideDotTooltip();
                    }
                );
                point.addEventListener(
                    "click",
                    () => toggleSeries("standing")
                );
                svg.append(point);
            }
        });

        if (state.pinnedSeries) {
            const key = state.pinnedSeries;
            const labelOffset = key === "finish" ? 17 : -11;

            rounds.forEach((round, index) => {
                const isDnp = (
                    key === "finish" &&
                    round.did_not_participate
                );
                if (!isDnp && !Number.isInteger(round[key])) return;

                const exact = createSvg("text", {
                    x: x(index),
                    y: isDnp
                        ? dnpY - 11
                        : y(round[key]) + labelOffset,
                    class: (
                        "challenge-exact-position " +
                        `challenge-exact-position-${key}` +
                        (isDnp ? " is-dnp" : "")
                    ),
                    "text-anchor": "middle",
                    "data-challenge-series": key,
                });
                exact.textContent = isDnp
                    ? "DNP"
                    : `P${round[key]}`;
                svg.append(exact);
            });
        }

        focusSeries(null);
    };

    const resetQuestionUi = () => {
        state.hintsUsed = 0;
        state.resolved = false;
        state.pinnedSeries = null;
        state.hoveredSeries = null;
        driverInput.value = "";
        seasonInput.value = "";
        feedback.textContent = "";
        hintList.innerHTML = '<li class="challenge-hint-placeholder">No hints used yet.</li>';
        reveal.hidden = true;
        newRunButton.hidden = true;
        nextButton.hidden = false;
        title.textContent = "Reading the archive…";
        kicker.textContent = state.mode === "daily" ? "Today’s mystery campaign" : "Mystery campaign";
        setLoadingVisible(true);
        setControlsEnabled(false);
        updateStats();
    };

    const loadQuestion = async () => {
        resetQuestionUi();
        const params = new URLSearchParams({ mode: state.mode, streak: String(state.streak) });
        if (state.usedIds.length) params.set("exclude", state.usedIds.slice(-80).join(","));
        try {
            params.set("_v", "full-season-dnp-v1");
            const response = await fetch(
                `/api/archive-challenge/question?${params}`,
                { cache: "no-store" }
            );
            if (!response.ok) throw new Error("Question request failed");
            state.question = await response.json();
            if (state.question.question_id) state.usedIds.push(state.question.question_id);
            drawChart(state.question.rounds, state.question.max_position);
            title.textContent = `${state.question.season_round_count || state.question.rounds.length}-round championship`;
            setLoadingVisible(false);

            if (state.mode === "daily" && localStorage.getItem(dailyStorageKey())) {
                const saved = JSON.parse(localStorage.getItem(dailyStorageKey()));
                feedback.textContent = saved.correct ? "You have already completed today’s challenge." : "Today’s attempt has already been used.";
                setControlsEnabled(false);
            } else {
                setControlsEnabled(true);
                driverInput.focus();
            }
        } catch (error) {
            console.error(error);
            setLoadingVisible(true, "The challenge could not be loaded. Please try again.");
        }
    };

    const useHint = async () => {
        if (!state.question || state.resolved || state.hintsUsed >= 4) return;
        try {
            const response = await fetch("/api/archive-challenge/hint", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ token: state.question.token, index: state.hintsUsed }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || "Hint failed");
            if (state.hintsUsed === 0) hintList.replaceChildren();
            const item = document.createElement("li"); item.textContent = payload.hint; hintList.append(item);
            state.hintsUsed += 1;
            updateStats();
            hintButton.disabled = state.hintsUsed >= 4;
            root.querySelector("[data-hint-cost]").textContent = state.hintsUsed >= 4 ? "No hints left" : "−1 point";
        } catch (error) {
            feedback.textContent = error.message;
        }
    };

    const submitGuess = async () => {
        if (!state.question || state.resolved) return;
        if (!driverInput.value.trim() || !seasonInput.value.trim()) {
            feedback.textContent = "Enter both a driver and a season.";
            return;
        }
        setControlsEnabled(false);
        try {
            const response = await fetch("/api/archive-challenge/guess", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    token: state.question.token,
                    driver: driverInput.value,
                    season: seasonInput.value,
                    hints_used: state.hintsUsed,
                }),
            });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || "Guess failed");
            state.resolved = true;
            const answer = payload.answer;
            answerTitle.textContent = `${answer.driver} · ${answer.season}`;
            answerSummary.textContent = `${answer.constructors.join(" / ")} · Championship P${answer.final_position} · ${answer.wins} wins · ${answer.podiums} podiums · ${answer.points} points.`;
            viewSeason.href = answer.season_url;
            reveal.hidden = false;

            if (payload.correct) {
                revealKicker.textContent = `Correct · +${payload.points} points`;
                state.streak += 1;
                state.score += payload.points;
                state.bestStreak = Math.max(state.bestStreak, state.streak);
                localStorage.setItem("f1archive-best-streak", String(state.bestStreak));
                feedback.textContent = "Correct. The streak continues.";
                if (state.mode === "daily") nextButton.hidden = true;
            } else {
                revealKicker.textContent = "Not quite";
                feedback.textContent = `${payload.driver_correct ? "Driver correct." : "Driver incorrect."} ${payload.season_correct ? "Season correct." : "Season incorrect."}`;
                if (state.mode === "endless") {
                    state.streak = 0;
                    nextButton.hidden = true;
                    newRunButton.hidden = false;
                }
            }

            if (state.mode === "daily") {
                localStorage.setItem(dailyStorageKey(), JSON.stringify({ correct: payload.correct, points: payload.points }));
            }
            updateStats();
        } catch (error) {
            feedback.textContent = error.message;
            setControlsEnabled(true);
        }
    };

    root.querySelectorAll("[data-mode]").forEach((button) => {
        button.addEventListener("click", () => {
            root.querySelectorAll("[data-mode]").forEach((item) => {
                const active = item === button;
                item.classList.toggle("active", active);
                item.setAttribute("aria-selected", String(active));
            });
            state.mode = button.dataset.mode;
            state.streak = 0;
            state.score = 0;
            state.usedIds = [];
            loadQuestion();
        });
    });
    hintButton.addEventListener("click", useHint);
    submitButton.addEventListener("click", submitGuess);
    nextButton.addEventListener("click", loadQuestion);
    newRunButton.addEventListener("click", () => { state.score = 0; state.usedIds = []; loadQuestion(); });
    [driverInput, seasonInput].forEach((input) => input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") submitGuess();
    }));

    updateStats();
    loadQuestion();
})();
