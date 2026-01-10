# Previously, we stored node/edge data in dicts in a NetworkX graph, which
# had the potential for conflicts between "real" data (e.g. node length,
# edge multiplicity) and "internal" data (e.g. node height, edge control
# points, ...) -- but after the refactor these conflicts should no longer pose
# a problem. These tests verify this.
from metagenomescope import config
from metagenomescope.graph import AssemblyGraph


def test_node_attr_conflict():
    # Shouldn't fail with an error
    g = AssemblyGraph("metagenomescope/tests/input/check_attrs_test_node.gml")
    six_seen = False
    for n in g.nodeid2obj.values():
        # A node having the attribute "height" is ok now! nature is healing
        if n.name == "6":
            assert n.data == {
                "orientation": config.FWD,
                "length": 1,
                "height": "20",
            }
            six_seen = True
        else:
            assert n.data == {"orientation": config.FWD, "length": 1}
    assert six_seen

    for e in g.edgeid2obj.values():
        if not e.is_fake:
            assert e.data == {
                "orientation": "EB",
                "mean": -1,
                "stdev": 5,
                "bsize": 5,
            }


def test_edge_attr_conflict():
    # Shouldn't fail with an error
    g = AssemblyGraph("metagenomescope/tests/input/check_attrs_test_edge.gml")

    for n in g.nodeid2obj.values():
        assert n.data == {"orientation": config.FWD, "length": 1}

    six_seen = False
    for e in g.edgeid2obj.values():
        if not e.is_fake:
            # an edge with the attribute "ctrl_pt_coords" is also ok :D
            # (note that we use new_src_id here because this graph will have
            # some patterns identified, meaning some nodes will get
            # split/removed/etc.)
            if g.nodeid2obj[e.new_src_id].name == "6":
                assert e.data == {
                    "orientation": "EB",
                    "mean": -1,
                    "stdev": 5,
                    "bsize": 5,
                    "ctrl_pt_coords": "1234",
                }
                six_seen = True
            else:
                assert e.data == {
                    "orientation": "EB",
                    "mean": -1,
                    "stdev": 5,
                    "bsize": 5,
                }
    assert six_seen
