import pytest
from metagenomescope.graph.node import Node
from metagenomescope.layout import layout_config
from metagenomescope import config
from metagenomescope.errors import WeirdError


def check_nolength_node_layout(nlay):
    assert nlay.orientation is None
    assert nlay.length is None
    assert nlay.shape == "rect"
    assert nlay.width == layout_config.NOLENGTH_NODE_WIDTH
    assert nlay.height == layout_config.NOLENGTH_NODE_HEIGHT


def test_init_no_length_unsplit():
    # Nodes with no length can happen when we visualize edge-centric
    # graphs -- as of writing, LJA or Flye DOT files. These should
    # be drawn as small circles, each with the same size.
    n = Node(0, "0", {})
    check_nolength_node_layout(n.layout)


def test_update_split_no_length():
    n = Node(0, "0", {})
    check_nolength_node_layout(n.layout)

    # splitting this node shouldn't change its shape or dimensions; we'll
    # change it into a semicircle on the cytoscape.js side of things
    n.layout.update_split(config.SPLIT_LEFT)
    check_nolength_node_layout(n.layout)

    n.layout.update_split(config.SPLIT_RIGHT)
    check_nolength_node_layout(n.layout)

    n.layout.update_split(None)
    check_nolength_node_layout(n.layout)


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

    # verify that "units" is no longer an optional parameter, so calling
    # get_dims() should raise a TypeError.
    with pytest.raises(TypeError) as ei:
        n.layout.get_dims()
