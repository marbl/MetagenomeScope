import logging
from metagenomescope import log_utils, ui_config, config
from metagenomescope.graph import AssemblyGraph


def test_log_lines_with_sep_basic(caplog):
    caplog.set_level(logging.INFO)
    log_utils.log_lines_with_sep(["asdfghjk", "qwerty"])
    # the separator is 15 chars longer to account for the usual
    # {HH:MM:SS.mmm} prefix.
    # also, note that i'm using "".join() instead of just making
    # this into one nightmare single-line string. this makes this test clearer
    assert (
        "".join(["asdfghjk\n", "-----------------------\n", "qwerty"])
        in caplog.text
    )


def test_log_lines_with_sep_just_one_line(caplog):
    caplog.set_level(logging.INFO)
    log_utils.log_lines_with_sep(["asdfghjk"])
    assert "".join(["asdfghjk\n", "-----------------------"]) in caplog.text


def test_log_lines_with_sep_endsepline(caplog):
    caplog.set_level(logging.INFO)
    log_utils.log_lines_with_sep(["asdfghjk", "qwerty"], endsepline=True)
    assert (
        "".join(
            [
                "asdfghjk\n",
                "-----------------------\n",
                "qwerty\n" "-----------------------",
            ]
        )
        in caplog.text
    )


def test_log_layout_start_basic(caplog):
    caplog.set_level(logging.DEBUG)
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    log_utils.log_layout_start(
        {
            "requestGood": True,
            "draw_type": config.DRAW_ALL,
            "scope_settings": ["fizz", "buzz"],
            "modifier_settings": ["mod", "ifier", "yay"],
            "layout_alg": ui_config.LAYOUT_DOT,
            "layout_params": {
                ui_config.LAYOUT_DOT: {"ranksep": 333},
                ui_config.LAYOUT_SFDP: {"flumbity": 25, "glumbity": 0},
            },
        },
        ag,
    )
    assert (
        "Laying out (#1 \u2013 4) with dot (fizz; buzz; mod; ifier; yay; "
        "ranksep = 333)..."
    ) in caplog.text


def test_log_layout_start_no_layout_params(caplog):
    caplog.set_level(logging.DEBUG)
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    log_utils.log_layout_start(
        {
            "requestGood": True,
            "draw_type": config.DRAW_ALL,
            "scope_settings": ["fizz", "buzz"],
            "modifier_settings": ["mod", "ifier", "yay"],
            "layout_alg": ui_config.LAYOUT_DOT,
            "layout_params": {
                ui_config.LAYOUT_SFDP: {"flumbity": 25, "glumbity": 0},
            },
        },
        ag,
    )
    assert (
        "Laying out (#1 \u2013 4) with dot (fizz; buzz; mod; ifier; yay)..."
    ) in caplog.text


def test_log_layout_start_no_scope_modifier_settings(caplog):
    caplog.set_level(logging.DEBUG)
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    log_utils.log_layout_start(
        {
            "requestGood": True,
            "draw_type": config.DRAW_ALL,
            "scope_settings": [],
            "modifier_settings": [],
            "layout_alg": ui_config.LAYOUT_DOT,
            "layout_params": {
                ui_config.LAYOUT_DOT: {"ranksep": 333},
                ui_config.LAYOUT_SFDP: {"flumbity": 25, "glumbity": 0},
            },
        },
        ag,
    )
    assert (
        "Laying out (#1 \u2013 4) with dot (ranksep = 333)..."
    ) in caplog.text


def test_log_layout_start_no_layout_params_or_scope_modifier_settings(caplog):
    caplog.set_level(logging.DEBUG)
    ag = AssemblyGraph("metagenomescope/tests/input/sample1.gfa")
    log_utils.log_layout_start(
        {
            "requestGood": True,
            "draw_type": config.DRAW_ALL,
            "scope_settings": [],
            "modifier_settings": [],
            "layout_alg": ui_config.LAYOUT_DOT,
            "layout_params": {
                ui_config.LAYOUT_SFDP: {"flumbity": 25, "glumbity": 0},
            },
        },
        ag,
    )
    assert "Laying out (#1 \u2013 4) with dot..." in caplog.text
