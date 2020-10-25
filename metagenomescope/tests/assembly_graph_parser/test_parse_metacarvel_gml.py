from networkx import NetworkXError
from .utils import run_tempfile_test
from metagenomescope.assembly_graph_parser import parse_metacarvel_gml


def test_parse_metacarvel_gml_good():
    """Tests that MetaCarvel GMLs are parsed correctly, using the MaryGold
    fig. 2a graph as an example.

    The bulk of work in GML parsing is done using NetworkX's read_gml()
    function, so we don't test this super thoroughly. Mostly, we just verify
    that all of the graph attributes are being read correctly here.

    A pleasant thing about this graph is that one of the nodes (NODE_3) has a
    different orientation than the others. This slight difference lends itself
    well to writing mostly-simple tests that can still check to make sure
    details are being processed as expected.
    """
    digraph = parse_metacarvel_gml(
        "metagenomescope/tests/input/marygold_fig2a.gml"
    )
    # Make sure that the appropriate amounts of nodes and edges are read
    assert len(digraph.nodes) == 12
    assert len(digraph.edges) == 16
    for i in range(1, 13):
        label = "NODE_{}".format(i)
        if i == 3:
            assert digraph.nodes[label]["orientation"] == "-"
        else:
            assert digraph.nodes[label]["orientation"] == "+"
        assert digraph.nodes[label]["length"] == "100"
        assert "id" not in digraph.nodes[label]
        assert "label" not in digraph.nodes[label]
    for e in digraph.edges:
        if e == ("NODE_3", "NODE_5"):
            assert digraph.edges[e]["orientation"] == "BB"
        elif e == ("NODE_1", "NODE_3"):
            assert digraph.edges[e]["orientation"] == "EE"
        else:
            assert digraph.edges[e]["orientation"] == "EB"
        assert digraph.edges[e]["mean"] == "-200.00"
        assert digraph.edges[e]["stdev"] == 25.1234
        assert digraph.edges[e]["bsize"] == 30


def get_marygold_gml():
    with open("metagenomescope/tests/input/marygold_fig2a.gml", "r") as mg:
        return mg.readlines()


def test_parse_metacarvel_gml_no_labels():
    """Tests parsing GMLs where a node doesn't have a label.

    NX should raise an error automatically in this case.
    """
    mg = get_marygold_gml()
    # Remove the fifth line (the one that defines a label for node 10)
    mg.pop(4)
    run_tempfile_test(
        "gml", mg, NetworkXError, "no 'label' attribute", join_char=""
    )
    # Remove another label attribute, this time for node 6
    # (This label decl. is on line 17, and we use an index of 15 here due to
    # 0-indexing and then due to line 5 already being removed)
    mg.pop(15)
    run_tempfile_test(
        "gml", mg, NetworkXError, "no 'label' attribute", join_char=""
    )


def test_parse_metacarvel_gml_no_ids():
    """Tests parsing GMLs where a node doesn't have an ID.

    NX should raise an error automatically in this case.
    """
    mg = get_marygold_gml()
    # Remove the fourth line (the one that defines an ID for node 10)
    mg.pop(3)
    run_tempfile_test(
        "gml", mg, NetworkXError, "no 'id' attribute", join_char=""
    )
    # Remove another ID attribute, this time for node 1
    mg.pop(8)
    run_tempfile_test(
        "gml", mg, NetworkXError, "no 'id' attribute", join_char=""
    )


def test_parse_metacarvel_gml_insufficient_node_metadata():
    """Tests parsing GMLs where nodes don't have orientation and/or length."""
    mg = get_marygold_gml()
    # Remove orientation from node 10
    mg.pop(5)
    exp_msg = 'Only 11 / 12 nodes have "orientation" given.'
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")
    # Remove length from node 10 (it's the line after the previous line we
    # removed)
    mg.pop(5)
    # due to "precedence" (just the order of iteration in the for loops), we
    # expect orientation to take priority over length in these error messages
    # -- but this doesn't really matter
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")

    # Restore mg
    mg = get_marygold_gml()
    # Now, just remove the length line. We should see an error message about
    # length, not orientation, now.
    mg.pop(6)
    exp_msg = 'Only 11 / 12 nodes have "length" given.'
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")
    # For fun, let's remove all of the lines with length and make sure this
    # updates the error msg accordingly
    mg = [line for line in mg if "length" not in line]
    exp_msg = 'Only 0 / 12 nodes have "length" given.'
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")

    # ... And let's try that same thing with orientation, which as we've
    # established takes priority in error messages (again, doesn't actually
    # matter, but we might as well test that this behavior remains consistent)
    mg = [line for line in mg if "orientation" not in line]
    exp_msg = 'Only 0 / 12 nodes have "orientation" given.'
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")


