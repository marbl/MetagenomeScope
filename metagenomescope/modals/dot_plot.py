import dash_bootstrap_components as dbc
from dash import html
from .. import ui_config, chart_utils


def get_dot_plot_seq_ui(seq_num):
    idprefix = f"dp{seq_num}"
    axis = chart_utils.get_dot_plot_axis(seq_num)
    title = f"{axis}-axis"
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        # H5 elements mess up the styling a bit due to
                        # margins and junk so just kinda imitate this.
                        # not ideallll but sufficient
                        html.Span(title, style={"font-size": "1.25rem"}),
                        width=6,
                    ),
                    dbc.Col(
                        html.Div(
                            dbc.RadioItems(
                                options=[
                                    {
                                        "label": "Node(s)",
                                        "value": ui_config.GRAPH_SEQ,
                                    },
                                    {
                                        "label": "Specify below",
                                        "value": ui_config.OTHER_SEQ,
                                    },
                                ],
                                value=ui_config.GRAPH_SEQ,
                                className="btn-group",
                                inputClassName="btn-check",
                                labelClassName="btn btn-sm btn-outline-dark",
                                labelCheckedClassName="active",
                                id=f"{idprefix}SeqType",
                            ),
                            className="btn-opt-group",
                            style={"text-align": "right"},
                        ),
                        width=6,
                    ),
                ],
                style={"margin-bottom": "0.5em"},
            ),
            html.Div(
                dbc.InputGroup(
                    [
                        dbc.InputGroupText("Node name(s)"),
                        dbc.Input(
                            type="text",
                            id=f"{idprefix}GraphSeq",
                        ),
                    ],
                    size="sm",
                ),
                id=f"{idprefix}GraphSeqUI",
            ),
            html.Div(
                dbc.Textarea(
                    size="sm",
                    placeholder="Single sequence (just A/C/G/Ts)",
                    style={"min-height": "10em"},
                    className="font-monospace",
                    spellcheck=False,
                    id=f"{idprefix}OtherSeq",
                ),
                id=f"{idprefix}OtherSeqUI",
                className="removedEntirely",
            ),
        ],
        style={
            "margin-bottom": "1em",
        },
    )


def get_modal_body():
    return html.Div(
        [
            html.Div(
                (
                    "This interface is designed for comparing sequences "
                    "up to ~10 Mbp each. It may struggle for longer sequences."
                ),
                className="modal-topnote",
            ),
            # https://www.dash-bootstrap-components.com/docs/components/layout/
            # basically the two dbc.Cols should add up to a total width of 12
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Div(
                                dbc.Button(
                                    [
                                        html.I(
                                            className="bi bi-arrow-return-right"
                                        ),
                                        html.Span(
                                            "Autofill from one or two selected nodes",
                                            className="iconlbl",
                                        ),
                                    ],
                                    id="dotPlotAutoButton",
                                    color="success",
                                    style={"margin-bottom": "1em"},
                                ),
                                style={"text-align": "center"},
                            ),
                            get_dot_plot_seq_ui(1),
                            get_dot_plot_seq_ui(2),
                            html.H5("Parameters"),
                            dbc.InputGroup(
                                [
                                    dbc.InputGroupText(
                                        ui_config.KMER_TEXT,
                                        className="input-group-text-next-to-radio-button-group",
                                    ),
                                    html.Div(
                                        dbc.RadioItems(
                                            options=[
                                                {
                                                    "label": "Autoselect",
                                                    "value": ui_config.K_AUTO,
                                                },
                                                {
                                                    "label": [
                                                        html.Span(
                                                            "Specify manually",
                                                            style={
                                                                "padding-right": "0.7em"
                                                            },
                                                        ),
                                                        html.I(
                                                            className="bi bi-arrow-right jank-icon-in-label",
                                                            style={
                                                                "-webkit-text-stroke": "0.5px",
                                                            },
                                                        ),
                                                    ],
                                                    "value": ui_config.K_MANUAL,
                                                },
                                            ],
                                            value=ui_config.K_AUTO,
                                            className="btn-group",
                                            inputClassName="btn-check",
                                            labelClassName="btn btn-sm btn-outline-dark",
                                            labelCheckedClassName="active",
                                            id="dotPlotKType",
                                        ),
                                        className="btn-opt-group",
                                    ),
                                    dbc.Input(
                                        type="text",
                                        id="dotPlotK",
                                        value=ui_config.K_DEFAULT,
                                        className="short-num-input input-group-text-next-to-radio-button-group",
                                    ),
                                ],
                                size="sm",
                            ),
                            ui_config.OPTIONS_SEP,
                            dbc.InputGroup(
                                [
                                    dbc.InputGroupText(
                                        "Marker size",
                                        className="input-group-text-next-to-radio-button-group",
                                    ),
                                    html.Div(
                                        dbc.RadioItems(
                                            options=[
                                                {
                                                    "label": "Autoselect",
                                                    "value": ui_config.MARKERSIZE_AUTO,
                                                },
                                                {
                                                    "label": [
                                                        html.Span(
                                                            "Specify manually",
                                                            style={
                                                                "padding-right": "0.7em"
                                                            },
                                                        ),
                                                        html.I(
                                                            className="bi bi-arrow-right jank-icon-in-label",
                                                            style={
                                                                "-webkit-text-stroke": "0.5px",
                                                            },
                                                        ),
                                                    ],
                                                    "value": ui_config.MARKERSIZE_MANUAL,
                                                },
                                            ],
                                            value=ui_config.MARKERSIZE_AUTO,
                                            className="btn-group",
                                            inputClassName="btn-check",
                                            labelClassName="btn btn-sm btn-outline-dark",
                                            labelCheckedClassName="active",
                                            id="dotPlotMarkerSizeType",
                                        ),
                                        className="btn-opt-group",
                                    ),
                                    dbc.Input(
                                        type="text",
                                        id="dotPlotMarkerSize",
                                        value=ui_config.MARKERSIZE_DEFAULT,
                                        className="short-num-input input-group-text-next-to-radio-button-group",
                                    ),
                                ],
                                size="sm",
                            ),
                            ui_config.OPTIONS_SEP,
                            dbc.InputGroup(
                                [
                                    dbc.InputGroupText(
                                        "Space between plots",
                                    ),
                                    dbc.Input(
                                        type="text",
                                        id="dotPlotSpace",
                                        value=ui_config.SPACE_DEFAULT,
                                        className="short-num-input",
                                    ),
                                ],
                                size="sm",
                            ),
                            html.Div(
                                id="dotPlotParameterNotes",
                                style={"margin-top": "1em"},
                            ),
                        ],
                        width=5,
                    ),
                    dbc.Col(
                        html.Img(id="dotPlotImg"),
                        style={"text-align": "center"},
                        width=7,
                    ),
                ]
            ),
            html.Div(
                [
                    html.Span(
                        "(No plot has been drawn yet.)",
                        className="font-monospace",
                        id="dotPlotStatus",
                        style={
                            "margin-right": "1em",
                            "vertical-align": "middle",
                        },
                    ),
                    html.Button(
                        [
                            html.I(className="bi bi-pencil-fill"),
                            html.Span(
                                "Draw dot plot",
                                className="iconlbl",
                            ),
                        ],
                        id="dotPlotRunButton",
                        className="btn btn-success",
                        type="button",
                    ),
                ],
                style={"text-align": "right"},
            ),
        ]
    )
