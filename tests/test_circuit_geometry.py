from services.circuit_service import (
    CURRENT_LAYOUTS,
    get_current_circuit_geometry,
)


def test_every_current_layout_builds_an_svg_url():
    assert len(CURRENT_LAYOUTS) >= 22

    for circuit_id in CURRENT_LAYOUTS:
        geometry = get_current_circuit_geometry(circuit_id)
        assert geometry is not None
        assert geometry["svg_url"].endswith(".svg")
        assert geometry["license"] == "CC BY 4.0"


def test_unknown_historic_layout_falls_back_cleanly():
    assert get_current_circuit_geometry("unknown_circuit") is None


def test_key_2026_venues_use_expected_layouts():
    assert (
        get_current_circuit_geometry("silverstone")["layout_id"]
        == "silverstone-8"
    )
    assert (
        get_current_circuit_geometry("monaco")["layout_id"]
        == "monaco-6"
    )
    assert (
        get_current_circuit_geometry("madring")["layout_id"]
        == "madring-1"
    )
