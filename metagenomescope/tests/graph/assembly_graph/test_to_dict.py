import pytest
from metagenomescope.errors import GraphError
from metagenomescope.graph import AssemblyGraph


def test_to_dict_fails_if_layout_not_done():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    with pytest.raises(GraphError) as ei:
        ag.to_dict()
    assert str(ei.value) == (
        "You need to call .layout() on this AssemblyGraph object before "
        "calling .to_dict()."
    )
