import pytest
from metagenomescope import config
from metagenomescope.graph import Pattern, Node, Edge, validators
from metagenomescope.errors import WeirdError
from metagenomescope.graph.pattern import is_pattern, verify_vr_and_nodes_good


def test_is_pattern():
    assert not is_pattern(Node(0, "asdf", {}))
    # WOW there's a lot of junk we need to have to init a Pattern lol
    # this is representing a chain from node 5 -> node 6
    assert is_pattern(
        Pattern(
            1,
            validators.ValidationResults(
                config.PT_CHAIN, True, [5, 6], [5], [6]
            ),
            [Node(5, "5", {}), Node(6, "6", {})],
            [Edge(10, 5, 6, {})],
        )
    )

def test_verify_vr_and_nodes_good_okay():
    verify_vr_and_nodes_good(
        validators.ValidationResults(
            config.PT_CHAIN, True, [5, 6], [5], [6]
        ),
        [Node(6, "six", {}), Node(5, "five", {})],
    )


def test_verify_vr_and_nodes_good_invalid_vr():
    with pytest.raises(WeirdError) as ei:
        verify_vr_and_nodes_good(validators.ValidationResults(), [])
    assert str(ei.value) == (
        "Can't create a Pattern from an invalid ValidationResults?"
    )


def test_verify_vr_and_nodes_good_node_mismatch():
    with pytest.raises(WeirdError) as ei:
        verify_vr_and_nodes_good(
            validators.ValidationResults(
                config.PT_CHAIN, True, [5, 6], [5], [6]
            ),
            [Node(6, "six", {}), Node(7, "seven", {})],
        )
    assert str(ei.value) == "Different node IDs: [6, 7] vs. [5, 6]"
