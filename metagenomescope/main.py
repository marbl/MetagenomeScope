#!/usr/bin/env python3

import logging
import dash_cytoscape as cyto
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import plotly.graph_objects as go
from dash import (
    Dash,
    html,
    callback,
    clientside_callback,
    ctx,
    dcc,
    Input,
    Output,
    State,
)
from . import (
    defaults,
    css_config,
    cy_config,
    ui_config,
    config,
    ui_utils,
    cy_utils,
    color_utils,
    path_utils,
)
from .log_utils import start_log, log_lines_with_sep
from .graph import AssemblyGraph, graph_utils
from .errors import UIError

# Needed for layout extensions like dagre. And for exporting SVG images, per
# https://dash.plotly.com/cytoscape/images.
cyto.load_extra_layouts()


def run(
    graph: str = None,
    agp: str = None,
    port: int = defaults.PORT,
    verbose: bool = defaults.VERBOSE,
    debug: bool = defaults.DEBUG,
):
    """Reads the graph and starts a Dash app for visualizing it.

    Parameters
    ----------
    graph: str
        Path to the assembly graph to be visualized.

    port: int
        Port number to run the server on. We'll just pass this to Dash.

    verbose: bool
        If True, include DEBUG messages in the log output.

    debug: bool
        If True, run Dash in debug mode. See https://dash.plotly.com/devtools.
        (This is very useful for development since it supports hot reloading
        and other nice features, but for just ordinary use this should be
        turned off -- using debug mode will require processing the graph
        twice on startup.)

    Returns
    -------
    None
    """
    start_log(verbose)
    logger = logging.getLogger(__name__)
    log_lines_with_sep(
        [
            "Settings:",
            f"Graph: {graph}",
            f"AGP file: {agp}",
            f"Port: {port}",
            f"Verbose?: {verbose}",
            f"Debug mode?: {debug}",
        ],
        logger.info,
        endsepline=True,
    )

    # Read the assembly graph file and create an object representing it.
    # Creating the AssemblyGraph object will identify patterns, scale nodes and
    # edges, etc.
    ag = AssemblyGraph(graph, agp_fp=agp)

    # Prepare some of the UI components in advance. A nice thing about Dash
    # (which I guess comes from it being built on top of React) is that we can
    # define these kinds of components and reuse them without having to rewrite
    # a bunch of code.
    ctrl_sep = html.Div(
        style={
            "width": "100%",
            "height": css_config.CONTROLS_BORDER_THICKNESS,
            "background-color": css_config.CONTROLS_BORDER_COLOR,
            "margin": "1.25em 0",
        },
        className="ctrlSep",
    )

    ctrl_sep_invis = html.Div(
        style={
            "width": "100%",
            "height": "0",
            "background-color": css_config.CONTROLS_BORDER_COLOR,
            "margin": "0.7em 0",
        },
        className="ctrlSep",
    )

    colorful_random_text = html.Span(
        [
            html.Span(
                "R",
                style={"color": "#e00"},
            ),
            html.Span(
                "a",
                style={"color": "#e70"},
            ),
            html.Span(
                "n",
                style={"color": "#aa8822"},
            ),
            html.Span(
                "d",
                style={"color": "#22aa11"},
            ),
            html.Span(
                "o",
                style={"color": "#0bf"},
            ),
            html.Span(
                "m",
                style={"color": "#d3d"},
            ),
        ]
    )

    # If there are multiple components, show a "Components" tab in the info
    # dialog with information about these components. Also show various options
    # for selecting which component(s) to draw.
    #
    # This is all useless and confusing if the graph only has one component, so
    # this flag lets us figure out if we should show or hide this kinda stuff
    multiple_ccs = len(ag.components) > 1

    # Options for drawing components
    # If there is only one cc in the graph, we'll disable the "one component"
    # options. We'll make the "all components" option the default, and rename
    # it to be clearer. (Um, we could also change its icon from an asterisk to
    # something else if desired, but I actually think keeping the asterisk
    # makes sense. This way people don't worry that they are somehow seeing
    # "less" of the graph than they would otherwise. Like this is still the
    # "draw everything" option, if that makes sense.)
    cc_selection_options = {
        "ccDrawingSizeRank": [
            html.I(className="bi bi-hash"),
            html.Span("Component(s), by size rank"),
        ],
        "ccDrawingNodeNames": [
            html.I(className="bi bi-search"),
            html.Span(
                "Component(s), by node name",
            ),
        ],
        "ccDrawingAll": [
            html.I(className="bi bi-asterisk"),
            html.Span(
                (
                    "All components"
                    if multiple_ccs
                    else "Only component in the graph"
                ),
            ),
        ],
    }
    DEFAULT_CC_SELECTION_METHOD = (
        "ccDrawingSizeRank" if multiple_ccs else "ccDrawingAll"
    )
    CC_SELECTION_A_CLASSES_MULTIPLE_CCS = "dropdown-item"
    CC_SELECTION_A_ATTRS_MULTIPLE_CCS = {}
    if not multiple_ccs:
        # https://getbootstrap.com/docs/5.3/components/dropdowns/#disabled
        # thankfully this seems to prevent dash from noticing click events on
        # the disabled <a>s in question :)
        CC_SELECTION_A_CLASSES_MULTIPLE_CCS += " disabled"
        CC_SELECTION_A_ATTRS_MULTIPLE_CCS = {"aria-disabled": "true"}

    # If the user specified paths somehow (e.g. an AGP file), we'll show an
    # interface for these
    paths_given = len(ag.paths) > 0
    path_html = []
    if paths_given:
        ct_col = f"# {'nodes' if ag.node_centric else 'edges'}"
        path_html = [
            ctrl_sep,
            html.H4("Paths"),
            html.Div(
                [
                    html.Div(
                        [
                            "Available",
                            dbc.Badge(
                                path_utils.get_available_count_text(
                                    0, len(ag.paths)
                                ),
                                pill=True,
                                className=css_config.BADGE_CLASSES,
                                color=css_config.BADGE_ZERO_COLOR,
                                id="pathCount",
                            ),
                            html.Span(
                                html.I(
                                    className="bi bi-caret-right-fill",
                                    id="pathOpener",
                                ),
                                className="opener",
                            ),
                        ],
                        className="eleTableHeader",
                        id="pathHeader",
                    ),
                    dag.AgGrid(
                        rowData=[],
                        columnDefs=[
                            {
                                "field": ui_config.PATH_TBL_NAME_COL,
                                "headerName": "Name",
                                "cellClass": "path-table-name path-table-cells",
                                # i don't think we really need to explictly set
                                # this but let's be careful
                                "cellDataType": "text",
                            },
                            {
                                "field": ui_config.PATH_TBL_COUNT_COL,
                                "headerName": ct_col,
                                "cellClass": "path-table-cells",
                                # Mark that this column will contain numbers;
                                # this ensures that sorting works correctly
                                # (i.e. that "101" > "11").
                                "cellDataType": "number",
                            },
                        ],
                        # https://dash.plotly.com/dash-ag-grid/column-sizing
                        columnSize="responsiveSizeToFit",
                        className="ag-theme-balham-dark fancytable removedEntirely",
                        id="pathList",
                        # Needed to replace the default "No Rows To Show"
                        # message when no paths are available:
                        # https://community.plotly.com/t/how-to-customize-overlay-messages-in-dash-ag-grid/73932/2
                        dashGridOptions={
                            "overlayNoRowsTemplate": "No available paths.",
                        },
                        dangerously_allow_code=True,
                    ),
                ],
                className="noPadding",
            ),
        ]

    # update_title=None prevents Dash's default "Updating..." page title change
    app = Dash(__name__, title="MgSc", update_title=None)
    CONTROLS_TOGGLER_ICON_CLASSES = "bi bi-list"
    app.layout = dbc.Container(
        [
            # controls toggler (hamburger button)
            html.Div(
                html.I(
                    id="controlsTogglerIcon",
                    className=CONTROLS_TOGGLER_ICON_CLASSES,
                ),
                id="controlsToggler",
            ),
            # controls
            html.Div(
                # inner div containing everything. We structure things
                # this way so that the scrollbar is shown outside, i.e.
                # to the right of, the inner div's border -- if you just
                # put a border and a scrollbar on the same div, then the
                # scrollbar occurs inside the border, which looks gross imo
                # https://stackoverflow.com/a/27150900
                html.Div(
                    [
                        html.H4(
                            ag.basename,
                            className="font-monospace",
                            style={
                                "margin-top": "2em",
                                # If the user passes in a graph with a really
                                # long filename, split it over multiple lines.
                                # There are multiple ways to do this in CSS but
                                # this seems best for this purpose:
                                # https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_text/Wrapping_breaking_text
                                "word-break": "break-all",
                            },
                        ),
                        html.P(
                            [
                                f"{ui_utils.pluralize(ag.node_ct, 'node')}, "
                                f"{ui_utils.pluralize(ag.edge_ct, 'edge')}."
                            ]
                        ),
                        html.P(
                            f"{ui_utils.pluralize(len(ag.components), 'component')}."
                        ),
                        html.P(
                            html.Span(
                                "Nothing currently drawn.",
                                id="currDrawnText",
                            ),
                        ),
                        ctrl_sep_invis,
                        html.P(
                            [
                                html.Button(
                                    [
                                        html.I(
                                            className="bi bi-grid-1x2-fill"
                                        ),
                                        html.Span(
                                            "Graph info",
                                            className="iconlbl",
                                        ),
                                    ],
                                    id="infoButton",
                                    className="btn btn-light",
                                    type="button",
                                    **{
                                        "data-bs-toggle": "modal",
                                        "data-bs-target": "#infoDialog",
                                    },
                                )
                            ],
                        ),
                        ctrl_sep,
                        html.H4("Draw"),
                        # https://getbootstrap.com/docs/5.3/components/dropdowns/#single-button
                        html.Div(
                            [
                                html.Button(
                                    cc_selection_options[
                                        DEFAULT_CC_SELECTION_METHOD
                                    ],
                                    className="btn btn-sm btn-light dropdown-toggle",
                                    id="ccDrawingSelect",
                                    type="button",
                                    style={"width": "100%"},
                                    # We'll update the button's value along with its
                                    # children when the user selects a drawing method.
                                    # The value is used by our code to determine the
                                    # currently-selected drawing method.
                                    value=DEFAULT_CC_SELECTION_METHOD,
                                    **{
                                        "data-bs-toggle": "dropdown",
                                        "aria-expanded": "false",
                                    },
                                ),
                                html.Ul(
                                    [
                                        html.Li(
                                            html.A(
                                                cc_selection_options[
                                                    "ccDrawingSizeRank"
                                                ],
                                                className=CC_SELECTION_A_CLASSES_MULTIPLE_CCS,
                                                id="ccDrawingSizeRank",
                                                **CC_SELECTION_A_ATTRS_MULTIPLE_CCS,
                                            ),
                                        ),
                                        html.Li(
                                            html.A(
                                                cc_selection_options[
                                                    "ccDrawingNodeNames"
                                                ],
                                                className=CC_SELECTION_A_CLASSES_MULTIPLE_CCS,
                                                id="ccDrawingNodeNames",
                                                **CC_SELECTION_A_ATTRS_MULTIPLE_CCS,
                                            ),
                                        ),
                                        html.Li(
                                            html.A(
                                                cc_selection_options[
                                                    "ccDrawingAll"
                                                ],
                                                className="dropdown-item",
                                                id="ccDrawingAll",
                                            ),
                                        ),
                                    ],
                                    id="ccDrawingUl",
                                    # position-fixed is needed to make the
                                    # dropdown menu escape the control panel
                                    # when zoomed in super far: this fixes
                                    # https://github.com/marbl/MetagenomeScope/issues/270
                                    # I tried a billion other things and none
                                    # of them worked, except for this one.
                                    # God alone knows why. Shoutouts to
                                    # https://stackoverflow.com/a/74794768.
                                    className="dropdown-menu dropdown-menu-sm position-fixed",
                                    style={"font-size": "0.85em"},
                                ),
                            ],
                            className="dropdown",
                        ),
                        html.Div(
                            [
                                html.Button(
                                    html.I(className="bi bi-dash-lg"),
                                    id="ccSizeRankDecrBtn",
                                    # might add borders to the sides of these later
                                    className="btn btn-light cc-size-rank-adj",
                                    type="button",
                                ),
                                # dash doesn't have a html.Input thing like it
                                # does for other HTML tags, so we use dcc.Input
                                # which apparently is close enough
                                # (https://github.com/plotly/dash/issues/2791)
                                dcc.Input(
                                    type="text",
                                    id="ccSizeRankSelector",
                                    className="form-control",
                                    value="1",
                                    placeholder="Size rank(s)",
                                ),
                                html.Button(
                                    html.I(className="bi bi-plus-lg"),
                                    id="ccSizeRankIncrBtn",
                                    className="btn btn-light cc-size-rank-adj",
                                    type="button",
                                ),
                            ],
                            id="ccSizeRankSelectorEles",
                            className=css_config.CC_SELECTOR_ELES_CLASSES
                            + (
                                " invisibleButStillThere"
                                if "ccDrawingSizeRank"
                                != DEFAULT_CC_SELECTION_METHOD
                                else ""
                            ),
                        ),
                        html.Div(
                            [
                                dcc.Input(
                                    type="text",
                                    id="ccNodeNameSelector",
                                    className="form-control",
                                    placeholder="Node name(s)",
                                ),
                            ],
                            id="ccNodeNameSelectorEles",
                            className=css_config.CC_SELECTOR_ELES_CLASSES
                            + (
                                " invisibleButStillThere"
                                if "ccDrawingNodeNames"
                                != DEFAULT_CC_SELECTION_METHOD
                                else ""
                            ),
                        ),
                        html.Button(
                            [
                                html.I(className="bi bi-gear-fill"),
                                html.Span(
                                    "Options",
                                    className="iconlbl",
                                ),
                            ],
                            id="drawingOptionsButton",
                            className="btn btn-light",
                            type="button",
                            style={"margin-right": "1em"},
                        ),
                        html.Button(
                            [
                                html.I(className="bi bi-brush-fill"),
                                html.Span(
                                    "Draw",
                                    className="iconlbl",
                                ),
                            ],
                            id="drawButton",
                            className="btn btn-light",
                            type="button",
                        ),
                        ctrl_sep,
                        html.H4("Search"),
                        dbc.InputGroup(
                            [
                                dbc.Input(
                                    id="searchInput",
                                    placeholder="Node name(s)",
                                ),
                                dbc.Button(
                                    html.I(className="bi bi-search"),
                                    id="searchButton",
                                    color="light",
                                ),
                            ]
                        ),
                        ctrl_sep,
                        html.H4("Selected"),
                        html.Div(
                            ui_utils.get_selected_ele_html(
                                "Node",
                                [
                                    {
                                        "field": ui_config.NODE_TBL_NAME_COL,
                                        "headerName": "Name",
                                        "cellDataType": "text",
                                    },
                                ],
                            )
                            + ui_utils.get_selected_ele_html(
                                "Edge",
                                [
                                    {
                                        "field": ui_config.EDGE_TBL_SRC_COL,
                                        "headerName": "From",
                                        "cellDataType": "text",
                                    },
                                    {
                                        "field": ui_config.EDGE_TBL_TGT_COL,
                                        "headerName": "To",
                                        "cellDataType": "text",
                                    },
                                ],
                            )
                            + ui_utils.get_selected_ele_html(
                                "Pattern",
                                [
                                    {
                                        "field": ui_config.PATT_TBL_TYPE_COL,
                                        "headerName": "Type",
                                        "cellDataType": "text",
                                    },
                                    {
                                        "field": ui_config.PATT_TBL_NCT_COL,
                                        "headerName": "# nodes",
                                        "cellDataType": "number",
                                    },
                                    {
                                        "field": ui_config.PATT_TBL_ECT_COL,
                                        "headerName": "# edges",
                                        "cellDataType": "number",
                                    },
                                    {
                                        "field": ui_config.PATT_TBL_PCT_COL,
                                        "headerName": "# patts",
                                        "cellDataType": "number",
                                    },
                                ],
                            ),
                            className="noPadding",
                        ),
                        *path_html,
                        ctrl_sep,
                        html.H4(
                            "Colors",
                        ),
                        ctrl_sep_invis,
                        html.H5(
                            "Nodes",
                        ),
                        html.Div(
                            [
                                # See section "RadioItems as ButtonGroup" on
                                # https://www.dash-bootstrap-components.com/docs/components/button_group/
                                dbc.RadioItems(
                                    options=[
                                        {
                                            "label": colorful_random_text,
                                            "value": ui_config.COLORING_RANDOM,
                                        },
                                        {
                                            "label": "Uniform",
                                            "value": ui_config.COLORING_UNIFORM,
                                        },
                                    ],
                                    value=ui_config.DEFAULT_NODE_COLORING,
                                    className="btn-group",
                                    inputClassName="btn-check",
                                    labelClassName="btn btn-sm btn-outline-light",
                                    labelCheckedClassName="active",
                                    id="nodeColorRadio",
                                ),
                            ],
                            className="radio-group",
                        ),
                        ctrl_sep_invis,
                        html.H5(
                            "Edges",
                        ),
                        html.Div(
                            [
                                dbc.RadioItems(
                                    options=[
                                        {
                                            "label": colorful_random_text,
                                            "value": ui_config.COLORING_RANDOM,
                                        },
                                        {
                                            "label": "Uniform",
                                            "value": ui_config.COLORING_UNIFORM,
                                        },
                                    ],
                                    value=ui_config.DEFAULT_EDGE_COLORING,
                                    className="btn-group",
                                    inputClassName="btn-check",
                                    labelClassName="btn btn-sm btn-outline-light",
                                    labelCheckedClassName="active",
                                    id="edgeColorRadio",
                                ),
                            ],
                            className="radio-group",
                        ),
                        ctrl_sep,
                        html.H4("Screenshots"),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        dbc.RadioItems(
                                            options=[
                                                {
                                                    "label": "PNG",
                                                    "value": ui_config.SCREENSHOT_PNG,
                                                },
                                                {
                                                    "label": "JPG",
                                                    "value": ui_config.SCREENSHOT_JPG,
                                                },
                                                {
                                                    "label": "SVG",
                                                    "value": ui_config.SCREENSHOT_SVG,
                                                },
                                            ],
                                            value=ui_config.DEFAULT_SCREENSHOT_FILETYPE,
                                            className="btn-group",
                                            inputClassName="btn-check",
                                            labelClassName="btn btn-sm btn-outline-light",
                                            labelCheckedClassName="active",
                                            id="imageTypeRadio",
                                        ),
                                    ],
                                    className="radio-group",
                                    # Needed in order to allow these buttons to be
                                    # on the same line as the export button. i
                                    # don't know why exactly this works - it was
                                    # in the CSS for .btn-group for old mgsc, so
                                    # I guess this is from Bootstrap 3.3? Old magic
                                    style={"display": "inline-block"},
                                ),
                                html.Button(
                                    [
                                        html.I(className="bi bi-camera-fill"),
                                        html.Span(
                                            "Save",
                                            className="iconlbl",
                                        ),
                                    ],
                                    id="panelExportButton",
                                    className="btn btn-light",
                                    type="button",
                                ),
                            ],
                        ),
                        ctrl_sep,
                    ],
                    id="innerControlsDivForBorder",
                    style={
                        "border-right": f"{css_config.CONTROLS_BORDER_THICKNESS} solid {css_config.CONTROLS_BORDER_COLOR}",
                        "background-color": css_config.CONTROLS_BG_COLOR,
                        "width": "100%",
                    },
                ),
                id="controls",
                style={
                    "position": "absolute",
                    "top": "0em",
                    "bottom": "0em",
                    "left": "0em",
                    "width": css_config.CONTROLS_WIDTH,
                    "height": "100%",
                    # seems to help force the inner div to span the entire
                    # page height - https://stackoverflow.com/a/52408006
                    "display": "grid",
                    # only show the scrollbar when needed - firefox doesn't
                    # seem to need this, but chrome does
                    "overflow-y": "auto",
                    "text-align": "center",
                    "z-index": "1",
                    "color": css_config.CONTROLS_FG_COLOR,
                    "background-color": css_config.CONTROLS_BORDER_COLOR,
                    "transition": f"left {css_config.CONTROLS_TRANSITION_DURATION}",
                },
                className="",
            ),
            # cy
            html.Div(
                [
                    # In previous versions of MetagenomeScope, we would destroy
                    # and create a Cytoscape.js instance every time the user
                    # would draw a new section of the graph. Here, though, it
                    # is more natural to have a single persistent instance of
                    # Cytoscape.js -- and just add elements, adjust its
                    # stylesheet, etc. as requested. This both works better
                    # with Dash and is recommended by Cytoscape.js' docs
                    # ("Optimisations" > "Recycle large instances").
                    cyto.Cytoscape(
                        id="cy",
                        elements=[],
                        layout={"name": "dagre", "rankDir": "LR"},
                        style={
                            "width": "100%",
                            "height": "100%",
                        },
                        boxSelectionEnabled=True,
                        maxZoom=9,
                        stylesheet=cy_utils.get_cyjs_stylesheet(
                            node_coloring=ui_config.DEFAULT_NODE_COLORING,
                            edge_coloring=ui_config.DEFAULT_EDGE_COLORING,
                        ),
                    )
                ],
                id="cyDiv",
                style={
                    "position": "absolute",
                    "left": css_config.CONTROLS_WIDTH,
                    "top": "0em",
                    "bottom": "0em",
                    "right": "0em",
                    "z-index": "0",
                    # for debugging layout jank...
                    # "border": "3px solid #00ff00",
                    # NOTE: so, if you adjust this
                    # (like https://js.cytoscape.org/demos/fcose-gene/) so that
                    # the control panel is on the right and we're changing the
                    # "right" style property of #cyDiv, then the canvas
                    # contents no longer shift (while still resizing the
                    # canvas to fill the void left by the hidden control
                    # panel). I spent multiple hours trying to find a way
                    # to make this work on the left side of the canvas and was
                    # unsuccessful -- I think it might be something to do with
                    # how HTML canvases work under the hood. idk. anyway this
                    # at least adds a smooth transition.
                    "transition": f"left {css_config.CONTROLS_TRANSITION_DURATION}",
                },
            ),
            # floating buttons on top of the Cytoscape.js graph
            html.Button(
                html.I(className="bi bi-camera-fill"),
                id="floatingExportButton",
                className="btn btn-light floatingButton",
                type="button",
            ),
            html.Div(
                [
                    html.Button(
                        html.I(className="bi bi-arrows-angle-contract"),
                        id="fitSelectedButton",
                        className="btn btn-light floatingButton",
                        type="button",
                    ),
                    html.Br(),
                    html.Button(
                        html.I(className="bi bi-arrows-angle-expand"),
                        id="fitButton",
                        className="btn btn-light floatingButton",
                        type="button",
                    ),
                ],
                id="floatingButtonsBottomRight",
            ),
            # Graph info modal dialog
            # https://getbootstrap.com/docs/5.3/components/modal/#live-demo
            html.Div(
                html.Div(
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.H1(
                                        [
                                            html.I(
                                                className="bi bi-grid-1x2-fill"
                                            ),
                                            html.Span(
                                                "Graph information",
                                                className="iconlbl",
                                            ),
                                        ],
                                        className="modal-title fs-5",
                                        id="infoDialogLabel",
                                    ),
                                    html.Button(
                                        className="btn-close",
                                        type="button",
                                        **{
                                            "data-bs-dismiss": "modal",
                                            "aria-label": "Close",
                                        },
                                    ),
                                ],
                                className="modal-header",
                            ),
                            html.Div(
                                [
                                    # navigation adapted from
                                    # https://getbootstrap.com/docs/5.3/components/navs-tabs/#javascript-behavior
                                    html.Ul(
                                        [
                                            html.Li(
                                                html.Button(
                                                    "Overview",
                                                    className="nav-link active",
                                                    id="statsTab",
                                                    type="button",
                                                    role="tab",
                                                    **{
                                                        "data-bs-toggle": "tab",
                                                        "data-bs-target": "#statsTabPane",
                                                        "aria-controls": "statsTabPane",
                                                        "aria-selected": "true",
                                                    },
                                                ),
                                                className="nav-item",
                                                role="presentation",
                                            ),
                                            (
                                                html.Li(
                                                    html.Button(
                                                        "Components",
                                                        className="nav-link",
                                                        id="ccTab",
                                                        type="button",
                                                        role="tab",
                                                        **{
                                                            "data-bs-toggle": "tab",
                                                            "data-bs-target": "#ccTabPane",
                                                            "aria-controls": "ccTabPane",
                                                            "aria-selected": "false",
                                                        },
                                                    ),
                                                    className="nav-item",
                                                    role="presentation",
                                                )
                                                if multiple_ccs
                                                else None
                                            ),
                                            html.Li(
                                                html.Button(
                                                    "Sequences",
                                                    className="nav-link",
                                                    id="seqLenTab",
                                                    type="button",
                                                    role="tab",
                                                    **{
                                                        "data-bs-toggle": "tab",
                                                        "data-bs-target": "#seqLenTabPane",
                                                        "aria-controls": "seqLenTabPane",
                                                        "aria-selected": "false",
                                                    },
                                                ),
                                                className="nav-item",
                                                role="presentation",
                                            ),
                                        ],
                                        id="infoDialogTabs",
                                        role="tablist",
                                        className="nav nav-tabs",
                                    ),
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.Table(
                                                        html.Tbody(
                                                            [
                                                                html.Tr(
                                                                    [
                                                                        html.Th(
                                                                            "Filename"
                                                                        ),
                                                                        html.Th(
                                                                            "Filetype",
                                                                        ),
                                                                        html.Th(
                                                                            "# nodes"
                                                                        ),
                                                                        html.Th(
                                                                            "# edges"
                                                                        ),
                                                                        html.Th(
                                                                            "# components"
                                                                        ),
                                                                    ]
                                                                ),
                                                                html.Tr(
                                                                    [
                                                                        html.Td(
                                                                            ag.basename,
                                                                            className="font-monospace",
                                                                        ),
                                                                        html.Td(
                                                                            ag.filetype,
                                                                            className="font-monospace",
                                                                        ),
                                                                        html.Td(
                                                                            f"{ag.node_ct:,}",
                                                                        ),
                                                                        html.Td(
                                                                            f"{ag.edge_ct:,}",
                                                                        ),
                                                                        html.Td(
                                                                            f"{len(ag.components):,}"
                                                                        ),
                                                                    ]
                                                                ),
                                                            ]
                                                        ),
                                                        className=css_config.INFO_DIALOG_TABLE_CLASSES,
                                                    ),
                                                    html.P(
                                                        "Note that, as of writing, these counts include "
                                                        "both + and - copies of nodes / edges / components."
                                                    ),
                                                    html.P(
                                                        [
                                                            "Based on the input graph's filetype, we "
                                                            "assume its sequences are stored on its ",
                                                            html.Span(
                                                                ag.seq_noun
                                                                + "s",
                                                                className="fw-bold",
                                                            ),
                                                            ".",
                                                        ]
                                                    ),
                                                    ui_utils.get_length_info(
                                                        ag
                                                    ),
                                                ],
                                                id="statsTabPane",
                                                className="tab-pane fade show active",
                                                role="tabpanel",
                                                tabIndex="0",
                                                **{
                                                    "aria-labelledby": "statsTab"
                                                },
                                            ),
                                            (
                                                html.Div(
                                                    [
                                                        html.Ul(
                                                            [
                                                                html.Li(
                                                                    html.Button(
                                                                        "Treemap of nodes",
                                                                        className="nav-link active",
                                                                        id="ccNestTreemapTab",
                                                                        type="button",
                                                                        role="tab",
                                                                        **{
                                                                            "data-bs-toggle": "tab",
                                                                            "data-bs-target": "#ccNestTreemapTabPane",
                                                                            "aria-controls": "ccNestTreemapTabPane",
                                                                            "aria-selected": "true",
                                                                        },
                                                                    ),
                                                                    className="nav-item",
                                                                    role="presentation",
                                                                ),
                                                                html.Li(
                                                                    html.Button(
                                                                        "Histogram of nodes/edges",
                                                                        className="nav-link",
                                                                        id="ccNestHistTab",
                                                                        type="button",
                                                                        role="tab",
                                                                        **{
                                                                            "data-bs-toggle": "tab",
                                                                            "data-bs-target": "#ccNestHistTabPane",
                                                                            "aria-controls": "ccNestHistTabPane",
                                                                            "aria-selected": "false",
                                                                        },
                                                                    ),
                                                                    className="nav-item",
                                                                    role="presentation",
                                                                ),
                                                            ],
                                                            className="nav nav-tabs",
                                                            id="ccTabs",
                                                            role="tablist",
                                                        ),
                                                        html.Div(
                                                            [
                                                                html.Div(
                                                                    html.Div(
                                                                        id="ccTreemapContainer",
                                                                    ),
                                                                    className="tab-pane fade show active",
                                                                    id="ccNestTreemapTabPane",
                                                                    role="tabpanel",
                                                                    tabIndex="0",
                                                                    **{
                                                                        "aria-labelledby": "ccNestTreemapTab"
                                                                    },
                                                                ),
                                                                html.Div(
                                                                    html.Div(
                                                                        id="ccHistContainer",
                                                                    ),
                                                                    className="tab-pane fade",
                                                                    id="ccNestHistTabPane",
                                                                    role="tabpanel",
                                                                    tabIndex="0",
                                                                    **{
                                                                        "aria-labelledby": "ccNestHistTab"
                                                                    },
                                                                ),
                                                            ],
                                                            className="tab-content",
                                                            id="ccNestTabContent",
                                                        ),
                                                    ],
                                                    id="ccTabPane",
                                                    className="tab-pane fade show",
                                                    role="tabpanel",
                                                    tabIndex="0",
                                                    **{
                                                        "aria-labelledby": "ccTab"
                                                    },
                                                )
                                                if multiple_ccs
                                                else None
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        id="seqLenHistContainer",
                                                    ),
                                                ],
                                                id="seqLenTabPane",
                                                className="tab-pane fade",
                                                role="tabpanel",
                                                tabIndex="0",
                                                **{
                                                    "aria-labelledby": "seqLenTab"
                                                },
                                            ),
                                        ],
                                        className="tab-content",
                                        id="infoDialogTabContent",
                                    ),
                                ],
                                className="modal-body",
                            ),
                        ],
                        className="modal-content",
                    ),
                    className="modal-dialog modal-xl",
                ),
                id="infoDialog",
                className="modal fade",
                # additional accessibility things from bootstrap examples that
                # may not be necessary for a visualization tool like this atm
                **{
                    "aria-hidden": "true",
                    "aria-labelledby": "infoDialogLabel",
                    "tabIndex": "-1",
                },
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        [
                            html.H1(
                                [
                                    html.I(className="bi bi-gear-fill"),
                                    html.Span(
                                        "Drawing options",
                                        className="iconlbl",
                                    ),
                                ],
                                className="modal-title fs-5",
                            ),
                        ]
                    ),
                    dbc.ModalBody(
                        [
                            html.Div(
                                [
                                    # I'm sticking with a standard dcc.Checklist
                                    # (rather than dbc.Checklist) because I don't
                                    # like the default formatting of their inline
                                    # checklists. Even after doing some massaging
                                    # to make the margins better, there is still an
                                    # ugly unclickable region between the checkbox
                                    # and label... maybe I am just doing something
                                    # wrong, but I think the UX of the dcc.Checklist
                                    # is better.
                                    dcc.Checklist(
                                        options=[
                                            {
                                                "label": "Show patterns",
                                                "value": ui_config.SHOW_PATTERNS,
                                            },
                                        ],
                                        value=ui_config.DEFAULT_DRAW_SETTINGS,
                                        id="drawSettingsChecklist",
                                    )
                                ],
                                className="form-check",
                            ),
                        ]
                    ),
                ],
                id="modal",
                is_open=False,
            ),
            # toast messages will go here. you can change top-0 to bottom-0 to
            # position these in the bottom right of the window; see
            # https://getbootstrap.com/docs/5.3/components/toasts/#live-example
            html.Div(
                id="toastHolder",
                className="toast-container position-fixed top-0 end-0 p-3",
            ),
            # we'll update this when it's time to draw the graph -- after
            # we flush it (removing all currently present elements) and
            # before we redraw it (based on updating this data).
            # See https://github.com/plotly/dash-cytoscape/issues/106#issuecomment-3535358135
            dcc.Store(
                id="doneFlushing",
            ),
            # we'll update this after drawing the graph. As of writing, it is
            # just used to contain a list of the component numbers that are
            # currently drawn. This is useful to have around to help with
            # searching. (We could try to get this info from doneFlushing,
            # but this is risky: doneFlushing can get cleared without redrawing
            # the graph if a bad drawing request is made -- e.g. someone enters
            # in a component size rank that doesn't exist.)
            dcc.Store(
                id="currDrawnInfo",
            ),
            # Similarly, we'll update this during the process of searching
            # for nodes. There is some jank where (1) Dash Cytoscape doesn't
            # apparently support procedurally selecting elements in the graph
            # through a callback or something, and (2) JS code can only see
            # stuff about the current page state -- it can't access the entire
            # graph on the python side.
            #
            # So! In order to make searching work, we use an ordinary callback
            # (in Python) that checks that nodes are in the graph, etc., and
            # if we still want to select stuff from the currently-drawn graph
            # then we update this Store.
            dcc.Store(
                id="nodeSelectionInfo",
            ),
            # And when selecting stuff in a path
            dcc.Store(
                id="pathSelectionInfo",
            ),
        ],
    )

    if multiple_ccs:

        @callback(
            Output("ccHistContainer", "children"),
            Input("ccNestHistTab", "n_clicks"),
            prevent_initial_call=True,
        )
        def plot_cc_hist(n_clicks):
            graph_utils.validate_multiple_ccs(ag)
            cc_node_cts, cc_edge_cts = ag.get_component_node_and_edge_cts()

            fig = go.Figure()
            fig.add_trace(
                go.Histogram(
                    x=cc_node_cts,
                    marker_color="#0a0",
                    marker_line_width=2,
                    marker_line_color="#030",
                    name="# nodes",
                )
            )
            fig.add_trace(
                go.Histogram(
                    x=cc_edge_cts,
                    marker_color="#447",
                    marker_line_width=2,
                    marker_line_color="#005",
                    marker_pattern_shape="x",
                    marker_pattern_fgcolor="#fff",
                    name="# edges",
                )
            )
            fig.update_layout(
                barmode="stack",
                title_text="Numbers of nodes and edges per component",
                xaxis_title_text="# nodes or # edges",
                yaxis_title_text="# components",
                font=dict(size=16),
                # By default the title is shoved up really high above
                # the figure; this repositions it to be closer, while
                # still keeping a bit of padding. From
                # https://community.plotly.com/t/margins-around-graphs/11550/6
                title=dict(yanchor="bottom", y=1, yref="paper"),
                title_pad=dict(b=30),
                margin=dict(t=75),
            )
            # Hack to add padding to the right of the y-axis tick labels:
            # https://stackoverflow.com/a/66736119
            fig.update_yaxes(ticksuffix=" ")
            return dcc.Graph(figure=fig)

        @callback(
            Output("ccTreemapContainer", "children"),
            Input("ccTab", "n_clicks"),
            prevent_initial_call=True,
        )
        def plot_cc_treemap(n_clicks):
            cc_names, cc_parents, cc_sizes, cc_aggs = ag.to_treemap()
            # silly thing: scale the aggregated rectangles' colors along a
            # distinct purple gradient to make them stand out visually
            cc_marker_colors = color_utils.selectively_interpolate_hsl(cc_aggs)
            fig = go.Figure(
                go.Treemap(
                    # actual data
                    labels=cc_names,
                    parents=cc_parents,
                    values=cc_sizes,
                    # stylistic things
                    marker_colors=cc_marker_colors,
                    # Need to set "total" here so that the size of the top-
                    # level element is treated as the sum of its children,
                    # rather than as an extra size in addition to the sum
                    # of its children. (And we want to set a size of the
                    # top-level element in order to show that in the
                    # hover template, etc.)
                    branchvalues="total",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "<b>Nodes:</b> %{value:,} (%{percentRoot:.2%})"
                    ),
                    # If we don't set name="", then the hover popup shows
                    # "trace 0" next to it and that looks gross
                    name="",
                    root_color="#ddd",
                    # Don't re-sort rectangles by size -- preserve their order
                    # based on their underlying component size ranks, which
                    # I think makes navigation easier for users
                    sort=False,
                )
            )
            fig.update_layout(
                title_text="Number of nodes per component",
                title=dict(yanchor="bottom", y=1, yref="paper"),
                font=dict(size=16),
                title_pad=dict(b=30),
                # Use a bit of extra bottom margin in order to make sure
                # that hover tooltips for rectangles at the bottom of the
                # plot don't get chopped off by the figure border
                margin=dict(l=0, r=0, b=30, t=75),
            )
            return dcc.Graph(figure=fig)

    @callback(
        Output("seqLenHistContainer", "children"),
        Input("seqLenTab", "n_clicks"),
        prevent_initial_call=True,
    )
    def plot_seqlen_hist(n_clicks):
        fig = go.Figure()
        fig.add_trace(
            go.Histogram(
                x=ag.seq_lengths,
                marker_color="#811",
                marker_line_width=2,
                marker_line_color="#100",
                name="Sequence lengths",
            )
        )
        fig.update_layout(
            title_text=f"{ag.seq_noun.title()} sequence lengths",
            xaxis_title_text="Length (bp)",
            yaxis_title_text=f"# {ag.seq_noun}s",
            font=dict(size=16),
            title=dict(yanchor="bottom", y=1, yref="paper"),
            title_pad=dict(b=30),
            margin=dict(t=75),
        )
        fig.update_yaxes(ticksuffix=" ")
        return dcc.Graph(figure=fig)

    @callback(
        Output("controls", "className"),
        Output("controlsTogglerIcon", "className"),
        Output("cyDiv", "style"),
        State("controls", "className"),
        State("cyDiv", "style"),
        Input("controlsToggler", "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_controls(controls_classes, cy_div_style, n_clicks):
        """Toggles visibility of the control panel's div.

        Also toggles the color of the toggler hamburger icon -- it is colored
        light when the controls are visible, and dark when the controls are not
        visible. (We may want to adjust this in a fancier way if/when the user
        can control the background color of the graph, but it's ok for now.)
        """
        if "offscreen-controls" in controls_classes:
            # Make the control panel visible again, and make the cytoscape.js
            # div occupy only part of the screen
            cy_div_style["left"] = css_config.CONTROLS_WIDTH
            return ("", CONTROLS_TOGGLER_ICON_CLASSES, cy_div_style)
        else:
            # Hide the control panel, and make the cytoscape.js div occupy the
            # whole screen
            cy_div_style["left"] = "0em"
            return (
                "offscreen-controls",
                CONTROLS_TOGGLER_ICON_CLASSES + " darkToggler",
                cy_div_style,
            )

    @callback(
        Output("modal", "is_open"),
        Input("drawingOptionsButton", "n_clicks"),
        State("modal", "is_open"),
    )
    def toggle_drawing_options_modal(nc, is_open):
        # from https://www.dash-bootstrap-components.com/docs/components/modal/
        if nc:
            return not is_open
        return is_open

    # By default, bootstrap's dropdowns don't change the button element (i.e.
    # the thing showing the name of the dropdown), as an ordinary HTML <select>
    # would. You can use <select>s with bootstrap, but the styling is limited
    # and you can't (easily?) show icons :( You can also use Dash's
    # dcc.Dropdown objects, which DO allow icons and also allow mutating the
    # dropdown name on selecting something, but bootstrap's styling apparently
    # clobbers Dash's and the result looks kind of gross.
    #
    # So! A reasonable option, I think, is using Bootstrap icons but just
    # adding some custom code here to change the dropdown's button based on
    # what gets selected. The "children" output changes the contents of the
    # dropdown button to use the fancy icon and label, and the "value" is an
    # easy-to-read label for what drawing method is currently selected.
    @callback(
        Output("ccDrawingSelect", "children"),
        Output("ccDrawingSelect", "value"),
        Output("ccSizeRankSelectorEles", "className"),
        Output("ccNodeNameSelectorEles", "className"),
        State("ccSizeRankSelectorEles", "className"),
        State("ccNodeNameSelectorEles", "className"),
        Input("ccDrawingSizeRank", "n_clicks"),
        Input("ccDrawingNodeNames", "n_clicks"),
        Input("ccDrawingAll", "n_clicks"),
        prevent_initial_call=True,
    )
    def change_drawing_method(
        cc_sr_eles_classes,
        cc_nn_eles_classes,
        cc_sr_clicks,
        cc_nn_clicks,
        cc_all_clicks,
    ):
        if ctx.triggered_id == "ccDrawingSizeRank":
            cc_sr_eles_classes = css_config.CC_SELECTOR_ELES_CLASSES
            cc_nn_eles_classes = (
                css_config.CC_SELECTOR_ELES_CLASSES + " invisibleButStillThere"
            )
        elif ctx.triggered_id == "ccDrawingNodeNames":
            cc_sr_eles_classes = (
                css_config.CC_SELECTOR_ELES_CLASSES + " invisibleButStillThere"
            )
            cc_nn_eles_classes = css_config.CC_SELECTOR_ELES_CLASSES
        else:
            # draw all components, so hide both size rank and node name eles
            cc_sr_eles_classes = (
                css_config.CC_SELECTOR_ELES_CLASSES + " invisibleButStillThere"
            )
            cc_nn_eles_classes = (
                css_config.CC_SELECTOR_ELES_CLASSES + " invisibleButStillThere"
            )
        return (
            cc_selection_options[ctx.triggered_id],
            ctx.triggered_id,
            cc_sr_eles_classes,
            cc_nn_eles_classes,
        )

    @callback(
        Output("ccSizeRankSelector", "value"),
        State("ccSizeRankSelector", "value"),
        Input("ccSizeRankDecrBtn", "n_clicks"),
        Input("ccSizeRankIncrBtn", "n_clicks"),
        prevent_initial_call=True,
    )
    def update_cc_size_rank(size_rank, decr_n_clicks, incr_n_clicks):
        # reset to something sane if empty
        if size_rank is None or size_rank == "":
            return "1"

        # If the text is something like "-5", this is probably the
        # user specifying a half-open range {1,2,3,4,5} rather then
        # them trying to access component negative five. seriously
        # how would that even work. so anyway let's avoid false alarms
        if size_rank[0] == "-":
            return size_rank

        try:
            # just in case the user gets confused and types in "#2"
            # or something, let's be okay with that. we will update
            # the number correctly, but without the "#", which should
            # be a nice sort of cue that "you don't need the #"
            if size_rank[0] == "#":
                size_rank = size_rank[1:]
            num_size_rank = int(size_rank)
            if ctx.triggered_id == "ccSizeRankDecrBtn":
                adjfunc = ui_utils.decr_size_rank
            else:
                adjfunc = ui_utils.incr_size_rank
            return str(adjfunc(num_size_rank, 1, len(ag.components)))
        except ValueError:
            # TODO: maybe update in the future to parse ranges, etc.,
            # and adjust accordingly? but that would require a lot of
            # effort for minimal benefit
            return size_rank

    @callback(
        Output("cy", "stylesheet"),
        Input("nodeColorRadio", "value"),
        Input("edgeColorRadio", "value"),
        prevent_initial_call=True,
    )
    def update_colorings(node_color_radio, edge_color_radio):
        return cy_utils.get_cyjs_stylesheet(
            node_coloring=node_color_radio,
            edge_coloring=edge_color_radio,
        )

    @callback(
        Output("cy", "generateImage"),
        State("imageTypeRadio", "value"),
        Input("panelExportButton", "n_clicks"),
        Input("floatingExportButton", "n_clicks"),
        prevent_initial_call=True,
    )
    def export_screenshot(image_type, panel_n_clicks, floating_n_clicks):
        # see https://dash.plotly.com/cytoscape/images for a high-level
        # tutorial, and https://github.com/plotly/dash-cytoscape/blob/f96e760f3b84c3f4d7ecbfaa905e9d57c698456d/dash_cytoscape/Cytoscape.py#L194
        # for detailed options
        return {
            "type": image_type,
            "filename": ui_utils.get_screenshot_basename(),
            "action": "download",
        }

    @callback(
        Output("toastHolder", "children", allow_duplicate=True),
        Output("cy", "elements", allow_duplicate=True),
        Output("doneFlushing", "data"),
        State("toastHolder", "children"),
        State("cy", "elements"),
        State("ccDrawingSelect", "value"),
        State("ccSizeRankSelector", "value"),
        State("ccNodeNameSelector", "value"),
        State("drawSettingsChecklist", "value"),
        Input("drawButton", "n_clicks"),
        Input("ccSizeRankSelector", "n_submit"),
        Input("ccNodeNameSelector", "n_submit"),
        prevent_initial_call=True,
    )
    def flush(
        curr_toasts,
        curr_cy_eles,
        cc_drawing_selection_type,
        size_ranks,
        node_names,
        draw_settings,
        draw_btn_n_clicks,
        size_rank_input_n_submit,
        node_name_input_n_submit,
    ):
        """Sanity-checks a drawing request before drawing.

        Note that this can now be triggered by:
        (1) clicking on the "Draw" button,
        (2) pressing Enter in the size rank input, or
        (3) pressing Enter in the node name input.
        """
        logging.debug(
            "Received request to draw the graph. Validating request."
        )

        if cc_drawing_selection_type == "ccDrawingSizeRank":
            try:
                cc_nums = ui_utils.get_size_ranks(
                    size_ranks, len(ag.components)
                )
            except UIError as err:
                return (
                    ui_utils.add_error_toast(
                        curr_toasts, "Size rank error", str(err)
                    ),
                    curr_cy_eles,
                    {"requestGood": False},
                )
        elif cc_drawing_selection_type == "ccDrawingNodeNames":
            try:
                nn2cn = ag.get_nodename2ccnum(node_names)
            except UIError as err:
                return (
                    ui_utils.add_error_toast(
                        curr_toasts, "Node name error", str(err)
                    ),
                    curr_cy_eles,
                    {"requestGood": False},
                )
            cc_nums = set(nn2cn.values())
        else:
            cc_nums = range(1, len(ag.components) + 1)

        # Parse other (less easy to mess up) drawing options
        incl_patterns = False
        for val in draw_settings:
            if val == ui_config.SHOW_PATTERNS:
                incl_patterns = True

        # Okay, now we've done enough checks that this request to draw the
        # graph seems good. Let's clear all elements in the graph and trigger
        # draw(), which will actually add new elements to the graph.
        ccn = "cc" if len(cc_nums) == 1 else "ccs"
        # cc_nums has to be JSON-serializable
        cc_nums = list(cc_nums)
        logging.debug(
            f"Request to draw {ccn} {ui_utils.fmt_num_ranges(cc_nums)} "
            "seems good; flushing the graph."
        )

        return (
            curr_toasts,
            [],
            {
                "requestGood": True,
                "cc_nums": cc_nums,
                "patterns": incl_patterns,
            },
        )

    @callback(
        Output("cy", "elements", allow_duplicate=True),
        Output("currDrawnText", "children"),
        Output("currDrawnInfo", "data"),
        State("cy", "elements"),
        State("currDrawnText", "children"),
        State("currDrawnInfo", "data"),
        Input("doneFlushing", "data"),
        prevent_initial_call=True,
    )
    def draw(
        curr_cy_eles,
        curr_curr_drawn_text,
        curr_curr_drawn_info,
        curr_done_flushing,
    ):
        # as far as I can tell, this gets triggered whenever doneFlushing is
        # updated -- even if it is updated to the exact same thing as it was
        # before. To avoid making us redraw the entire graph if the user just
        # like specified a node name that didn't exist when searching for a cc,
        # we use the "requestGood" key in doneFlushing to let us know when we
        # ACTUALLY want to redraw the graph.
        if curr_done_flushing["requestGood"]:
            logging.debug(
                "Request good, so flushing should be done. Beginning drawing."
            )
            cc_nums = curr_done_flushing["cc_nums"]
            incl_patterns = curr_done_flushing["patterns"]
            logging.debug(
                "Converting graph to Cytoscape.js elements ("
                f"{ui_utils.pluralize(len(cc_nums), 'cc')}, "
                f"show patterns = {incl_patterns}"
                ")..."
            )
            new_cy_eles = ag.to_cyjs(cc_nums, incl_patterns=incl_patterns)
            logging.debug(f"...Done. {len(new_cy_eles):,} ele(s) total.")
            return (
                new_cy_eles,
                f"Currently drawn: {ui_utils.fmt_num_ranges(cc_nums)}",
                {"cc_nums": cc_nums},
            )
        else:
            logging.debug("Caught a bad drawing request. Not redrawing.")
            return (
                curr_cy_eles,
                curr_curr_drawn_text,
                curr_curr_drawn_info,
            )

    # When drawing is finished, update the paths div with info about all
    # paths selectable for the currently drawn region of the graph
    if paths_given:

        @callback(
            Output("pathCount", "children"),
            Output("pathList", "rowData"),
            Output("pathCount", "color"),
            Input("currDrawnInfo", "data"),
            prevent_initial_call=True,
        )
        def update_curr_available_paths(curr_drawn_info):
            logging.debug(
                "Updating info about available paths based on what was drawn..."
            )
            # get the list of currently available paths, based on what's drawn
            available_pathnames = path_utils.get_available_list(
                curr_drawn_info["cc_nums"], ag.ccnum2pathnames
            )
            act = len(available_pathnames)
            # show a summary
            available_count_text = path_utils.get_available_count_text(
                act, len(ag.paths)
            )
            # and also a table
            rows = []
            for p in available_pathnames:
                rows.append(
                    {
                        ui_config.PATH_TBL_NAME_COL: p,
                        ui_config.PATH_TBL_COUNT_COL: len(ag.paths[p]),
                    }
                )
            logging.debug(f"Done. {available_count_text}")
            return available_count_text, rows, ui_utils.get_badge_color(act, False)

        @callback(
            Output("pathSelectionInfo", "data"),
            Input("pathList", "cellClicked"),
            prevent_initial_call=True,
        )
        def highlight_path(clicked_cell):
            if clicked_cell["colId"] == ui_config.PATH_TBL_NAME_COL:
                eles = ag.paths[clicked_cell["value"]]
                return {
                    "requestGood": True,
                    "eles": eles,
                    "nodes": ag.node_centric,
                }
            else:
                return {"requestGood": False}

        clientside_callback(
            """
            function(pathSelectionInfo) {
                if (!pathSelectionInfo["requestGood"]) {
                    console.log("Caught a bad path selection request.");
                } else {
                    let cy = document.getElementById("cy")._cyreg.cy;
                    let eles = cy.collection();
                    for (var i = 0; i < pathSelectionInfo["eles"].length; i++) {
                        let name = pathSelectionInfo["eles"][i];
                        if (pathSelectionInfo["nodes"]) {
                            newEles = cy.nodes(
                                '[label="' + name + '"], ' +
                                '[label="' + name + '-L"], ' +
                                '[label="' + name + '-R"]'
                            );
                        } else {
                            newEles = cy.edges('[edgeID="' + name + '"]');
                        }
                        if (newEles.empty()) {
                            alert(
                                "Ele. with name " + name + " not currently " +
                                "drawn? This should never happen by this point."
                            );
                            return;
                        }
                        eles = eles.union(newEles);
                    }
                    cy.fit(eles);
                    cy.filter(':selected').unselect();
                    eles.select();
                }
            }
            """,
            Input("pathSelectionInfo", "data"),
            prevent_initial_call=True,
        )

    # It looks like Bootstrap requires us to use JS to show the toast. If we
    # try to show it ourselves (by just adding the "show" class when creating
    # the toast) then the toast never goes away and also doesn't have smooth
    # animation when appearing. As far as I can tell, using a clientside
    # callback (https://dash.plotly.com/clientside-callbacks) is the smoothest
    # way to do this.
    #
    # (The "data-mgsc-shown" attribute makes sure that we don't re-show a toast
    # that has already been shown. This is because one of the draw() callback's
    # outputs is the toastHolder's children, so even if we just draw the graph
    # successfully without triggering any new toasts then this clientside
    # callback will still be triggered. Oh no! "data-mgsc-shown" fixes things.)
    clientside_callback(
        """
        function(toasts) {
            var tele = document.getElementById("toastHolder").lastChild;
            if (tele !== null && tele.getAttribute("data-mgsc-shown") === "false") {
                var toast = bootstrap.Toast.getOrCreateInstance(tele);
                toast.show();
                tele.setAttribute("data-mgsc-shown", "true");
            }
        }
        """,
        Input("toastHolder", "children"),
        prevent_initial_call=True,
    )

    # Fits the display to everything in the graph using cy.fit().
    # It looks like this is the sort of thing that can't be adjusted by
    # Dash-Cytoscape (since we don't really have a Cytoscape.js "instance"
    # lying around like we did in the JS implementation)...
    #
    # We can work around this by extracting the existing Cytoscape.js instance
    # after-the-fact and then using it to do stuff. There appears to be no
    # official, well-documented way to do this, but the secret evil way of
    # doing this is accessing the _cyreg.cy attribute of the DOM element
    # containing the Cytoscape.js instance (which we've named "cy" above).
    # This is from https://stackoverflow.com/a/52603597.
    #
    # I am hesitant to rely on such a silly hack for this, but it appears that
    # this has remained unbroken for 7+ years now -- and it looks like lots of
    # other Dash-Cytoscape projects use this same workaround, judging by
    # https://github.com/search?q=_cyreg.cy+dash&type=code
    #
    # So I guess we can keep this workaround for now. In the future, if this
    # suddenly breaks, maybe we can just rip out Dash-Cytoscape entirely in
    # favor of handling all of the Cytoscape.js stuff ourself in clientside
    # callbacks / etc. Or we can access the underlying cy instance in a
    # different way (e.g. https://github.com/plotly/dash-cytoscape/issues/187#issuecomment-1924583683
    # which I don't really understand -- where is the "cy" variable coming from
    # there?).
    clientside_callback(
        """
        function(nClicks) {
            let cy = document.getElementById("cy")._cyreg.cy;
            cy.fit();
        }
        """,
        Input("fitButton", "n_clicks"),
        prevent_initial_call=True,
    )

    # NOTE: in older versions of metagenomescope, we maintained a list of
    # selected nodes/edges/patterns using cy.on('select'), etc. This let us
    # avoid having to search through everything drawn in the graph when fitting
    # to all selected elements. I will probably do this eventually (since it
    # will help with dynamically showing info about selected elements) but for
    # now it is sufficient to just search through the graph in this callback.
    clientside_callback(
        """
        function(nClicks) {
            let cy = document.getElementById("cy")._cyreg.cy;
            cy.fit(cy.$(":selected"));
        }
        """,
        Input("fitSelectedButton", "n_clicks"),
        prevent_initial_call=True,
    )

    def toggle_ele_table_classes(classes):
        if "removedEntirely" in classes:
            return (
                css_config.SELECTED_ELE_TBL_CLASSES,
                "bi bi-caret-down-fill",
            )
        else:
            return (
                css_config.SELECTED_ELE_TBL_CLASSES + " removedEntirely",
                "bi bi-caret-right-fill",
            )

    @callback(
        Output("selectedNodeList", "className"),
        Output("selectedNodeOpener", "className"),
        State("selectedNodeList", "className"),
        Input("selectedNodeHeader", "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_node_table(classes, n_clicks):
        return toggle_ele_table_classes(classes)


    @callback(
        Output("selectedEdgeList", "className"),
        Output("selectedEdgeOpener", "className"),
        State("selectedEdgeList", "className"),
        Input("selectedEdgeHeader", "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_edge_table(classes, n_clicks):
        return toggle_ele_table_classes(classes)

    @callback(
        Output("selectedPatternList", "className"),
        Output("selectedPatternOpener", "className"),
        State("selectedPatternList", "className"),
        Input("selectedPatternHeader", "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_pattern_table(classes, n_clicks):
        return toggle_ele_table_classes(classes)

    @callback(
        Output("pathList", "className"),
        Output("pathOpener", "className"),
        State("pathList", "className"),
        Input("pathHeader", "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_path_table(classes, n_clicks):
        return toggle_ele_table_classes(classes)

    @callback(
        Output("selectedNodeList", "rowData"),
        Output("selectedNodeCount", "children"),
        Output("selectedNodeCount", "color"),
        Output("selectedPatternList", "rowData"),
        Output("selectedPatternCount", "children"),
        Output("selectedPatternCount", "color"),
        Input("cy", "selectedNodeData"),
        prevent_initial_call=True,
    )
    def list_selected_nodes_and_patterns(selected_nodes):
        # TODO: record all available data fields and use this info to
        # define table columns. Then, extract this data from the AG here.
        # (We could also pass node data directly to Cytoscape, but that
        # seems wasteful since it involves duplicating the data...)
        node_data = []
        patt_data = []
        for n in selected_nodes:
            if n["ntype"] == cy_config.NODE_DATA_TYPE:
                node_data.append({ui_config.NODE_TBL_NAME_COL: n["label"]})
            else:
                patt_data.append(
                    {
                        ui_config.PATT_TBL_TYPE_COL: config.PT2HR[n["ptype"]],
                        ui_config.PATT_TBL_NCT_COL: n["nct"],
                        ui_config.PATT_TBL_ECT_COL: n["ect"],
                        ui_config.PATT_TBL_PCT_COL: n["pct"],
                    }
                )
        # NOTE: this currently counts both splits of a node towards the
        # count. i guess ideally we only count once? but nbd
        nct = len(node_data)
        pct = len(patt_data)
        return (
            node_data,
            f"{nct:,}",
            ui_utils.get_badge_color(nct),
            patt_data,
            f"{pct:,}",
            ui_utils.get_badge_color(pct),
        )

    @callback(
        Output("selectedEdgeList", "rowData"),
        Output("selectedEdgeCount", "children"),
        Output("selectedEdgeCount", "color"),
        Input("cy", "selectedEdgeData"),
        prevent_initial_call=True,
    )
    def list_selected_edges(selected_edges):
        def id2name(i):
            # Node IDs (in the AssemblyGraph) are integers, but Cytoscape.js
            # expects them to be strings -- so we pass them as strings in the
            # Node / Edge / Pattern .to_cyjs() methods. Here, we need to turn
            # them back into integers in order to look up a node in the
            # AssemblyGraph by its ID.
            return str(ag.nodeid2obj[int(i)].name)

        edge_data = []
        for n in selected_edges:
            edge_data.append(
                {
                    ui_config.EDGE_TBL_SRC_COL: id2name(n["source"]),
                    ui_config.EDGE_TBL_TGT_COL: id2name(n["target"]),
                }
            )
        ect = len(edge_data)
        return edge_data, f"{ect:,}", ui_utils.get_badge_color(ect)

    @callback(
        Output("toastHolder", "children", allow_duplicate=True),
        Output("nodeSelectionInfo", "data"),
        State("toastHolder", "children"),
        State("searchInput", "value"),
        State("currDrawnInfo", "data"),
        Input("searchButton", "n_clicks"),
        Input("searchInput", "n_submit"),
        prevent_initial_call=True,
    )
    def check_nodes_for_search(
        curr_toasts, node_names, curr_curr_drawn_info, n_clicks, n_submit
    ):
        try:
            nn2ccnum = ag.get_nodename2ccnum(node_names)
        except UIError as err:
            # If we fail at this point, it is because either the input text
            # is empty / malformed or because it includes at least one node
            # name that is not present in the graph (in ANY component)
            return (
                ui_utils.add_error_toast(
                    curr_toasts, "Search error", str(err)
                ),
                {"requestGood": False},
            )

        # Find which, if any, components are currently drawn
        if (
            curr_curr_drawn_info is not None
            and "cc_nums" in curr_curr_drawn_info
        ):
            curr_drawn_cc_nums = set(curr_curr_drawn_info["cc_nums"])
        else:
            curr_drawn_cc_nums = set()

        # Which, if any, of the searched-for nodes are currently drawn?
        num_searched_for_nodes = len(nn2ccnum)
        drawn_nodes = []
        undrawn_nodes = []
        for n, c in nn2ccnum.items():
            if c in curr_drawn_cc_nums:
                drawn_nodes.append(n)
            else:
                undrawn_nodes.append(n)

        # If none of these nodes are currently drawn, show an error.
        if len(drawn_nodes) == 0:
            return ui_utils.add_error_toast(
                curr_toasts,
                "Search error",
                body_html=ui_utils.summarize_undrawn_nodes(
                    undrawn_nodes, nn2ccnum, num_searched_for_nodes
                ),
            ), {"requestGood": False}

        # By this point, we know that the request is good; at least one of
        # these nodes is currently drawn, so we can at least show *something.*
        toasts = curr_toasts
        if len(undrawn_nodes) > 0:
            # We will reach this case if someone searched for a list of nodes,
            # and some but not all of these nodes are not currently drawn.
            # In this case we show a warning toast message, not an error one.
            toasts = ui_utils.add_warning_toast(
                curr_toasts,
                "Search warning",
                body_html=ui_utils.summarize_undrawn_nodes(
                    undrawn_nodes, nn2ccnum, num_searched_for_nodes
                ),
            )
        return (
            toasts,
            {"requestGood": True, "nodesToSelect": drawn_nodes},
        )

    clientside_callback(
        """
        function(nodeSelectionInfo) {
            if (!nodeSelectionInfo["requestGood"]) {
                console.log("Caught a bad search request.");
            } else {
                let cy = document.getElementById("cy")._cyreg.cy;
                let eles = cy.collection();
                for (var i = 0; i < nodeSelectionInfo["nodesToSelect"].length; i++) {
                    let nodename = nodeSelectionInfo["nodesToSelect"][i];
                    // BE VERY CAREFUL about escaping strings here with
                    // backslashes. This can cause Dash to jank out with
                    // this infuriatingly vague error:
                    // https://community.plotly.com/t/clientside-callback-example-with-js-function-throws-cannot-read-property-apply-of-undefined-error/44411
                    //
                    // Also, including three queries to detect split nodes is
                    // very silly. Maybe assign each node a "basename" property
                    // or something in to_cyjs() to prevent the need for this?
                    // Or maybe the space requirement from that is prohibitive.
                    //
                    // Also whenever you update this callback you have to use
                    // like ctrl+shift+R or something to get rid of Dash's
                    // cache. Otherwise you get the aforementioned terrible
                    // vague error. Writing this function raised my blood
                    // pressure i think
                    newEles = cy.nodes(
                        '[label="' + nodename + '"], ' +
                        '[label="' + nodename + '-L"], ' +
                        '[label="' + nodename + '-R"]'
                    );
                    if (newEles.empty()) {
                        // I think we could show a toast here but that will
                        // take some finagling
                        alert(
                            "Node with name " + nodename + " not currently " +
                            "drawn? This should never happen by this point."
                        );
                        return;
                    }
                    eles = eles.union(newEles);
                }
                cy.fit(eles);
                cy.filter(':selected').unselect();
                eles.select();
            }
        }
        """,
        Input("nodeSelectionInfo", "data"),
        prevent_initial_call=True,
    )

    app.run(debug=debug, port=port)
