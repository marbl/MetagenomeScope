import dash_bootstrap_components as dbc
from dash import html
from .. import ui_utils, css_config


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


def get_components_tab(ag):
    inner_tabs = [
        dbc.Tab(
            label="Treemap of nodes",
        ),
        dbc.Tab(
            label="Histograms of nodes / edges",
        ),
        dbc.Tab(
            label="Length \u00d7 Coverage",
        ),
    ]
    return dbc.Tabs(inner_tabs)


def get_modal_body(ag):
    # TODO don't incl components tab if not multi ccs
    return dbc.Tabs(
        [
            dbc.Tab(
                get_overview_tab(ag),
                label="Overview",
            ),
            dbc.Tab(
                get_components_tab(ag),
                label="Components",
            ),
            dbc.Tab(
                label="Lengths",
            ),
            dbc.Tab(
                label="Coverages",
            ),
        ]
    )
