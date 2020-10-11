from networkx.drawing.nx_agraph import write_dot
from metagenomescope.graph_objects import AssemblyGraph


def test_simple_hierarch_decomp():
    r"""I don't know why I called this test "simple", but whatever. The input
        graph looks like

        3
       / \
      1   4 -> 5 ---> 6 -------> 7 -> 14 -> 15 -> 16
     / \ /           /          /
    0   2          11          /
     \            /           /
      8 -> 9 -> 10 -> 12 -> 13

    ...and the following simplifications should happen:

        3
       / \
      1   [Chain] --> 6 ------> [Chain]
     / \ /           /         /
    0   2          11         /
     \            /          /
      \--> [Chain] -> [Chain]

      22=[Bubble]=23 -> 6 ------> [Chain]
     /                 /         /
    0                11         /
     \              /          /
      \----> [Chain] -> [Chain]

      [Chain] --------> 6 ------> [Chain]
     /                 /         /
    0                11         /
     \              /          /
      \----> [Chain] -> [Chain]

    Arguably, the final simplification with the 22->Bubble->23 thing isn't
    really useful. I am not sure what the best way to handle this is.
    """
    ag = AssemblyGraph(
        "metagenomescope/tests/input/hierarchical_test_graph.gml"
    )
    ag.hierarchically_identify_patterns()
    write_dot(ag.decomposed_digraph, "dec.gv")
    # This is with the "maximum" decomposition settings for this test graph.
    assert len(ag.decomposed_digraph.nodes) == 7
    assert len(ag.decomposed_digraph.edges) == 8
    assert len(ag.chains) == 4
    assert len(ag.cyclic_chains) == 0
    assert len(ag.frayed_ropes) == 0
    assert len(ag.bubbles) == 1
