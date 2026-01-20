import pytest
from metagenomescope.graph.node import Node
from metagenomescope.config import SPLIT_LEFT, SPLIT_RIGHT, FWD
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
        b.to_dot(indent=" ")
        == ' 0 [width=3,height=3,shape=rect,label="B"];\n'
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