def test_parse_metacarvel_gml_insufficient_edge_metadata():
    """Tests parsing GMLs where nodes don't have orientation and/or length."""
    mg = get_marygold_gml()
    # Remove orientation from edge 8 -> 9 (line 190 in the file)
    mg.pop(189)
    exp_msg = 'Only 15 / 16 edges have "orientation" given.'
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")
    # Remove orientation from all edges in the file
    mg = [
        line
        for line in mg
        if 'orientation "E' not in line and 'orientation "B' not in line
    ]
    exp_msg = 'Only 0 / 16 edges have "orientation" given.'
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")

    # Restore mg
    mg = get_marygold_gml()
    # Remove mean from edge 12 -> 8
    mg.pop(182)
    exp_msg = 'Only 15 / 16 edges have "mean" given.'
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")
    # Also remove mean from edge 8 -> 9
    # This is actually line 191 of the file, but remember 0-indexing + already
    # popped one line above in the file
    mg.pop(189)
    exp_msg = 'Only 14 / 16 edges have "mean" given.'
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")

    # Restore mg
    mg = get_marygold_gml()
    # Remove bsize from edge 7 -> 12
    mg.pop(168)
    exp_msg = 'Only 15 / 16 edges have "bsize" given.'
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")

    # Remove stdev from edge 7 -> 9
    # Note that we haven't restored mg from above yet! This tests the whole
    # precedence thing mentioned in the ...insufficient_node_metadata() test
    # above (orientation, mean, stdev, bsize is the order of attributes
    # checked) -- I don't care too much about that, but this at least gives us
    # some confidence that multiple things can be missing without completely
    # breaking this function.
    mg.pop(174)
    exp_msg = 'Only 15 / 16 edges have "stdev" given.'
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")

    # Remove bsize from *all* lines -- stdev error should still show up
    mg = [line for line in mg if "bsize" not in line]
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")


def test_parse_metacarvel_gml_undirected_graph():
    """Tests parsing a GML that isn't directed."""
    mg = get_marygold_gml()
    exp_msg = "The input graph should be directed."

    # Try two things: 1) the choice of directed/undirected isn't specified
    # (defaults to undirected), 2) explicitly specified as not directed
    mg.pop(1)
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")

    mg.insert(1, "  directed 0\n")
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")


def test_parse_metacarvel_gml_duplicate_edges():
    """Tests parsing GMLs with duplicate edges, which are disallowed in
    MetagenomeScope.
    """
    mg = get_marygold_gml()
    # Remove the last line in the file (only contains a ] character, and closes
    # the graph definition)
    mg.pop()
    # ...And insert in another definition for edge 12 -> 8
    mg.append(" edge [\n")
    mg.append("  source 12\n")
    mg.append("  target 8\n")
    mg.append('  orientation "EB"\n')
    mg.append('  mean "-200.00"\n')
    mg.append("  stdev 25.1234\n")
    mg.append("  bsize 30\n")
    mg.append(" ]\n")
    mg.append("]")

    run_tempfile_test(
        "gml", mg, NetworkXError, "(12->8) is duplicated", join_char=""
    )

    # NetworkX should have just failed when trying to read this GML file, since
    # it includes a duplicate edge and is a multigraph. Cool!
    # Now, let's be antagonistic and turn this graph into a multigraph, in an
    # attempt to get NetworkX to let this slide.
    mg.insert(1, "  multigraph 1\n")

    # This time around, parse_metacarvel_gml() should raise an error: it'll
    # detect that the input graph is a multigraph and be all like "nuh uh
    # you didn't get that from MetaCarvel, now did you" (something like that)
    run_tempfile_test(
        "gml", mg, ValueError, "Multigraphs are unsupported", join_char=""
    )


