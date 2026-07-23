from services.circuit_service import get_current_circuit_geometry


def test_australia_uses_a_local_authored_package():
    geometry = get_current_circuit_geometry("albert_park")
    assert geometry is not None
    assert geometry["layout_id"] == "australia"
    assert geometry["svg_template"] == "circuits/australia.svg"
    assert geometry["interactive"] is True
    assert geometry["segments_authored"] is True


def test_other_circuits_are_not_yet_authored():
    assert get_current_circuit_geometry("monaco") is None
    assert get_current_circuit_geometry("unknown_circuit") is None
