import pytest

from metagenomescope import input_node_utils


def test_negate_node_id():
    with pytest.raises(ValueError) as ei:
        input_node_utils.negate_node_id("")
    assert "Can't negate an empty node ID" in str(ei.value)
    assert input_node_utils.negate_node_id("1") == "-1"
    assert input_node_utils.negate_node_id("-3") == "3"
    assert input_node_utils.negate_node_id("20") == "-20"
    assert input_node_utils.negate_node_id("-100") == "100"
    # IDs should be stored as strings -- so we should be able to negate them
    # regardless of if it makes sense mathematically
    assert input_node_utils.negate_node_id("0") == "-0"
    assert input_node_utils.negate_node_id("-0") == "0"
    assert input_node_utils.negate_node_id("contig_id_123") == "-contig_id_123"
    assert input_node_utils.negate_node_id("-contig_id_123") == "contig_id_123"
    assert input_node_utils.negate_node_id("abcdef") == "-abcdef"
    assert input_node_utils.negate_node_id("-abcdef") == "abcdef"
