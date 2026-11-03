import dash_bootstrap_components as dbc
from dash import html, dcc
from .. import chart_utils, ui_utils, ui_config, css_config


def get_pane_id(tab_id):
    return f"{tab_id}Pane"


def get_nav(title, tab_id, selected=False):
    btn_classes = "nav-link"
    if selected:
        btn_classes += " active"
    pane_id = get_pane_id(tab_id)
    return html.Li(
        html.Button(
            title,
            className=btn_classes,
            id=tab_id,
            type="button",
            role="tab",
            **{
                "data-bs-toggle": "tab",
                "data-bs-target": f"#{pane_id}",
                "aria-controls": pane_id,
                "aria-selected": "true" if selected else "false",
            },
        ),
        className="nav-item",
        role="presentation",
    )


def get_pane(content, tab_id, selected=False):
    classes = "tab-pane fade"
    if selected:
        classes += " show active"
    return html.Div(
        content,
        className=classes,
        id=get_pane_id(tab_id),
        role="tabpanel",
        tabIndex="0",
        **{"aria-labelledby": tab_id},
    )


def get_tabs(navs, panes):
    """Returns Dash HTML elements representing a Bootstrap tabbed UI.

    Parameters
    ----------
    navs: list of Dash html elements
        Should be a list where each entry was produced by get_nav(). These
        correspond to the "headers" you can click on to switch between panes.

    panes: list of Dash html elements
        Should be a list where each entry was produced by get_pane(). These
        correspond to the "bodies" that contain the actual content you are
        switching between.

    Returns
    -------
    list of Dash html elements
        As of writing, this will contain two things: a html.Ul element
        wrapping the navs, and a html.Div element wrapping the panes.

    Notes
    -----
    So, okay, ideally we would use dbc.Tabs to structure this nicely.
    This is implemented in commit 95aafe6e7ac559e6bd772eaa07a7160d6b10c8c7.
    However, Dash's tabs become super slow when there are a lot of them (?)
    so for now I am just going back to the old approach based on
    https://getbootstrap.com/docs/5.3/components/navs-tabs/#javascript-behavior

    This approach involves splitting up navs (the buttons at the top) and the
    actual content that clicking on these navs opens. We just say "navs" and
    "panes" here, I guess.
    """
    return [
        html.Ul(navs, className="nav nav-tabs", role="tablist"),
        html.Div(panes, className="tab-content"),
    ]


