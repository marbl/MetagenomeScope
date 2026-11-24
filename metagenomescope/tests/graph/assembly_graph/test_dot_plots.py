import pytest
from metagenomescope.graph import AssemblyGraph
from metagenomescope.errors import UIError


def test_order_nodes_in_path_single():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    id_list = ag.get_node_ids("1")
    assert len(id_list) == 1
    assert ag.order_nodes_in_path(id_list) == "1"


def test_order_nodes_in_path_simple():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    id_list = ag.get_node_ids("5, 3, -4")
    assert len(id_list) == 3
    assert ag.order_nodes_in_path(id_list) == "3, -4, 5"


def test_order_nodes_in_path_no_path():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    id_list = ag.get_node_ids("5, 3, 4")
    assert len(id_list) == 3
    with pytest.raises(UIError) as ei:
        ag.order_nodes_in_path(id_list)
    assert "not a clear single path" in str(ei.value)


def test_order_nodes_in_path_nothing_selected():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    with pytest.raises(UIError) as ei:
        ag.order_nodes_in_path([])
    assert str(ei.value) == "No nodes selected."