def test_parse_metacarvel_gml_duplicate_nodes():
    """Tests parsing a GML with duplicate nodes, which is disallowed in both
    MetagenomeScope and NetworkX.
    """
    # CASE 1: just insert a repeated node definition, and make sure NX doesn't
    # parse it
    mg = get_marygold_gml()
    # Remove the last line in the file
    mg.pop()
    # ...And insert in another definition for node 1

    mg.append("  node [\n")
    mg.append("   id 1\n")
    mg.append('   label "NODE_1"\n')
    mg.append('   orientation "FOW"\n')
    mg.append('   length "100"\n')
    mg.append("  ]\n")
    mg.append("]")

    run_tempfile_test(
        "gml", mg, NetworkXError, "node id 1 is duplicated", join_char=""
    )

    # CASE 2: since that failed because of the node ID being duplicated, try
    # using a new ID but the same label as an extant node
    mg = get_marygold_gml()
    # Remove the last line in the file
    mg.pop()
    # ...And insert in another definition for node 1

    mg.append("  node [\n")
    mg.append("   id 100\n")
    mg.append('   label "NODE_1"\n')
    mg.append('   orientation "FOW"\n')
    mg.append('   length "100"\n')
    mg.append("  ]\n")
    mg.append("]")

    run_tempfile_test(
        "gml",
        mg,
        NetworkXError,
        "node label 'NODE_1' is duplicated",
        join_char="",
    )

    # Cool, so now we know that NX disallows duplicate IDs and duplicate
    # labels.
    # You could say "well, what if you add in a node with a different ID *and*
    # a different label?"
    # ...But that would just mean that you added in a completely new node! And
    # that's cool. So we're done here :)


def test_parse_metacarvel_gml_invalid_node_metadata():
    """Tests GMLs where node metadata is provided, but is somehow incorrect."""

    # Test invalid orientations
    ors = ['"HIMOM"', "1", '"EB"', '"BB"', '"BE"', '"EE"', '"ABC"']
    for o in ors:
        mg = get_marygold_gml()
        mg.pop(5)
        mg.insert(5, "   orientation {}\n".format(o))
        # p is just the thing we expect in the error message, without any
        # double-quotes. We have to account for quotes here in order to be able
        # to test both numbers (e.g. 1) and strings (e.g. "FOW"). (NX gets
        # angry if you put a string like FOW outside of quotes in a GML file.)
        p = "".join([c for c in o if c != '"'])
        exp_msg = 'Node NODE_10 has unsupported orientation "{}".'.format(p)
        run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")

    # Test invalid lengths
    lengths = [
        "100.0",
        "0",
        "ABC",
        "-1",
        "-1.0",
        "-100",
        "2a",
        "0x123",
        "01.2",
    ]
    for length_to_test in lengths:
        mg = get_marygold_gml()
        mg.pop(6)
        mg.insert(6, '   length "{}"\n'.format(length_to_test))
        exp_msg = 'Node NODE_10 has non-positive-integer length "{}".'.format(
            length_to_test
        )
        run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")


def test_parse_metacarvel_gml_invalid_edge_metadata():
    """Tests GMLs where edge metadata is provided, but is somehow incorrect."""

    # 1. Test orientation
    for val in (
        '"FOW"',
        '"REV"',
        '"ABC"',
        "3.2",
        "3",
        "2",
        "1",
        "0",
        "-1",
        '"NaN"',
        '"inf"',
    ):
        mg = get_marygold_gml()
        mg.pop(189)
        mg.insert(189, "   orientation {}\n".format(val))
        # Remove double-quotes from val when checking the error message
        # (since *everything* will get encased in one layer double-quotes,
        # including the stuff that already has double-quotes like "FOW")
        # (See test_parse_metacarvel_gml_invalid_node_metadata() above)
        p = "".join([c for c in val if c != '"'])
        exp_msg = 'has unsupported orientation "{}".'.format(p)
        run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")

    mg.pop(189)
    mg.insert(189, '   orientation "REV"\n')
    exp_msg = 'has unsupported orientation "REV".'
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")

    # Restoring the orientation to something normal (say, BB) should work
    mg.pop(189)
    mg.insert(189, '   orientation "BB"\n')
    run_tempfile_test("gml", mg, None, None, join_char="")

    # 2. Test various disallowed bsize values
    vals = (
        "6.2",
        "0.0",
        "0",
        "1.2",
        "1.0",
        "-1",
        "-2",
        '"nan"',
        '"inf"',
        '"-inf"',
        '"NaN"',
    )
    for val in vals:
        mg = get_marygold_gml()
        mg.pop(192)
        mg.insert(192, "   bsize {}\n".format(val))
        p = "".join([c for c in val if c != '"'])
        exp_msg = 'has non-positive-integer bsize "{}".'.format(p)
        run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")

    # 3. Test mean
    mg = get_marygold_gml()
    mg.pop(198)
    mg.insert(198, '   mean "ABC"\n')
    exp_msg = 'has non-numeric mean "ABC".'
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")

    # 4. Test stdev
    mg = get_marygold_gml()
    mg.pop(199)
    mg.insert(199, '   stdev "ABC"\n')
    exp_msg = 'has non-numeric stdev "ABC".'
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")
    # TODO test bsize, mean, stdev more thoroughly

    # Test that NaN/infinity/zero/negative values work ok (but only with
    # mean/stdev; not with bsize)
    vals = (
        "nan",
        "NaN",
        "inf",
        "-inf",
        "Infinity",
        "-Infinity",
        "0",
        "0.0",
        "-1.0",
    )
    for val in vals:
        for field, line_num in (("mean", 198), ("stdev", 199)):
            mg = get_marygold_gml()
            mg.pop(line_num)
            mg.insert(line_num, '   {} "{}"\n'.format(field, val))
            run_tempfile_test("gml", mg, None, None, join_char="")