def get_overview_tab_content(ag):
    return [
        html.Table(
            html.Tbody(
                [
                    html.Tr(
                        [
                            html.Th("Filename"),
                            html.Th(
                                "Filetype",
                            ),
                            html.Th("# nodes"),
                            html.Th("# edges"),
                            html.Th("# components"),
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
                            html.Td(f"{len(ag.components):,}"),
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
                    ag.seq_noun + "s",
                    className="fw-bold",
                ),
                ".",
            ]
        ),
        ui_utils.get_approx_length_disclaimer_if_needed(ag),
        ui_utils.get_length_info(ag),
        *ui_utils.get_cov_info(ag),
        *ui_utils.get_patt_info(ag),
        html.Div(
            dbc.Button(
                [
                    html.I(className="bi bi-file-earmark-spreadsheet-fill"),
                    html.Span(
                        "Save node, edge and pattern counts per component (TSV)",
                        className="iconlbl",
                    ),
                ],
                id="tsvButton",
                color="success",
                # it looks like google sheets :3
                # ^^^ things a fundamentally unwell person (me) would say
                outline=True,
            ),
            style={"text-align": "center"},
        ),
    ]


def get_cc_treemap_tab(ag):
    return html.Div(
        [
            html.Div(id="ccTreemapContainer"),
            chart_utils.get_treemap_options(ag),
        ]
    )


def get_cc_hist_tab():
    return html.Div(
        [
            html.Div(id="ccHistContainer"),
            chart_utils.get_node_edge_toggle("ccHistEleType"),
            ui_config.OPTIONS_SEP,
            chart_utils.get_hist_options(
                "ccHistNumBins",
                "ccHistNumBinsApply",
                "ccHistMaxX",
                "ccHistMaxXApply",
                "ccHistYScale",
            ),
        ]
    )


def get_cc_covlen_tab():
    return html.Div(
        [
            html.Div(
                dcc.Graph(
                    id="covlenCCScatterGraph",
                    mathjax=True,
                    # This SORT OF prevents a flash of
                    # unstyled content -- it at least does
                    # a better job than display: none, which
                    # always results in an awkward scatterplot
                    # that is like some fraction of the modal
                    # width and visibly takes a moment to get
                    # auto-resized to the correct width. using
                    # this makes it so that more often the plot
                    # just pops into existence perfectly like it
                    # did before we made the dcc.Graph() persistent.
                    #
                    # see https://community.plotly.com/t/30631
                    # re: visibility hidden
                    style={
                        "height": "0",
                        "visibility": "hidden",
                    },
                ),
                id="covlenCCScatterContainer",
            ),
            chart_utils.get_scatterplot_options(
                "covlenCCScatterXScale",
                "covlenCCScatterYScale",
            ),
            html.Div(
                id="covlenCCScatterMissingInfo",
            ),
            html.Div(
                [
                    dcc.Clipboard(
                        target_id="covlenCCSelectedNums",
                        title="Copy to clipboard",
                        # without inline-block, this spans
                        # a whole row and looks gross.
                        # https://dash.plotly.com/dash-core-components/clipboard
                        # Also! If the clipboard API is not available (see those
                        # Dash docs), then the clipboard icon will not be shown.
                        # I am not sure EXACTLY what that looks like but -- if it
                        # will be entirely removed from the app layout -- then I
                        # think it makes sense to give the margin to the clipboard
                        # icon rather than the text, since if the clipboard icon is
                        # hidden we have no use for the margin.
                        style={
                            "display": "inline-block",
                            "margin-right": "0.6em",
                        },
                    ),
                    html.Span(
                        ui_config.NO_COMPONENTS_SELECTED_MSG,
                        id="covlenCCSelectedNums",
                    ),
                ],
                style={
                    "background-color": "#f3f3f3",
                    "border": "1px solid #666",
                    "padding": "0.3em",
                },
            ),
        ],
    )


def get_components_tab(ag):
    navs = [
        get_nav("Treemap of nodes", "graphInfoCCTreemapTab", selected=True),
        get_nav("Histograms of nodes / edges", "graphInfoCCHistTab"),
        get_nav("Length \u00d7 Coverage", "graphInfoCCCovLenTab"),
    ]
    panes = [
        get_pane(
            get_cc_treemap_tab(ag), "graphInfoCCTreemapTab", selected=True
        ),
        get_pane(get_cc_hist_tab(), "graphInfoCCHistTab"),
        get_pane(get_cc_covlen_tab(), "graphInfoCCCovLenTab"),
    ]
    return get_tabs(navs, panes)


def get_lengths_tab():
    return html.Div(
        [
            html.Div(id="seqLenHistContainer"),
            chart_utils.get_hist_options(
                "seqLenHistNumBins",
                "seqLenHistNumBinsApply",
                "seqLenHistMaxX",
                "seqLenHistMaxXApply",
                "seqLenHistYScale",
            ),
        ],
    )


def get_coverages_tab():
    return html.Div(
        [
            html.Div(id="covHistContainer"),
            chart_utils.get_hist_options(
                "covHistNumBins",
                "covHistNumBinsApply",
                "covHistMaxX",
                "covHistMaxXApply",
                "covHistYScale",
            ),
            ui_config.OPTIONS_SEP,
            html.Div(id="covHistMissingInfo"),
        ],
    )


def get_covlen_eles_tab():
    return html.Div(
        [
            html.Div(id="covlenEleScatterContainer"),
            chart_utils.get_scatterplot_options(
                "covlenEleScatterXScale",
                "covlenEleScatterYScale",
            ),
            html.Div(id="covlenEleScatterMissingInfo"),
        ],
    )


def get_modal_body(ag):
    """Creates the body of the graph info modal dialog.

    This will hide some parts of the dialog depending on the input graph. For
    example, if the graph only consists of one component, then we'll hide the
    "Components" tab and the stuff within it.

    Parameters
    ----------
    ag: metagenomescope.graph.AssemblyGraph

    Returns
    -------
    list of Dash html elements or whatever
        (i'm sure there is a formal way to specify this return type but also:
        i don't really think it matters atp)
    """
    # Mark the overview nav as selected because it's the first one
    navs = [get_nav("Overview", "infoStatsTab", selected=True)]
    panes = [
        get_pane(get_overview_tab_content(ag), "infoStatsTab", selected=True)
    ]

    if ag.multiple_ccs:
        navs.append(get_nav("Components", "infoCCTab"))
        panes.append(get_pane(get_components_tab(ag), "infoCCTab"))

    navs.append(get_nav("Lengths", "infoLengthsTab"))
    panes.append(get_pane(get_lengths_tab(), "infoLengthsTab"))

    if ag.has_covs:
        navs.append(get_nav("Coverages", "infoCoveragesTab"))
        panes.append(get_pane(get_coverages_tab(), "infoCoveragesTab"))

        if ag.has_covlens:
            navs.append(
                get_nav(
                    f"Length \u00d7 Coverage ({ag.cov_source}s)",
                    "infoCovLenElesTab",
                )
            )
            panes.append(get_pane(get_covlen_eles_tab(), "infoCovLenElesTab"))

    return get_tabs(navs, panes)


def get_modal(ag):
    # https://getbootstrap.com/docs/5.3/components/modal/#live-demo
    return html.Div(
        html.Div(
            html.Div(
                [
                    html.Div(
                        [
                            html.H1(
                                [
                                    html.I(className="bi bi-grid-1x2-fill"),
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
                        get_modal_body(ag),
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
    )
