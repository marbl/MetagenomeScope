# These tests check what happens when an input graph has reserved attributes in
# its nodes / edges. We (currently) store all node/edge data as dicts in a
# NetworkX graph -- which is fine, but it means that "real" things like node
# length, edge multiplicity, etc. have to exist alongside "internal" things
# like node height, edge control point data, etc. To alleviate this problem, we
# just preemptively disallow input graphs from containing any of these internal
# fields as attributes. IDEALLY we'd refactor things so that "real" data fields
# can be named anything, but ... that's gonna be a lot of work and if I
# refactor this codebase one more time I think my brain is going to leap out of
# my head and punch me in the face.
from metagenomescope.graph import AssemblyGraph


def test_check_attrs_node():
    # Shouldn't fail with an error
    AssemblyGraph("metagenomescope/tests/input/check_attrs_test_node.gml")


def test_check_attrs_edge():
    # Shouldn't fail with an error
    AssemblyGraph("metagenomescope/tests/input/check_attrs_test_edge.gml")
