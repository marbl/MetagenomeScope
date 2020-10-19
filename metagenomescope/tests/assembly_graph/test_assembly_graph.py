from metagenomescope.graph_objects import AssemblyGraph
from metagenomescope.input_node_utils import negate_node_id
import networkx as nx
from pytest import approx

def test_scale_nodes():
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    # This graph has six nodes, with lengths 8, 10, 21, 7, 8, 4.
    #                          (for node IDs 1,  2,  3, 4, 5, 6.)
    ag.scale_nodes()
    nodename2rl = {
        "1" : approx(0.4180047),
        "2" : approx(0.5525722),
        "3" : 1,
        "4" : approx(0.3374782),
        "5" : approx(0.4180047),
        "6" : 0
    }
    seen_nodenames = []
    for node in ag.digraph.nodes:
        print(nx.get_node_attributes(ag.digraph, "relative_length"))
        name = ag.digraph.nodes[node]["name"]
        rl = ag.digraph.nodes[node]["relative_length"]
        if name in nodename2rl:
            assert rl == nodename2rl[name]
        else:
            assert rl == nodename2rl[negate_node_id(name)]
        seen_nodenames.append(name)
    assert len(seen_nodenames) == 12

def test_scale_nodes_all_lengths_equal():
    pass
    #ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    ## This graph has six nodes, with lengths 8, 10, 21, 7, 8, 4.
    #ag.scale_nodes()
    #assert ag.digraph.nodes["1"]["relative_length"] = 
