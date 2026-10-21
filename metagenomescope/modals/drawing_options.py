import copy
import dash_bootstrap_components as dbc
from dash import html, dcc
from .. import ui_utils, misc_utils, ui_config, css_config


def get_layout_tab(
    node_centric,
    orientation_in_name,
    is_flye_dot,
    multiple_ccs,
    default_dot_alg_desc,
):

    JS_ALG_WARNING = html.P(
        [
            html.Span("Note:", style={"font-weight": "bold"}),
            " This layout algorithm is run within the web browser. "
            "It may struggle or take a while for large graphs.",
        ]
    )

    DAGRE_ALG_DESC = [
        html.P(
            [
                "Client-side hierarchical layout algorithm (",
                html.A(
                    "GitHub wiki",
                    href="https://github.com/dagrejs/dagre/wiki",
                    target="_blank",
                ),
                ").",
            ]
        ),
        JS_ALG_WARNING,
    ]

    FCOSE_ALG_DESC = [
        html.P(
            [
                "Client-side force-directed layout algorithm described in ",
                html.A(
                    "Balci & Dogrusoz 2021",
                    href="https://doi.org/10.1109/TVCG.2021.3095303",
                    target="_blank",
                ),
                ' ("fCoSE: A fast compound graph layout algorithm with ',
                'constraint support").',
            ]
        ),
        JS_ALG_WARNING,
    ]

    scope_options = copy.deepcopy(ui_config.SCOPE_SETTINGS_OPTIONS)
    default_scope_settings = copy.deepcopy(ui_config.DEFAULT_SCOPE_SETTINGS)

    modifier_options = copy.deepcopy(ui_config.MODIFIER_SETTINGS_OPTIONS)
    default_modifier_settings = copy.deepcopy(
        ui_config.DEFAULT_MODIFIER_SETTINGS
    )

    # Drawing only the nonredundant parts of the graph only makes sense if
    # (1) there are pairs of nodes/edges X and -X in the graph (i.e.
    # ag.orientation_in_name is True) and (2) there are multiple components.
    #
    # If this is NOT the case, then let's just turn off (and disable) the
    # "just show nonredundant ccs" option here. We COULD hide it entirely but
    # I think disabling gives a clearer user experience.
    if not (orientation_in_name and multiple_ccs):
        disable_dcc_checklist_option(scope_options, ui_config.NR_CCS)
        # Go a step further: ensure that this option is turned off entirely for
        # these kinds of graphs.
        misc_utils.safe_list_discard(default_scope_settings, ui_config.NR_CCS)

    # Similar deal for decoupling. It makes no sense for graphs where
    # orientation_in_name is false, and -- furthermore -- Flye DOT files where
    # the nodes do not have orientations mean the algorithm gets funky.
    if not (orientation_in_name and not is_flye_dot):
        disable_dcc_checklist_option(scope_options, ui_config.DECOUPLE)
        misc_utils.safe_list_discard(
            default_scope_settings, ui_config.DECOUPLE
        )

    # Finally, we don't support recursive layout when patterns are not drawn
    # and/or when decoupling is selected.
    if not ui_utils.recursive_layout_enabled(default_scope_settings):
        ui_utils.disable_dcc_checklist_option(
            modifier_options, ui_config.RECURSIVE
        )
        misc_utils.safe_list_discard(
            default_modifier_settings, ui_config.RECURSIVE
        )

    return html.Div(
        [
            html.Div(
                (
                    "These settings will take "
                    "effect when you redraw the graph."
                ),
                className="modal-topnote drawing-option-topnote",
            ),
            html.H5("What should we draw?"),
            # Eventually we can add other stuff here, e.g. "filter
            # nodes/edges with < X cov"
            #
            # I'm sticking with a standard dcc.Checklist (rather than
            # dbc.Checklist) because I don't like the default formatting
            # of their inline checklists. Even after doing some massaging
            # to make the margins better, there is still an ugly
            # unclickable region between the checkbox and label... maybe I
            # am just doing something wrong, but I think the UX of the
            # dcc.Checklist is better.
            html.Div(
                dcc.Checklist(
                    options=scope_options,
                    value=default_scope_settings,
                    id="scopeSettingsChecklist",
                ),
                className="form-check fancyChecklistInDialog",
            ),
            html.Br(),
            html.H5("How should we draw it?"),
            html.Div(
                dcc.Checklist(
                    options=modifier_options,
                    value=default_modifier_settings,
                    id="modifierSettingsChecklist",
                ),
                className="form-check fancyChecklistInDialog",
            ),
            html.Br(),
            html.H5("Layout algorithm"),
            html.Div(
                [
                    html.Div(
                        dbc.RadioItems(
                            options=[
                                {
                                    "label": html.Span(
                                        [
                                            html.I(
                                                className="bi bi-arrow-right"
                                            ),
                                            html.Span(
                                                ui_config.DOT_TEXT,
                                                className="iconlbl",
                                            ),
                                        ],
                                        id="dotAlgSpan",
                                    ),
                                    "value": ui_config.LAYOUT_DOT,
                                },
                                {
                                    "label": html.Span(
                                        [
                                            html.I(className="bi bi-snow"),
                                            html.Span(
                                                "sfdp",
                                                className="iconlbl",
                                            ),
                                        ],
                                        id="sfdpAlgSpan",
                                    ),
                                    "value": ui_config.LAYOUT_SFDP,
                                },
                                {
                                    "label": html.Span(
                                        [
                                            html.I(
                                                className="bi bi-arrow-right"
                                            ),
                                            html.Span(
                                                "Dagre",
                                                className="iconlbl",
                                            ),
                                        ],
                                        id="dagreAlgSpan",
                                    ),
                                    "value": ui_config.LAYOUT_DAGRE,
                                },
                                {
                                    "label": html.Span(
                                        [
                                            html.I(className="bi bi-snow"),
                                            html.Span(
                                                "fCoSE",
                                                className="iconlbl",
                                            ),
                                        ],
                                        id="fcoseAlgSpan",
                                    ),
                                    "value": ui_config.LAYOUT_FCOSE,
                                },
                            ],
                            value=ui_config.DEFAULT_LAYOUT_ALG,
                            className="btn-group",
                            inputClassName="btn-check",
                            labelClassName="btn btn-outline-dark layout-alg-btn",
                            labelCheckedClassName="active",
                            id="layoutAlgRadio",
                        ),
                        className="btn-opt-group",
                        style={
                            "margin-top": "0.75em",
                            "margin-bottom": "0.75em",
                        },
                    ),
                    html.Div(
                        default_dot_alg_desc,
                        id="dotAlgDesc",
                        className=css_config.ALG_DESC_CLASSES
                        + (
                            " removedEntirely"
                            if ui_config.DEFAULT_LAYOUT_ALG
                            != ui_config.LAYOUT_DOT
                            else ""
                        ),
                    ),
                    html.Div(
                        html.P(
                            [
                                "Force-directed layout algorithm described in ",
                                html.A(
                                    "Hu 2005",
                                    href="http://yifanhu.net/PUB/graph_draw_small.pdf",
                                    target="_blank",
                                ),
                                ' ("Efficient and high quality force-directed graph '
                                'drawing").',
                            ]
                        ),
                        id="sfdpAlgDesc",
                        className=css_config.ALG_DESC_CLASSES
                        + (
                            " removedEntirely"
                            if ui_config.DEFAULT_LAYOUT_ALG
                            != ui_config.LAYOUT_SFDP
                            else ""
                        ),
                    ),
                    html.Div(
                        DAGRE_ALG_DESC,
                        id="dagreAlgDesc",
                        className=css_config.ALG_DESC_CLASSES
                        + (
                            " removedEntirely"
                            if ui_config.DEFAULT_LAYOUT_ALG
                            != ui_config.LAYOUT_DAGRE
                            else ""
                        ),
                    ),
                    html.Div(
                        FCOSE_ALG_DESC,
                        id="fcoseAlgDesc",
                        className=css_config.ALG_DESC_CLASSES
                        + (
                            " removedEntirely"
                            if ui_config.DEFAULT_LAYOUT_ALG
                            != ui_config.LAYOUT_FCOSE
                            else ""
                        ),
                    ),
                ],
                style={"text-align": "center"},
            ),
            html.Br(),
            html.H5("Layout parameters"),
            html.Div(
                [
                    dbc.InputGroup(
                        [
                            dbc.InputGroupText(
                                html.Span(
                                    [
                                        html.A(
                                            "Rank separation",
                                            href="https://graphviz.org/docs/attrs/ranksep/",
                                            target="_blank",
                                        ),
                                        " (",
                                        ui_config.DOT_TEXT,
                                        " only)",
                                    ],
                                ),
                            ),
                            dbc.Input(
                                type="text",
                                id="dotRanksep",
                                value=ui_config.NODECENTRIC_2_DEFAULT_DOT_RANKSEP[
                                    node_centric
                                ],
                                className="short-num-input",
                            ),
                        ],
                        size="sm",
                    ),
                    ui_config.OPTIONS_SEP,
                    dbc.InputGroup(
                        [
                            dbc.InputGroupText(
                                html.Span(
                                    [
                                        html.Span(
                                            "K",
                                            style={"font-style": "italic"},
                                        ),
                                        " (",
                                        html.A(
                                            "spring constant",
                                            href="https://graphviz.org/docs/attrs/K/",
                                            target="_blank",
                                        ),
                                        ", sfdp only)",
                                    ],
                                ),
                            ),
                            dbc.Input(
                                type="text",
                                id="sfdpK",
                                value=0.3,
                                className="short-num-input",
                            ),
                        ],
                        size="sm",
                    ),
                    ui_config.OPTIONS_SEP,
                    dbc.InputGroup(
                        [
                            dbc.InputGroupText(
                                html.Span(
                                    [
                                        html.A(
                                            "Overlap scaling factor",
                                            href="https://graphviz.org/docs/attrs/overlap_scaling/",
                                            target="_blank",
                                        ),
                                        " (sfdp only)",
                                    ],
                                ),
                            ),
                            dbc.Input(
                                type="text",
                                id="sfdpOverlapScaling",
                                value=-10,
                                className="short-num-input",
                            ),
                        ],
                        size="sm",
                    ),
                ],
                style={
                    "margin-top": "0.75em",
                },
            ),
        ],
    )


