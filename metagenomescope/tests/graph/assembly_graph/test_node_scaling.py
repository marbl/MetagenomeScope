from metagenomescope.graph import AssemblyGraph
from metagenomescope.input_node_utils import negate_node_id
from metagenomescope import config
from pytest import approx


def test_scale_nodes():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    # This graph has six nodes, with lengths 8, 10, 21, 7, 8, 4.
    #                          (for node IDs 1,  2,  3, 4, 5, 6.)
    nodename2rl = {
        "1": approx(0.4180047),
        "2": approx(0.5525722),
        "3": 1,
        "4": approx(0.3374782),
        "5": approx(0.4180047),
        "6": 0,
    }
    nodename2lp = {
        "1": config.MID_LONGSIDE_PROPORTION,
        "2": config.HIGH_LONGSIDE_PROPORTION,
        "3": config.HIGH_LONGSIDE_PROPORTION,
        "4": config.MID_LONGSIDE_PROPORTION,
        "5": config.MID_LONGSIDE_PROPORTION,
        "6": config.LOW_LONGSIDE_PROPORTION,
    }
    seen_nodenames = []
    for node in ag.nodeid2obj:
        name = node.data["name"]
        rl = node.relative_length
        lp = node.longside_proportion
        if name in nodename2rl:
            assert rl == nodename2rl[name]
            assert lp == nodename2lp[name]
        else:
            negated_name = negate_node_id(name)
            assert rl == nodename2rl[negated_name]
            assert lp == nodename2lp[negated_name]
        seen_nodenames.append(name)
    assert len(seen_nodenames) == 12


def test_scale_nodes_all_lengths_equal():
    ag = AssemblyGraph("metagenomescope/tests/input/loop.gfa")
    # all of the nodes in this graph have length 3
    for node in ag.nodeid2obj:
        assert node.relative_length == 0.5
        assert node.longside_proportion == config.MID_LONGSIDE_PROPORTION


def test_compute_node_dimensions():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")

    def get_dims(rl, lp):
        area = config.MIN_NODE_AREA + (
            rl * (config.MAX_NODE_AREA - config.MIN_NODE_AREA)
        )
        hgt = area**lp
        wid = area / hgt
        return (wid, hgt)

    # Relative length and longside proportions reused from test_scale_nodes()
    nodename2dims = {
        "1": get_dims(0.4180047, config.MID_LONGSIDE_PROPORTION),
        "2": get_dims(0.5525722, config.HIGH_LONGSIDE_PROPORTION),
        "3": get_dims(1, config.HIGH_LONGSIDE_PROPORTION),
        "4": get_dims(0.3374782, config.MID_LONGSIDE_PROPORTION),
        "5": get_dims(0.4180047, config.MID_LONGSIDE_PROPORTION),
        "6": get_dims(0, config.LOW_LONGSIDE_PROPORTION),
    }

    seen_nodenames = []
    for node in ag.nodeid2obj:
        name = node.data["name"]
        w = node.width
        h = node.height
        exp_data = ()
        if name in nodename2dims:
            exp_data = nodename2dims[name]
        else:
            exp_data = nodename2dims[negate_node_id(name)]
        assert w == approx(exp_data[0])
        assert h == approx(exp_data[1])
        seen_nodenames.append(name)
    assert len(seen_nodenames) == 12


def test_compute_node_dimensions_all_lengths_equal():
    ag = AssemblyGraph("metagenomescope/tests/input/loop.gfa")
    default_area = config.MIN_NODE_AREA + (
        0.5 * (config.MAX_NODE_AREA - config.MIN_NODE_AREA)
    )
    default_height = default_area**config.MID_LONGSIDE_PROPORTION
    default_width = default_area / default_height

    # This double-checks that the defaults we expect here are computed
    # properly. If the config values are updated that may break this, so feel
    # free to comment this out if that happens to you.
    assert default_area == 5.5
    assert default_height == approx(3.115839)
    assert default_width == approx(1.765174)

    for node in ag.nodeid2obj:
        assert node.height == default_height
        assert node.width == default_width
