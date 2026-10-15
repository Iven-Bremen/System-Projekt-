import Komunikation
import Send
from Send import OSTechG, OSTechS


def test_ostech_tec_measurements_use_controller_x_selector():
    assert Komunikation.OSTECHCommand.XTA.value.command == "xTA"
    assert Komunikation.OSTECHCommand.XTCA.value.command == "xTCA"
    assert Komunikation.OSTECHCommand.XTVA.value.command == "xTVA"
    assert OSTechG.T1A.command == "xTA"
    assert OSTechG.T1CA.command == "xTCA"
    assert OSTechG.T1VA.command == "xTVA"


def test_ostech_tec_setting_queries_use_controller_x_selector():
    tec_queries = {
        query for key, query, _, _ in Komunikation.OSTECH_SETTING_QUERIES
        if key.startswith("1T")
    }
    assert tec_queries == {
        "xTT", "xTLU", "xTLL", "xTCL", "xTCCK", "xTCCN", "xTCCV"
    }
    assert OSTechS.T1TT.command == "xTT"
    assert OSTechS.T1CR.command == "xTCR"
    assert Send._OSTECH_ACTION_DESIRED["xTCR"] == ("1TC", True)
    assert Send._OSTECH_ACTION_DESIRED["xTCS"] == ("1TC", False)