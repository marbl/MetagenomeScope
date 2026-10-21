import dash_bootstrap_components as dbc
from dash import html, dcc
from .. import chart_utils, ui_utils, ui_config, css_config


def get_overview_tab(ag):
    return html.Div(
        [
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
                        html.I(
                            className="bi bi-file-earmark-spreadsheet-fill"
                        ),
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
    )


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
    inner_tabs = [
        dbc.Tab(
            get_cc_treemap_tab(ag),
            label="Treemap of nodes",
            tab_id="graphInfoCCTreemapTab",
        ),
        dbc.Tab(
            get_cc_hist_tab(),
            label="Histograms of nodes / edges",
            tab_id="graphInfoCCHistTab",
        ),
        dbc.Tab(
            get_cc_covlen_tab(),
            label="Length \u00d7 Coverage",
            tab_id="graphInfoCCCovLenTab",
        ),
    ]
    return dbc.Tabs(inner_tabs, id="graphInfoModalCCTabs")


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
    # Creates the outer layer of the modal dialog. Note that some tabs will
    # not be shown, depending on the input graph (e.g. if the graph has only 1
    # component then we'll hide the "Components" tab and the stuff within it)
    inner_tabs = [
        dbc.Tab(
            get_overview_tab(ag),
            label="Overview",
            tab_id="graphInfoOverviewTab",
        ),
    ]
    if ag.multiple_ccs:
        inner_tabs.append(
            dbc.Tab(
                get_components_tab(ag),
                label="Components",
                tab_id="graphInfoComponentsTab",
            )
        )
    inner_tabs.append(
        dbc.Tab(
            get_lengths_tab(),
            label="Lengths",
            tab_id="graphInfoLengthsTab",
        )
    )
    if ag.has_covs:
        inner_tabs.append(
            dbc.Tab(
                get_coverages_tab(),
                label="Coverages",
                tab_id="graphInfoCoveragesTab",
            )
        )
        if ag.has_covlens:
            inner_tabs.append(
                dbc.Tab(
                    get_covlen_eles_tab(),
                    label=f"Length \u00d7 Coverage ({ag.cov_source}s)",
                    tab_id="graphInfoCovLenElesTab",
                )
            )
    return [
        dbc.Tabs(inner_tabs, id="graphInfoModalTabs"),
        # invisible buttons used to trigger callbacks
        html.Div(
            [
                html.Button(id="gim_cc_TreemapButton"),
                html.Button(id="gim_cc_HistButton"),
                html.Button(id="gim_cc_CovLenScatterButton"),
                html.Button(id="gim_len_HistButton"),
                html.Button(id="gim_cov_HistButton"),
                html.Button(id="gim_covlenele_ScatterButton"),
            ],
            className="removedEntirely",
        ),
    ]
