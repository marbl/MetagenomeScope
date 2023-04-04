import networkx as nx
from metagenomescope.graph import validators


def get_test_path_graph(num_nodes):
    """Returns a "path graph" as a nx.MultiDiGraph."""
    return nx.path_graph(num_nodes, nx.MultiDiGraph())


def get_intervening_graph():
    """Returns a graph that contains nodes that "intervene" in many possible
    chains. Looks something like:

       4
      ^
     /
    0 -> 1 -> 2 -> 3
             ^
            /
           5
    """
    g = nx.MultiDiGraph()
    g.add_edge(0, 1)
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(0, 4)
    g.add_edge(5, 2)
    return g


def test_easiest_possible_case():
    """Tests case where the chain is 0 -> 1 -> 2, and the "starting node" used
    is 0.
    """
    g = get_test_path_graph(3)
    results = validators.is_valid_chain(g, 0)

    assert results
    assert results.nodes == [0, 1, 2]
    assert results.starting_node == 0
    assert results.ending_node == 2


def test_backwards_extension():
    """Tests case where the chain is 0 -> 1 -> 2, and the "starting node" used
    is 1. In this case, a chain will be detected of 1 -> 2, and -- to verify
    that this chain is "maximally" large -- the chain should be extended
    back up. This should result in a chain being detected that covers the
    full path graph.
    """
    g = get_test_path_graph(3)
    results = validators.is_valid_chain(g, 1)

    assert results
    assert results.nodes == [0, 1, 2]
    assert results.starting_node == 0
    assert results.ending_node == 2


def test_easy_no_chain():
    """Tests 0 -> 1 -> 2 case starting at 2. No chain will be found here to
    start off with, so the code won't bother doing the backwards extension
    stuff.
    """
    g = get_test_path_graph(3)
    results = validators.is_valid_chain(g, 2)

    assert not results
    assert results.nodes == []
    assert results.starting_node is None
    assert results.ending_node is None


def test_intervening_paths_harder():
    """Test that checks what chains are found in the "intervening graph."

    Only 2 -> 3 should be detected -- everything else isn't possible due to
    the "intervening" nodes/edges (also, sidenote, writing out "intervening"
    like 5 times here has made it not look like a word at all).
    """
    g = get_intervening_graph()
    # Only one chain can be detected in this graph: 2 -> 3
    # ... So starting at everything except for 2 should result in nothing found
    for i in [0, 1, 3, 4, 5]:
        results = validators.is_valid_chain(g, i)
        assert not results

    # Check that 2 -> 3 is indeed recognized as a chain
    results = validators.is_valid_chain(g, 2)
    assert results
    assert results.nodes == [2, 3]


def test_intervening_paths_easier():
    """Removes an edge in the "intervening graph" and checks that
    the chain detection's behavior adapts accordingly.

    After this modification, the graph should look like:

       4
      ^
     /
    0 -> 1 -> 2 -> 3

    ... so we should find one chain in this graph, 1 -> 2 -> 3.
    """
    g = get_intervening_graph()
    # Try lopping off the 5 -> 2 edge
    g.remove_edge(5, 2)

    # Now, 1 -> 2 -> 3 should be a valid chain
    # Due to backwards extension, we should be able to start in either 1 or 2
    # and detect the same chain (note the (1, 3) range -- the endpoint, 3, is
    # excluded and therefore not checked)
    for i in range(1, 3):
        results = validators.is_valid_chain(g, i)
        assert results
        assert results.nodes == [1, 2, 3]
        assert results.starting_node == 1
        assert results.ending_node == 3

    # Of course, the other nodes in the graph won't result in chains being
    # detected (3 and 4 have no outgoing nodes, 5 is an "island", 0 has an
    # intervening outgoing edge to 4)
    assert not validators.is_valid_chain(g, 0)
    assert not validators.is_valid_chain(g, 3)
    assert not validators.is_valid_chain(g, 4)
    assert not validators.is_valid_chain(g, 5)


def test_cyclic_chain_easy():
    """Checks that the following graph isn't considered a chain:

         __
        /  \
       V    \
       1 --> 2

       It should get tagged as a cyclic chain later on.
    """
    g = nx.MultiDiGraph()
    g.add_edge(1, 2)
    g.add_edge(2, 1)
    # Regardless of picked starting node, this shouldn't work
    for s in [1, 2]:
        assert not validators.is_valid_chain(g, s)


def test_cyclic_chain_ambiguous_end():
    """Checks that the following graph isn't considered a chain:

         __
        /  \
       V    \
       1 --> 2 --> 3

       Note the "3" at the end. This test should make sure that the code
       can identify (even in the case where it initially finds a chain starting
       at node 1) that this putatively-ok chain is actually a cyclic chain.
    """
    g = nx.MultiDiGraph()
    g.add_edge(1, 2)
    g.add_edge(2, 1)
    g.add_edge(2, 3)
    # Regardless of picked starting node, this shouldn't work
    for s in [1, 2, 3]:
        assert not validators.is_valid_chain(g, s)


def test_cyclic_chain_found_to_be_cyclic_during_backwards_extension():
    """Function name is probably self-explanatory. This looks at this graph:

         ________
        /        \
       V          \
       1 --> 2 --> 3 --> 4

       If we look for a chain starting at "2", then we'll see that 2 -> 3 seems
       to be a valid chain (none of 3's outgoing edges hit 2 or 3). However,
       when we try to do backwards extension (finding a more "optimal" starting
       node for the chain than 2), we should hit 1 and then 3, and this should
       cause the code to realize that the pattern here is really a cyclic
       chain.

       Fun fact: I'm pretty sure this sort of case was treated as a "chain" by
       MetagenomeScope's pattern detection code before. Adding this test
       actually made me realize this bug existed!
    """
    g = nx.MultiDiGraph()
    g.add_edge(1, 2)
    g.add_edge(2, 3)
    g.add_edge(3, 1)
    g.add_edge(3, 4)
    # Regardless of picked starting node, this shouldn't work
    for s in [1, 2, 3, 4]:
        assert not validators.is_valid_chain(g, s)