def get_style_tab(node_centric):
    return html.Div(
        [
            html.Div(
                [
                    'Click "',
                    html.Span(
                        "Apply",
                        className="text-success",
                    ),
                    '" to make these settings take effect.',
                ],
                className="modal-topnote drawing-option-topnote",
            ),
            html.H5("When a node is selected..."),
            html.Div(
                dcc.Checklist(
                    options=[
                        {
                            "label": "Darken it",
                            "value": ui_config.SELECTED_NODE_DARKEN,
                        },
                        {
                            "label": "Show a border around it",
                            "value": ui_config.SELECTED_NODE_BORDER,
                        },
                        {
                            "label": "Color it red",
                            "value": ui_config.SELECTED_NODE_COLOR,
                        },
                    ],
                    value=ui_config.DEFAULT_SELECTED_NODE_SETTINGS,
                    id="selectedNodeSettingsChecklist",
                ),
                className="form-check fancyChecklistInDialog",
            ),
            html.Br(),
            html.H5("How thick should edges be?"),
            html.P("(These values are given in pixels.)"),
            html.H6("Real edges"),
            dbc.InputGroup(
                [
                    dbc.InputGroupText(html.Span("Default")),
                    dbc.Input(
                        type="text",
                        id="realDefaultEdgeWidth",
                        value=ui_config.NODECENTRIC_2_REAL_DEFAULT_EDGEWIDTH[
                            node_centric
                        ],
                        className="short-num-input",
                    ),
                    dbc.InputGroupText(html.Span("Selected")),
                    dbc.Input(
                        type="text",
                        id="realSelectedEdgeWidth",
                        value=ui_config.NODECENTRIC_2_REAL_SELECTED_EDGEWIDTH[
                            node_centric
                        ],
                        className="short-num-input",
                    ),
                ],
                size="sm",
                style={"margin-bottom": "1em"},
            ),
            html.H6("Fake edges"),
            dbc.InputGroup(
                [
                    dbc.InputGroupText(html.Span("Default")),
                    dbc.Input(
                        type="text",
                        id="fakeDefaultEdgeWidth",
                        value=ui_config.NODECENTRIC_2_FAKE_DEFAULT_EDGEWIDTH[
                            node_centric
                        ],
                        className="short-num-input",
                    ),
                    dbc.InputGroupText(html.Span("Selected")),
                    dbc.Input(
                        type="text",
                        id="fakeSelectedEdgeWidth",
                        value=ui_config.NODECENTRIC_2_FAKE_SELECTED_EDGEWIDTH[
                            node_centric
                        ],
                        className="short-num-input",
                    ),
                ],
                size="sm",
            ),
            html.Div(
                html.Button(
                    [
                        html.I(className="bi bi-pen-fill"),
                        html.Span(
                            "Apply",
                            className="iconlbl",
                        ),
                    ],
                    id="applyStyleOptionsButton",
                    className="btn btn-success",
                    type="button",
                ),
                style={"text-align": "right", "margin-top": "1em"},
            ),
        ]
    )
