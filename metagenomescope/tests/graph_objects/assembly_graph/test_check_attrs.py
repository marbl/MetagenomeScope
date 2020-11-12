from metagenomescope.graph_objects import AssemblyGraph
import pytest


def test_check_attrs_node():
    with pytest.raises(ValueError) as einfo:
        AssemblyGraph("metagenomescope/tests/input/check_attrs_test_node.gml")
    assert "has reserved attribute(s) {'height'}." in str(einfo.value)


def test_check_attrs_edge():
    with pytest.raises(ValueError) as einfo:
        AssemblyGraph("metagenomescope/tests/input/check_attrs_test_edge.gml")
    assert "has reserved attribute(s) {'ctrl_pt_coords'}." in str(einfo.value)
