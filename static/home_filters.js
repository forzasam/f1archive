const allDrivers = JSON.parse(document.getElementById("driver-data").textContent);
const allConstructors = JSON.parse(document.getElementById("constructor-data").textContent);
const filterApiUrl = "/api/filter-options";

function normalise(value) {
    return value
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .trim();
}

function matchScore(name, query) {
    const normalisedName = normalise(name);
    const parts = normalisedName.split(/\s+/);
    const terms = query.split(/\s+/).filter(Boolean);
    if (!terms.every((term) => normalisedName.includes(term))) return null;

    return terms.reduce((score, term) => {
        if (parts.some((part) => part === term)) return score + 100;
        if (parts.some((part) => part.startsWith(term))) return score + 70;
        if (normalisedName.startsWith(term)) return score + 50;
        return score + 20;
    }, 0);
}

function createAutocomplete({ kind, items, onSelect }) {
    const input = document.getElementById(`${kind}-search`);
    const hidden = document.getElementById(`${kind}-filter`);
    const panel = document.getElementById(`${kind}-results`);
    const list = document.getElementById(`${kind}-results-list`);
    const empty = document.getElementById(`${kind}-no-results`);
    let sourceItems = [...items];
    let visibleItems = [];
    let activeIndex = -1;

    function close() {
        panel.hidden = true;
        input.setAttribute("aria-expanded", "false");
        activeIndex = -1;
    }

    function setSource(nextItems) {
        sourceItems = [...nextItems];
        if (document.activeElement === input && input.value.trim()) render();
    }

    function clearSelection({ keepText = false } = {}) {
        hidden.value = "";
        if (!keepText) input.value = "";
    }

    function choose(item) {
        input.value = item.name;
        hidden.value = item.id;
        close();
        onSelect(item);
    }

    function setActive(index) {
        const buttons = [...list.querySelectorAll(".autocomplete-option")];
        buttons.forEach((button, i) => {
            button.classList.toggle("is-active", i === index);
            button.setAttribute("aria-selected", i === index ? "true" : "false");
        });
        activeIndex = index;
        buttons[index]?.scrollIntoView({ block: "nearest" });
    }

    function render() {
        const query = normalise(input.value);
        hidden.value = "";
        list.replaceChildren();
        if (!query) return close();

        visibleItems = sourceItems
            .map((item) => ({ item, score: matchScore(item.name, query) }))
            .filter(({ score }) => score !== null)
            .sort((a, b) => b.score - a.score || a.item.name.localeCompare(b.item.name))
            .slice(0, 6)
            .map(({ item }) => item);

        empty.hidden = visibleItems.length !== 0;
        visibleItems.forEach((item) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "autocomplete-option";
            button.setAttribute("role", "option");
            button.setAttribute("aria-selected", "false");

            const badge = document.createElement("span");
            badge.className = "autocomplete-badge";
            badge.textContent = kind === "driver"
                ? item.name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("")
                : item.name.slice(0, 2).toUpperCase();

            const text = document.createElement("span");
            text.className = "autocomplete-option-text";
            const name = document.createElement("strong");
            name.textContent = item.name;
            text.appendChild(name);
            if (item.nationality) {
                const nationality = document.createElement("small");
                nationality.textContent = item.nationality;
                text.appendChild(nationality);
            }

            button.append(badge, text);
            button.addEventListener("mousedown", (event) => event.preventDefault());
            button.addEventListener("click", () => choose(item));
            list.appendChild(button);
        });

        panel.hidden = false;
        input.setAttribute("aria-expanded", "true");
        activeIndex = -1;
    }

    input.addEventListener("input", render);
    input.addEventListener("focus", render);
    input.addEventListener("keydown", (event) => {
        if (panel.hidden) return;
        if (event.key === "ArrowDown" && visibleItems.length) {
            event.preventDefault();
            setActive((activeIndex + 1) % visibleItems.length);
        } else if (event.key === "ArrowUp" && visibleItems.length) {
            event.preventDefault();
            setActive((activeIndex - 1 + visibleItems.length) % visibleItems.length);
        } else if (event.key === "Enter" && visibleItems.length) {
            event.preventDefault();
            choose(visibleItems[activeIndex >= 0 ? activeIndex : 0]);
        } else if (event.key === "Escape") close();
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest(`[data-filter-kind="${kind}"]`)) close();
    });

    return { setSource, clearSelection, getSelectedId: () => hidden.value };
}

async function fetchRelated(query) {
    const response = await fetch(`${filterApiUrl}?${query.toString()}`);
    if (!response.ok) throw new Error("Could not update related filter options");
    return response.json();
}

let driverAutocomplete;
let constructorAutocomplete;

async function driverSelected(driver) {
    try {
        const data = await fetchRelated(new URLSearchParams({ driver: driver.id }));
        constructorAutocomplete.setSource(data.constructors);
        const selectedConstructor = constructorAutocomplete.getSelectedId();
        if (selectedConstructor && !data.constructors.some((item) => item.id === selectedConstructor)) {
            constructorAutocomplete.clearSelection();
        }
    } catch (error) {
        console.error(error);
        constructorAutocomplete.setSource(allConstructors);
    }
}

async function constructorSelected(constructor) {
    try {
        const data = await fetchRelated(new URLSearchParams({ constructor: constructor.id }));
        driverAutocomplete.setSource(data.drivers);
        const selectedDriver = driverAutocomplete.getSelectedId();
        if (selectedDriver && !data.drivers.some((item) => item.id === selectedDriver)) {
            driverAutocomplete.clearSelection();
        }
    } catch (error) {
        console.error(error);
        driverAutocomplete.setSource(allDrivers);
    }
}

driverAutocomplete = createAutocomplete({
    kind: "driver",
    items: allDrivers,
    onSelect: driverSelected,
});

constructorAutocomplete = createAutocomplete({
    kind: "constructor",
    items: allConstructors,
    onSelect: constructorSelected,
});

const initialDriver = document.getElementById("driver-filter").value;
const initialConstructor = document.getElementById("constructor-filter").value;
if (initialDriver) driverSelected({ id: initialDriver });
else if (initialConstructor) constructorSelected({ id: initialConstructor });
