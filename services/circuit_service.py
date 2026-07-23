from __future__ import annotations

from functools import lru_cache
import xml.etree.ElementTree as ET

import requests
from markupsafe import Markup


SOURCE_BASE = (
    "https://raw.githubusercontent.com/julesr0y/"
    "f1-circuits-svg/refs/heads/main/"
    "circuits/detailed/white-outline"
)

CURRENT_LAYOUTS = {
    "albert_park": ("melbourne-2", "Melbourne Grand Prix Circuit"),
    "shanghai": ("shanghai-1", "Shanghai International Circuit"),
    "suzuka": ("suzuka-2", "Suzuka Circuit"),
    "miami": ("miami-1", "Miami International Autodrome"),
    "villeneuve": ("montreal-6", "Circuit Gilles Villeneuve"),
    "monaco": ("monaco-6", "Circuit de Monaco"),
    "catalunya": ("catalunya-6", "Circuit de Barcelona-Catalunya"),
    "red_bull_ring": ("spielberg-3", "Red Bull Ring"),
    "silverstone": ("silverstone-8", "Silverstone Circuit"),
    "spa": ("spa-francorchamps-4", "Circuit de Spa-Francorchamps"),
    "hungaroring": ("hungaroring-3", "Hungaroring"),
    "zandvoort": ("zandvoort-5", "Circuit Zandvoort"),
    "monza": ("monza-7", "Autodromo Nazionale Monza"),
    "madring": ("madring-1", "Madring"),
    "baku": ("baku-1", "Baku City Circuit"),
    "marina_bay": ("marina-bay-4", "Marina Bay Street Circuit"),
    "americas": ("austin-1", "Circuit of the Americas"),
    "rodriguez": ("mexico-city-3", "Autódromo Hermanos Rodríguez"),
    "interlagos": ("interlagos-2", "Autódromo José Carlos Pace"),
    "vegas": ("las-vegas-1", "Las Vegas Strip Circuit"),
    "losail": ("lusail-1", "Lusail International Circuit"),
    "yas_marina": ("yas-marina-2", "Yas Marina Circuit"),
    "bahrain": ("bahrain-1", "Bahrain International Circuit"),
    "jeddah": ("jeddah-1", "Jeddah Corniche Circuit"),
}

# The source SVG path order is opposite to the racing direction for these.
REVERSE_LAYOUTS = {"shanghai-1", "suzuka-2"}


def get_current_circuit_geometry(circuit_id: str) -> dict | None:
    layout = CURRENT_LAYOUTS.get(circuit_id)
    if not layout:
        return None

    layout_id, display_name = layout
    return {
        "layout_id": layout_id,
        "display_name": display_name,
        "svg_url": f"{SOURCE_BASE}/{layout_id}.svg",
        "source_name": "f1-circuits-svg by Jules Roy",
        "source_url": "https://github.com/julesr0y/f1-circuits-svg",
        "license": "CC BY 4.0",
        "interactive": False,
        "segments_authored": False,
    }


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


@lru_cache(maxsize=32)
def get_inline_circuit_geometry(layout_id: str) -> dict | None:
    """
    Load the repository's detailed SVG and retain its complete authored
    presentation: track, start/finish line and direction indicator.

    Interaction is layered over a clone of the principal track path. The
    browser detects the repository's own start-line graphic and rotates the
    editorial percentages around that verified zero point.
    """
    allowed_layouts = {layout[0] for layout in CURRENT_LAYOUTS.values()}
    if layout_id not in allowed_layouts:
        return None

    try:
        response = requests.get(f"{SOURCE_BASE}/{layout_id}.svg", timeout=12)
        response.raise_for_status()
        source_root = ET.fromstring(response.text)
    except (requests.RequestException, ET.ParseError):
        return None

    view_box = source_root.attrib.get("viewBox", "0 0 500 500")
    width = source_root.attrib.get("width", "500")
    height = source_root.attrib.get("height", "500")

    paths = []
    authored_elements = []

    for index, element in enumerate(list(source_root)):
        tag = _local_name(element.tag)
        if tag not in {"path", "line", "polyline", "polygon", "circle", "rect", "g"}:
            continue

        element.set("data-source-element", str(index))
        authored_elements.append(ET.tostring(element, encoding="unicode"))

        if tag == "path" and element.attrib.get("d"):
            paths.append({
                "index": index,
                "d": element.attrib["d"],
                "transform": element.attrib.get("transform", ""),
                "score": len(element.attrib["d"]),
            })

    if not paths:
        return None

    principal = max(paths, key=lambda item: item["score"])

    return {
        "layout_id": layout_id,
        "view_box": view_box,
        "width": width,
        "height": height,
        "source_markup": Markup("\n".join(authored_elements)),
        "path_d": principal["d"],
        "transform": principal["transform"],
        "principal_source_index": principal["index"],
        "reverse_direction": layout_id in REVERSE_LAYOUTS,
    }
