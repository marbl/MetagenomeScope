# Copyright (C) 2016-- Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
# Authored by Marcus Fedarko
#
# This file is part of MetagenomeScope.
#
# MetagenomeScope is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MetagenomeScope is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MetagenomeScope.  If not, see <http://www.gnu.org/licenses/>.
from metagenomescope import ui_config
from metagenomescope.graph import AssemblyGraph


def get_cycle_with_tip_data():
    ag = AssemblyGraph("metagenomescope/tests/input/cycle_with_tip.gfa")

    # one component has nodes {1, 2, 3}; the other has {-3, -2, -1}.
    # we just care about the one with the positive node names here.
    assert len(ag.components) == 2
    nrccnums = ag.get_nr_cc_nums()
    assert len(nrccnums) == 1
    cc = ag.components[list(nrccnums)[0] - 1]

    # find node objects
    assert len(cc.nodes) == 3
    n1 = None
    n2 = None
    n3 = None
    for n in cc.nodes:
        assert n.name in ("1", "2", "3")
        if n.name == "1":
            n1 = n
        elif n.name == "2":
            n2 = n
        else:
            n3 = n
    assert n1 is not None
    assert n2 is not None
    assert n3 is not None

    return ag, cc, n1, n2, n3


def test_layout_cycle_with_tip_nonrecursive():
    """Tests layout on a component that looks like:

    +----+
    V    |
    1 -> 2 -> 3

    Testing what the layout looks like in terms of "is this this EXACT x
    coordinate" or something like that is a little tricky, since different dot
    versions might produce slightly different results. This is a somewhat quick
    and dirty approach, but hopefully it should not be super brittle...
    """
    ag, cc, n1, n2, n3 = get_cycle_with_tip_data()
    dr = cc.to_cyjs(
        [ui_config.SHOW_PATTERNS],
        ui_config.LAYOUT_DOT,
        {ui_config.LAYOUT_DOT: {"ranksep": 3}},
    )
    assert len(dr.region2layout) == 1
    lay = dr.region2layout[cc]
    assert lay is not None

    # internal node IDs
    i1 = n1.unique_id
    i2 = n2.unique_id
    i3 = n3.unique_id
    # we can test stuff like dimensions later, but that is all very rough now
    # so let's not bother. just verify that the nodes got put into the layout
    assert f"{i1} [width=" in lay.dot
    assert f"{i2} [width=" in lay.dot
    assert f"{i3} [width=" in lay.dot

    # IMPORTANT!!!! and actually the motivating factor for this whole test.
    # verify that the back edge detection worked, and that the back edge in
    # this cyclic chain is specially marked with constraint=false :)
    # this causes it to not impact node rankings, meaning that the end node of
    # the cyclic chain will be to the right of the start node of the cyclic
    # chain (https://github.com/marbl/MetagenomeScope/issues/368)
    # ... so that i can say in the paper that we do this, and not have to worry
    # that it has subtly become broken since i implemented it a while back ...
    assert f"{i1} -> {i2};\n" in lay.dot
    assert f'{i2} -> {i1} [constraint="false"];\n' in lay.dot
    assert f"{i2} -> {i3};\n" in lay.dot

    # consider node positions. Because we use rankdir=LR by default,
    # we should see 1, 2, and 3 occur from left to right. (And the 2 -> 1
    # back edge should have been marked with constraint=false, so we shouldn't
    # see something like
    #
    # +----+
    # V    |
    # 2 -> 1
    #  \
    #   \> 3
    #
    # because this would mean that 2 -> 1 would have actually impacted the
    # node ranking.)
    assert len(lay.nodeid2rel) == 3
    assert n1.unique_id in lay.nodeid2rel
    assert n2.unique_id in lay.nodeid2rel
    assert n3.unique_id in lay.nodeid2rel
    x1, y1 = lay.nodeid2rel[n1.unique_id]
    x2, y2 = lay.nodeid2rel[n2.unique_id]
    x3, y3 = lay.nodeid2rel[n3.unique_id]
    assert x1 < x2
    assert x2 < x3

    # verify that the only edges described in the edge relative coords from
    # the layout are those three edges in this component
    edges_seen_by_st = []
    assert len(lay.edgeid2rel) == 3
    for eid in lay.edgeid2rel:
        assert eid in ag.edgeid2obj
        eobj = ag.edgeid2obj[eid]
        edges_seen_by_st.append((eobj.new_src_id, eobj.new_tgt_id))
    assert len(edges_seen_by_st) == len(set(edges_seen_by_st))
    assert set(edges_seen_by_st) == set([(i1, i2), (i2, i1), (i2, i3)])

    # check stuff seems to fit within layout boundaries that are defined by
    # the layout's width and height attrs.
    #
    # i don't know exactly if stuff can be exactly on the boundary or whatever
    # (shouldn't really matter) so let's be conservative...
    # if this starts failing in the future that is PROBABLY okay so long as the
    # bounds are at least somewhat reasonable.

    # check node coords
    for x in (x1, x2, x3):
        assert x <= lay.width
    for y in (y1, y2, y3):
        assert y <= lay.height

    # check edge coords
    for relcoords in lay.edgeid2rel.values():
        assert len(relcoords) % 2 == 0
        for i, c in enumerate(relcoords):
            if i % 2 == 0:
                # this is an x coord
                assert c <= lay.width
            else:
                assert c <= lay.height


def test_layout_cyclic_chain_cc_non_gv_layout_alg():
    """When the layout algorithm isn't a Graphviz program, we'll do layout
    in the client side -- so the Layout object should be None."""
    _, cc, _, _, _ = get_cycle_with_tip_data()
    dr = cc.to_cyjs(
        [ui_config.SHOW_PATTERNS],
        ui_config.LAYOUT_DAGRE,
        {},
    )
    assert len(dr.region2layout) == 1
    lay = dr.region2layout[cc]
    assert lay is None