def test_parse_metacarvel_gml_repeated_node_labels_and_ids():
    """This and the following tests test a horrifying edge case I only
    realized *after* writing all of the above tests wherein the GML file
    specifies the same attribute twice for the same element. This produces a
    list of values: for example --

    node [
     id 10
     label "NODE_10"
     orientation "FOW"
     orientation "CC"
     length "100"
    ]

    will have the attribute dict
    {'orientation': ['FOW', 'CC'], 'length': '100'}

    Fortunately, pretty much all of the existing type validation code should
    fail against this nonsense. But we should test this.
    """
    # Test duplicate label -- this will crash networkx on trying to load the
    # graph
    mg = get_marygold_gml()
    mg.insert(5, '   label "NODE_10"\n')
    exp_msg = "unhashable type: 'list'"
    run_tempfile_test("gml", mg, TypeError, exp_msg, join_char="")

    # Test duplicate (but with different contents) label -- same error as above
    mg = get_marygold_gml()
    mg.insert(5, '   label "NODE_50"\n')
    run_tempfile_test("gml", mg, TypeError, exp_msg, join_char="")

    # Now, test duplicate ID -- same error
    mg = get_marygold_gml()
    mg.insert(5, "   id 1\n")
    run_tempfile_test("gml", mg, TypeError, exp_msg, join_char="")

    # Similarly, test duplicate but different ID
    mg = get_marygold_gml()
    mg.insert(5, "   id 100\n")
    run_tempfile_test("gml", mg, TypeError, exp_msg, join_char="")


def test_parse_metacarvel_gml_repeated_node_attrs():
    mg = get_marygold_gml()
    mg.insert(5, '   orientation "REV"\n')
    exp_msg = "Node NODE_10 has unsupported orientation \"['REV', 'FOW']\"."
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")

    mg = get_marygold_gml()
    mg.insert(5, '   length "200"\n')
    exp_msg = (
        "Node NODE_10 has non-positive-integer length \"['200', '100']\"."
    )
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")


def test_parse_metacarvel_gml_repeated_edge_attrs():
    mg = get_marygold_gml()
    mg.insert(166, '   orientation "EB"\n')
    exp_msg = (
        "Edge ('NODE_7', 'NODE_12') has unsupported orientation "
        "\"['EB', 'EB']\"."
    )
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")

    mg = get_marygold_gml()
    mg.insert(166, '   mean "123.45"\n')
    exp_msg = (
        "Edge ('NODE_7', 'NODE_12') has non-numeric mean "
        "\"['123.45', '-200.00']\"."
    )
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")

    mg = get_marygold_gml()
    mg.insert(166, '   stdev "123.45"\n')
    exp_msg = (
        "Edge ('NODE_7', 'NODE_12') has non-numeric stdev "
        "\"['123.45', 25.1234]\"."
    )
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")

    mg = get_marygold_gml()
    mg.insert(167, "   bsize 15\n")
    exp_msg = (
        "Edge ('NODE_7', 'NODE_12') has non-positive-integer bsize "
        '"[15, 30]".'
    )
    run_tempfile_test("gml", mg, ValueError, exp_msg, join_char="")


def test_parse_metacarvel_gml_repeated_edge_source_or_target():
    """If the user seriously tries to specify a source / target twice for a
    single edge, it should crash NetworkX. This test verifies that.
    """
    # 1. duplicate source
    mg = get_marygold_gml()
    mg.insert(167, "   source 8\n")
    exp_msg = "undefined source [7, 8]"
    run_tempfile_test("gml", mg, NetworkXError, exp_msg, join_char="")

    # 2. duplicate source *and* target (again, one of those "we're checking
    # this to make sure that having both things wrong doesn't somehow make a
    # right, but we really don't care about error precedence so long as at
    # least one error is reported" kinda scenarios)
    mg.insert(167, "   target 6\n")
    exp_msg = "undefined source [7, 8]"
    run_tempfile_test("gml", mg, NetworkXError, exp_msg, join_char="")

    # 3. just a duplicate target (reset the graph first)
    mg = get_marygold_gml()
    mg.insert(167, "   target 6\n")
    exp_msg = "undefined target [12, 6]"
    run_tempfile_test("gml", mg, NetworkXError, exp_msg, join_char="")
