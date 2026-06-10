import pytest
from metagenomescope.graph.node import Node
from metagenomescope.layout import layout_config
from metagenomescope.errors import WeirdError


def test_get_dims():
    # note that this does not actually care what n.layout.width
    # and n.layout.height *are*. We just care about if the conversions
    # are done okay. (The reason for this is that I will probably change
    # the code that sets node dimensions a bunch, to the point where I
    # think testing it will just be a waste of time since I'll keep
    # breaking / updating this test.)

    n = Node(0, "CoolNode", {"length": 5003})

    w = n.layout.width
    h = n.layout.height
    # the width and height of the layout are stored in inches
    assert n.layout.get_dims(units=layout_config.UNIT_GV_INCHES) == (w, h)

    # hardcoding 72 here because that is directly from Graphviz' docs:
    # https://graphviz.org/doc/info/attrs.html#points
    assert n.layout.get_dims(units=layout_config.UNIT_GV_POINTS) == (
        w * 72,
        h * 72,
    )

    # this is the weird one. See
    # https://github.com/marbl/MetagenomeScope/issues/166 for context.
    assert n.layout.get_dims(units=layout_config.UNIT_CY_PIXELS) == (
        w * 54,
        h * 54,
    )

    with pytest.raises(WeirdError) as ei:
        n.layout.get_dims(units="blah")
    assert str(ei.value) == 'Unrecognized unit: "blah"'
