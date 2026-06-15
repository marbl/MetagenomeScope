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
import pytest
from metagenomescope import ui_config
from metagenomescope.layout import Layout, layout_config
from metagenomescope.errors import WeirdError
from . import utils


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
    ag, cc, n1, n2, n3 = utils.get_cycle_with_tip_data()
    lay = Layout(
        cc,
        [ui_config.SHOW_PATTERNS],
        [],
        ui_config.LAYOUT_DOT,
        {ui_config.LAYOUT_DOT: {"ranksep": 3}},
    )
    utils.check_layout_cycle_with_tip(ag, lay, n1, n2, n3)


def test_layout_bad_algorithm():
    _, cc, _, _, _ = utils.get_cycle_with_tip_data()
    with pytest.raises(WeirdError) as ei:
        Layout(cc, [ui_config.SHOW_PATTERNS], [], "badalg", {})
    assert str(ei.value) == "badalg not mapped to a Graphviz program?"

    # even "recognized" algorithms that don't refer to graphviz progs
    # should still trigger an error if you call Layout() with them directly
    with pytest.raises(WeirdError) as ei:
        Layout(cc, [ui_config.SHOW_PATTERNS], [], ui_config.LAYOUT_DAGRE, {})
    assert (
        str(ei.value)
        == f"{ui_config.LAYOUT_DAGRE} not mapped to a Graphviz program?"
    )


def test_layout_to_solid_dot():
    # this example is a bit silly since we won't really call .to_solid_dot()
    # on a layout outside of the context of the recursive layout procedure.
    # but let's do it anyway just to test this without the added complexity of
    # the recursive stuff at this point
    ag, cc, n1, n2, n3 = utils.get_cycle_with_tip_data()
    lay = Layout(
        cc,
        [ui_config.SHOW_PATTERNS],
        [],
        ui_config.LAYOUT_DOT,
        {ui_config.LAYOUT_DOT: {"ranksep": 3}},
    )
    w = lay.width / layout_config.POINTS_PER_INCH
    h = lay.height / layout_config.POINTS_PER_INCH
    assert lay.to_solid_dot() == (
        f"  {cc.unique_id} [width={w},height={h},shape=rectangle,"
        f'label="cc{cc.cc_num}_id{cc.unique_id}"];\n'
    )
