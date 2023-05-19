import pytest
from metagenomescope.graph.node import Node
from metagenomescope.config import SPLIT_LEFT, SPLIT_RIGHT
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
        "Creating split Node 2: counterpart Node 1 (name: C-L) already has a "
        "counterpart Node (0)?"
    )


def test_constructor_counterpart_already_split():
    b = Node(0, "B", {})
    # Trying to create a Node with a split but no counterpart (the only way to
    # trigger the particular error we're trying to test here) will cause the
    # Node constructor to fail with an error about *that*. To trigger our
    # desired error, we can modify b.split after its creation.
    b.split = SPLIT_LEFT
    with pytest.raises(WeirdError) as ei:
        Node(1, "C", {}, counterpart_node=b, split=SPLIT_RIGHT)
    assert str(ei.value) == (
        f"Creating split Node 1 with split of {SPLIT_RIGHT}: counterpart "
        f"{b} already has a split of {SPLIT_LEFT}?"
    )


def test_make_into_split_already_split():
    b = Node(0, "B", {})
    # again, we can "cheat" to make this work
    b.split = SPLIT_LEFT
    with pytest.raises(WeirdError) as ei:
        b.make_into_split(1, SPLIT_RIGHT)
    assert str(ei.value) == (
        f"Node 0 (name: B): .split attr is already {SPLIT_LEFT}?"
    )
