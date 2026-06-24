import pytest
from metagenomescope.graph.node import Node
from metagenomescope import cy_config, ui_config
from metagenomescope.layout import layout_config
from metagenomescope.layout.layout_config import PIXELS_PER_INCH as PPI
from metagenomescope.config import SPLIT_LEFT, SPLIT_RIGHT, FWD, REV
from metagenomescope.errors import WeirdError


def test_constructor_counterpart_but_no_split():
    c = Node(0, "CoolNodeCounterpart", {})
    with pytest.raises(WeirdError) as ei:
        Node(1, "CoolNode", {}, counterpart_node=c)
    assert str(ei.value) == (
        "Creating Node 1: counterpart_node is not None, but split is None?"
    )


def test_constructor_split_but_no_counterpart():
    with pytest.raises(WeirdError) as ei:
        Node(0, "B", {}, split=SPLIT_LEFT)
    assert str(ei.value) == (
        f"Creating Node 0: split is {SPLIT_LEFT}, but no counterpart "
        "Node specified?"
    )


def test_constructor_counterpart_already_taken():
    b = Node(0, "B", {})
    c = Node(1, "C", {}, counterpart_node=b, split=SPLIT_LEFT)
    with pytest.raises(WeirdError) as ei:
        Node(2, "D", {}, counterpart_node=c, split=SPLIT_RIGHT)
    assert str(ei.value) == (
        f"Node 1 (name: C-L): split attr is already {SPLIT_LEFT}?"
    )


def test_make_into_split_already_split():
    b = Node(0, "B", {})
    # again, we can "cheat" to make this work
    b.split = SPLIT_LEFT
    with pytest.raises(WeirdError) as ei:
        b.make_into_split(1, SPLIT_RIGHT)
    assert str(ei.value) == (
        f"Node 0 (name: B): split attr is already {SPLIT_LEFT}?"
    )


def test_make_into_split_already_has_counterpart():
    b = Node(0, "B", {})
    # again, kind of cheating
    b.counterpart_node_id = 1
    with pytest.raises(WeirdError) as ei:
        b.make_into_split(1, SPLIT_RIGHT)
    assert str(ei.value) == (
        "Node 0 (name: B): counterpart_node_id attr is already 1?"
    )


def test_unsplit_on_non_split_node():
    b = Node(0, "B", {})
    with pytest.raises(WeirdError) as ei:
        b.unsplit()
    assert str(ei.value) == (
        "Node 0 (name: B) can't be unsplit; it's already not split?"
    )


def test_unsplit_on_node_without_counterpart():
    b = Node(0, "B", {})
    b.split = SPLIT_RIGHT
    with pytest.raises(WeirdError) as ei:
        b.unsplit()
    assert str(ei.value) == (
        "Node 0 (name: B) can't be unsplit; doesn't have a counterpart node "
        "ID?"
    )


def test_set_cc_num():
    b = Node(0, "B", {})
    assert b.cc_num is None
    b.set_cc_num(1)
    assert b.cc_num == 1
    # AND THE CROWD GOES WILD


def test_to_dot_non_split():
    b = Node(0, "B", {})
    b.layout.width = b.layout.height = 3
    assert (
        b.to_dot(indent=" ") == ' 0 [width=3,height=3,shape=rect,label="B"];\n'
    )


def test_to_dot_split():
    b = Node(0, "B", {"orientation": FWD})
    c = Node(
        1, "C", {"orientation": FWD}, counterpart_node=b, split=SPLIT_LEFT
    )
    b.layout.width = b.layout.height = 3
    c.layout.width = c.layout.height = 1
    assert (
        c.to_dot(indent=" ")
        == ' 1 [width=1,height=1,shape=rect,label="C-L"];\n'
    )
    assert (
        b.to_dot(indent=" ")
        == ' 0 [width=3,height=3,shape=rect,label="B-R"];\n'
    )


def test_to_cyjs_unoriented_simple():
    # a node in a Flye/LJA DOT file or something
    n = Node(0, "N", {})
    n.rand_idx = 5
    assert n.to_cyjs([]) == {
        "data": {
            "id": "0",
            "label": "N",
            "ntype": cy_config.NODE_DATA_TYPE,
            "w": layout_config.NOLENGTH_NODE_WIDTH * PPI,
            "h": layout_config.NOLENGTH_NODE_HEIGHT * PPI,
        },
        "classes": "nonpattern unoriented splitN noderand5",
    }


def test_to_cyjs_fwd_is_isolated_circle():
    n = Node(
        1,
        "Node1",
        {"length": 100, "orientation": FWD},
        is_isolated_circle=True,
    )
    n.rand_idx = 3
    assert n.to_cyjs([]) == {
        "data": {
            "id": "1",
            "label": "Node1",
            "ntype": cy_config.NODE_DATA_TYPE,
            # just get the layout dimensions from the underlying NodeLayout
            # object; we already test that elsewhere, so I don't think it is
            # worth going to the trouble of computing that here as well
            # (particularly since the node scaling code will probs be updated
            # again in the future...)
            "w": n.layout.width * PPI,
            "h": n.layout.height * PPI,
        },
        "classes": "nonpattern fwd isolatedcircle noderand3",
    }


def test_to_cyjs_rev_child_of_pattern():
    n = Node(
        1,
        "Node1",
        {"length": 100, "orientation": REV},
    )
    n.parent_id = 20
    n.rand_idx = 1

    # with scope_settings == [], this node will not have a defined
    # parent in its Cytoscape.js data representation
    assert n.to_cyjs([]) == {
        "data": {
            "id": "1",
            "label": "Node1",
            "ntype": cy_config.NODE_DATA_TYPE,
            "w": n.layout.width * PPI,
            "h": n.layout.height * PPI,
        },
        "classes": "nonpattern rev splitN noderand1",
    }

    # but if we are drawing the graph with patterns shown, then
    # this node will have a parent!
    assert n.to_cyjs([ui_config.SHOW_PATTERNS]) == {
        "data": {
            "id": "1",
            "label": "Node1",
            "ntype": cy_config.NODE_DATA_TYPE,
            "w": n.layout.width * PPI,
            "h": n.layout.height * PPI,
            "parent": "20",
        },
        "classes": "nonpattern rev splitN noderand1",
    }


def test_to_cyjs_show_patterns_but_no_parent():
    # What happens when a node has no parent but we have "show patterns"
    # given in the scope settings anyway? The answer is that we just don't
    # say the node has a parent, it's really not hard, this isn't complicated,
    # but let's test it anyway i guess just out of paranoia
    n = Node(
        1,
        "Node1",
        {"length": 100, "orientation": REV},
    )
    n.rand_idx = 1

    assert n.parent_id is None

    assert n.to_cyjs([ui_config.SHOW_PATTERNS]) == {
        "data": {
            "id": "1",
            "label": "Node1",
            "ntype": cy_config.NODE_DATA_TYPE,
            "w": n.layout.width * PPI,
            "h": n.layout.height * PPI,
        },
        "classes": "nonpattern rev splitN noderand1",
    }
