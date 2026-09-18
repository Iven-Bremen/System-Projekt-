import State


def test_lockin_display_uses_live_state_values():
    State.update_values({
        "OUTP1": 0.52149,
        "OUTP3": 0.90000,
        "OUTR1": 0.15000,
        "OAUX1": 1.23000,
        "OAUX2": 2.34000,
        "OUTP2": 0.41111,
        "OUTP4": 135.0,
        "OUTR2": 0.22000,
        "OAUX3": 3.45000,
        "OAUX4": 4.56000,
        "PHAS": 135.0,
    })

    value, unit = State.get_display_value_for_selection("CH1", "X")
    assert value == 0.52149
    assert unit == "V"

    value, unit = State.get_display_value_for_selection("CH2", "Phase (θ)")
    assert value == 135.0
    assert unit == "°"
