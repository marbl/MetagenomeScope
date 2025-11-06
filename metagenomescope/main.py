#!/usr/bin/env python3

import logging
import math
import base64
import matplotlib
import dash
import dash_cytoscape as cyto
from dash import (
    html,
    callback,
    clientside_callback,
    ctx,
    dcc,
    Input,
    Output,
    State,
)
from io import BytesIO
from matplotlib import pyplot
from . import defaults, cy_config, css_config, ui_utils
from .log_utils import start_log, log_lines_with_sep
from .misc_utils import pluralize
from .graph import AssemblyGraph
from .errors import WeirdError, UIError

# account for tkinter crashing: https://stackoverflow.com/a/51178529
matplotlib.use("Agg")


def run(
    graph: str = None,
    verbose: bool = defaults.VERBOSE,
):
    """Reads the graph and starts a Dash app for visualizing it.

    Parameters
    ----------
    graph: str
        Path to the assembly graph to be visualized.

    verbose: bool
        If True, include DEBUG messages in the log output.

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
            f"Verbose?: {verbose}",
        ],
        logger.info,
        endsepline=True,
    )
    # By default, matplotlib spits out a ton of debug log messages. Normally
    # these go unseen, but since we use debug mode for our verbose settings,
    # using --verbose will mean that all of these messages get shown to the
    # unsuspecting user. I think these messages can be safely hidden, so
    # let's do so. (https://stackoverflow.com/a/58393562)
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

    # Read the assembly graph file and create an object representing it.
    # Creating the AssemblyGraph object will identify patterns, scale nodes and
    # edges, etc.
    ag = AssemblyGraph(graph)

    # Prepare some of the UI components in advance. A nice thing about Dash
    # (which I guess comes from it being built on top of React) is that we can
    # define these kinds of components and reuse them without having to rewrite
    # a bunch of code.
    ctrl_sep = html.Div(
        style={
            "width": "100%",
            "height": css_config.CONTROLS_BORDER_THICKNESS,
            "background-color": "#002",
            "margin": "1.25em 0",
        },
        className="ctrlSep",
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
            html.I(className="bi bi-sort-down"),
            html.Span(
                "One component (by size rank)",
            ),
        ],
        "ccDrawingNodeName": [
            html.I(className="bi bi-search"),
            html.Span(
                "One component (with a node)",
            ),
        ],
        "ccDrawingAll": [
            html.I(className="bi bi-asterisk"),
            html.Span(
                "All components" if multiple_ccs else "Only component in the graph",
            ),
        ],
    }
    DEFAULT_CC_SELECTION_METHOD = "ccDrawingSizeRank" if multiple_ccs else "ccDrawingAll"
    CC_SELECTION_A_CLASSES_MULTIPLE_CCS = "dropdown-item"
    CC_SELECTION_A_ATTRS_MULTIPLE_CCS = {}
    if not multiple_ccs:
        # https://getbootstrap.com/docs/5.3/components/dropdowns/#disabled
        # thankfully this seems to prevent dash from noticing click events on
        # the disabled <a>s in question :)
        CC_SELECTION_A_CLASSES_MULTIPLE_CCS += " disabled"
        CC_SELECTION_A_ATTRS_MULTIPLE_CCS = {"aria-disabled": "true"}

    # update_title=None prevents Dash's default "Updating..." page title change
    app = dash.Dash(__name__, title="MgSc", update_title=None)
    CONTROLS_TOGGLER_ICON_CLASSES = "bi bi-list"
    app.layout = html.Div(
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
                            f"{pluralize(ag.node_ct, 'node')}, "
                            f"{pluralize(ag.edge_ct, 'edge')}."
                        ]
                    ),
                    html.P([f"{pluralize(len(ag.components), 'component')}."]),
                    html.P(
                        [
                            html.Button(
                                [
                                    html.I(className="bi bi-grid-1x2-fill"),
                                    html.Span(
                                        "Graph info", className="iconlbl"
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
                        style={"margin-top": "0.7em"},
                    ),
                    ctrl_sep,
                    html.H4("Draw"),
                    # https://getbootstrap.com/docs/5.3/components/dropdowns/#single-button
                    html.Div(
                        [
                            html.Button(
                                cc_selection_options[DEFAULT_CC_SELECTION_METHOD],
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
                                                "ccDrawingNodeName"
                                            ],
                                            className=CC_SELECTION_A_CLASSES_MULTIPLE_CCS,
                                            id="ccDrawingNodeName",
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
                                className="dropdown-menu dropdown-menu-sm",
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
                                type="number",
                                id="ccSizeRankSelector",
                                className="form-control",
                                value=1,
                                min=1,
                                max=len(ag.components),
                            ),
                            html.Button(
                                html.I(className="bi bi-plus-lg"),
                                id="ccSizeRankIncrBtn",
                                className="btn btn-light cc-size-rank-adj",
                                type="button",
                            ),
                        ],
                        id="ccSizeRankSelectorEles",
                        # The default cc selection option is "draw cc by size
                        # rank". However, if the graph only has one cc, then
                        # "draw all components" aka "draw only component" is
                        # the default -- meaning that we should hide the cc
                        # size rank selection elements by default.
                        className=css_config.CC_SELECTOR_ELES_CLASSES + (" hidden" if not multiple_ccs else ""),
                    ),
                    html.Div(
                        [
                            dcc.Input(
                                type="text",
                                id="ccNodeNameSelector",
                                className="form-control",
                                placeholder="Node name",
                            ),
                        ],
                        id="ccNodeNameSelectorEles",
                        # The select-cc-by-node-name stuff is always hidden at
                        # first, since the default cc selection option is
                        # either "by size rank" or "only cc".
                        className=css_config.CC_SELECTOR_ELES_CLASSES
                        + " hidden",
                    ),
                    html.Div(
                        [
                            dcc.Checklist(
                                # the first arg lists the options,
                                # the second arg lists the ones that are
                                # by default selected
                                ["Show patterns"],
                                ["Show patterns"],
                            ),
                        ],
                        className="form-check",
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
                        className="btn btn-light drawCtrl",
                        type="button",
                    ),
                    ctrl_sep,
                    # html.H4("Selected"),
                ],
                id="controls",
                style={
                    "position": "absolute",
                    "top": "0em",
                    "bottom": "0em",
                    "left": "0em",
                    "width": css_config.CONTROLS_WIDTH,
                    "text-align": "center",
                    # only show the scrollbar when needed - firefox doesn't
                    # seem to need this, but chrome does
                    "overflow-y": "auto",
                    "z-index": "1",
                    "background-color": "#123",
                    "color": "#ccc",
                    "border-right": f"{css_config.CONTROLS_BORDER_THICKNESS} solid #002",
                    "transition": f"left {css_config.CONTROLS_TRANSITION_DURATION}",
                },
                className="",
            ),
            # cy
            html.Div(
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
                                                    f"{ag.seq_noun.title()} sequence lengths",
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
                                                                            str(
                                                                                len(
                                                                                    ag.components
                                                                                )
                                                                            ),
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
                                                        html.Img(
                                                            id="ccHistContainer",
                                                            className="centered-img",
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
                                                    html.Img(
                                                        id="seqLenHistContainer",
                                                        className="centered-img",
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
            # toast messages will go here. you can change top-0 to bottom-0 to
            # position these in the bottom right of the window; see
            # https://getbootstrap.com/docs/5.3/components/toasts/#live-example
            html.Div(
                id="toastHolder",
                className="toast-container position-fixed top-0 end-0 p-3",
            ),
        ],
    )

    if multiple_ccs:

        @callback(
            Output("ccHistContainer", "src"),
            Input("ccTab", "n_clicks"),
            prevent_initial_call=True,
        )
        def plot_cc_hist(n_clicks):
            cc_sizes = []
            for cc in ag.components:
                cc_sizes.append(cc.num_total_nodes)
            if len(cc_sizes) < 1:
                raise WeirdError(
                    "How are you going to have a graph with 0 ccs???"
                )
            elif len(cc_sizes) == 1:
                return f"hey fyi this is just 1 cc with {cc_sizes[0]:,} nodes"
            # encode a static matplotlib image: https://stackoverflow.com/a/56932297
            # and https://matplotlib.org/stable/gallery/user_interfaces/web_application_server_sgskip.html
            with pyplot.style.context("ggplot"):
                fig, axes = pyplot.subplots(2, 1)
                fig.suptitle(
                    "Nodes per component",
                    fontsize=18,
                )
                axes[0].hist(
                    cc_sizes,
                    color="#0a0",
                    edgecolor="#030",
                    lw=1,
                )
                axes[1].hist(
                    cc_sizes,
                    bins=range(0, 51, 1),
                    color="#0a0",
                    edgecolor="#030",
                    lw=1,
                )
                ui_utils.use_thousands_sep(axes[0].xaxis)
                ui_utils.use_thousands_sep(axes[0].yaxis)
                # i know we shouldn't need a thousands sep when the bottom plot's
                # x-axis limit is at 50, but maybe we'll change that in the future
                ui_utils.use_thousands_sep(axes[1].xaxis)
                ui_utils.use_thousands_sep(axes[1].yaxis)
                axes[0].set_title("All components")
                axes[1].set_title(
                    "Just components with < 50 nodes (bin size: 1)"
                )
                fig.text(
                    0.07,
                    0.42,
                    "# components",
                    rotation=90,
                    fontsize=13,
                    color="#666",
                )
                axes[1].set_xlabel("# nodes in a component")
                fig.set_size_inches(10, 8)
                buf = BytesIO()
                fig.savefig(buf, format="png", bbox_inches="tight")
                data = base64.b64encode(buf.getbuffer()).decode("ascii")
                buf.close()
            pyplot.close()
            return f"data:image/png;base64,{data}"

    @callback(
        Output("seqLenHistContainer", "src"),
        Input("seqLenTab", "n_clicks"),
        prevent_initial_call=True,
    )
    def plot_seqlen_hist(n_clicks):
        with pyplot.style.context("ggplot"):
            fig, axes = pyplot.subplots(2, 1)
            fig.suptitle(
                f"{ag.seq_noun.title()} sequence lengths", fontsize=18
            )
            axes[0].hist(
                ag.seq_lengths,
                color="#700",
                edgecolor="#100",
                lw=1,
            )
            axes[1].hist(
                ag.seq_lengths,
                bins=range(0, 10001, 100),
                color="#700",
                edgecolor="#100",
                lw=1,
            )
            ui_utils.use_thousands_sep(axes[0].xaxis)
            ui_utils.use_thousands_sep(axes[0].yaxis)
            ui_utils.use_thousands_sep(axes[1].xaxis)
            ui_utils.use_thousands_sep(axes[1].yaxis)
            axes[0].set_title(f"All {ag.seq_noun}s")
            axes[1].set_title(
                f"Just {ag.seq_noun}s with lengths < 10 kbp (bin size: 100 bp)"
            )
            fig.text(
                0.07,
                0.45,
                f"# {ag.seq_noun}s",
                rotation=90,
                fontsize=13,
                color="#666",
            )
            axes[1].set_xlabel("Length (bp)")
            fig.set_size_inches(10, 8)
            buf = BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight")
            data = base64.b64encode(buf.getbuffer()).decode("ascii")
            buf.close()
        pyplot.close()
        return f"data:image/png;base64,{data}"

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
        Input("ccDrawingNodeName", "n_clicks"),
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
                css_config.CC_SELECTOR_ELES_CLASSES + " hidden"
            )
        elif ctx.triggered_id == "ccDrawingNodeName":
            cc_sr_eles_classes = (
                css_config.CC_SELECTOR_ELES_CLASSES + " hidden"
            )
            cc_nn_eles_classes = css_config.CC_SELECTOR_ELES_CLASSES
        else:
            # draw all components, so hide both size rank and node name eles
            cc_sr_eles_classes = (
                css_config.CC_SELECTOR_ELES_CLASSES + " hidden"
            )
            cc_nn_eles_classes = (
                css_config.CC_SELECTOR_ELES_CLASSES + " hidden"
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
        allow_duplicate=True,
    )
    def update_cc_size_rank(size_rank, decr_n_clicks, incr_n_clicks):
        if size_rank is None:
            return 1
        if ctx.triggered_id == "ccSizeRankDecrBtn":
            if type(size_rank) is not int:
                return max(math.floor(size_rank), 1)
            if size_rank <= 1:
                return 1
            elif size_rank > len(ag.components):
                return len(ag.components)
            else:
                return size_rank - 1
        else:
            if type(size_rank) is not int:
                return min(math.ceil(size_rank), len(ag.components))
            if size_rank < 1:
                return 1
            elif size_rank >= len(ag.components):
                return len(ag.components)
            else:
                return size_rank + 1

    @callback(
        Output("toastHolder", "children"),
        Output("cyDiv", "children"),
        State("toastHolder", "children"),
        State("cyDiv", "children"),
        State("ccDrawingSelect", "value"),
        State("ccSizeRankSelector", "value"),
        State("ccNodeNameSelector", "value"),
        Input("drawButton", "n_clicks"),
        prevent_initial_call=True,
    )
    def draw(
        curr_toasts,
        curr_cy,
        cc_drawing_selection_type,
        size_rank,
        node_name,
        n_clicks,
    ):
        ag_selection_params = {}

        if cc_drawing_selection_type == "ccDrawingSizeRank":
            # Invalid numbers (with respect to any set min / max values) will
            # be passed here as None, which is nice but does make it tough to
            # distinguish btwn "the <input> is empty" and "the user entered a
            # bad number". Anyway we just handle both cases with the same
            # message.
            #
            # (Note that floats may end up here, because I deliberately did not
            # set step=1 on the size rank selector. This allows the -/+ buttons
            # to actually see the current value and do intelligent rounding in
            # the update_cc_size_rank() callback.)
            if type(size_rank) is not int:
                return (
                    ui_utils.add_error_toast(
                        curr_toasts,
                        "Draw Error",
                        ui_utils.get_cc_size_rank_error_msg(ag),
                    ),
                    curr_cy,
                )
            ag_selection_params = {"cc_size_rank": size_rank}

        elif cc_drawing_selection_type == "ccDrawingNodeName":
            # looks like not typing in the node name field at all results
            # in node_name being None. However, if we type something in and
            # then fully delete it, then node_name becomes "". Eesh!
            if node_name is None or node_name == "":
                return (
                    ui_utils.add_error_toast(
                        curr_toasts, "Draw Error", "No node name specified."
                    ),
                    curr_cy,
                )
            ag_selection_params = {"cc_node_name": node_name}

        # if something goes wrong during drawing, propagate the result to
        # a toast message in the browser without changing the cytoscape div
        try:
            elements = ag.to_cyjs_elements(**ag_selection_params)
        except UIError as err:
            return (
                ui_utils.add_error_toast(curr_toasts, "Draw Error", str(err)),
                curr_cy,
            )

        # TODO store info in AsmGraph? about which ccs have been laid out.
        # For now, we can assume that the scaling stuff is not configurable,
        # so there is only a binary of "laid out" or "not laid out". Set up
        # UI elements in the viz to - like before - let user select one cc,
        # all ccs, or cc containing a given node to lay out. These will update
        # the layout status for either 1 or all ccs. Then, here, when we go
        # to draw some portion of the graph, we can figure out what parts of
        # layout we may have to redo if necessary. Eventually we can add
        # progress bars here or something to the viz but for now nbd
        # if not ag.layout_done:
        #     ag.layout()
        return curr_toasts, cyto.Cytoscape(
            id="cy",
            elements=elements,
            layout={"name": "cose"},
            style={
                "width": "100%",
                "height": "100%",
            },
            boxSelectionEnabled=True,
            maxZoom=9,
            stylesheet=[
                {
                    "selector": "node",
                    "style": {
                        "background-color": cy_config.NODE_COLOR,
                        "color": cy_config.UNSELECTED_NODE_FONT_COLOR,
                        "label": "data(label)",
                        "text-valign": "center",
                        "min-zoomed-font-size": "12",
                        "z-index": "2",
                    },
                },
                {
                    "selector": "node:selected",
                    "style": {
                        "color": cy_config.SELECTED_NODE_FONT_COLOR,
                        "background-blacken": cy_config.SELECTED_NODE_BLACKEN,
                    },
                },
                {
                    "selector": "node.fwd",
                    "style": {
                        "shape": "polygon",
                        "shape-polygon-points": cy_config.FWD_NODE_POLYGON_PTS,
                    },
                },
                {
                    "selector": "node.rev",
                    "style": {
                        "shape": "polygon",
                        "shape-polygon-points": cy_config.REV_NODE_POLYGON_PTS,
                    },
                },
                {
                    "selector": "node.unoriented",
                    "style": {
                        "shape": cy_config.UNORIENTED_NODE_SHAPE,
                    },
                },
            ],
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

    app.run(debug=True)
