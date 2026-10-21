import dash_bootstrap_components as dbc
from dash import html
from .. import aln_config


def get_modal_body(ag, aligner=aln_config.MINIMAP2):
    fspan = html.Span(ag.fasta_basename, className="font-monospace")
    return html.Div(
        [
            html.H5("Input sequence(s)"),
            html.P(
                [
                    "Here, you can specify the sequence(s) to search for in ",
                    "the graph (i.e. in the ",
                    fspan,
                    " file you provided).",
                ],
            ),
            html.P("Your input here should be in FASTA format."),
            html.P(
                "Note that this functionality requires that you have "
                f"{aligner} installed and available in your PATH!"
            ),
            dbc.Textarea(
                size="md",
                placeholder="FASTA of sequence(s) to search for in the graph",
                style={"min-height": "15em"},
                className="font-monospace",
                spellcheck=False,
                id="seqSearchInput",
            ),
            html.Div(
                [
                    html.Span(
                        "(No results yet.)",
                        className="font-monospace",
                        id="seqSearchStatus",
                        style={
                            "margin-right": "1em",
                            "vertical-align": "middle",
                        },
                    ),
                    html.Button(
                        [
                            html.I(className="bi bi-shuffle"),
                            html.Span(
                                "Map graph sequences to these sequences",
                                className="iconlbl",
                            ),
                        ],
                        id="seqSearchRunButton",
                        className="btn btn-success",
                        type="button",
                    ),
                ],
                style={
                    "text-align": "right",
                    "margin-top": "1em",
                    "margin-bottom": "1em",
                },
            ),
            html.H5(
                [
                    "Results: input sequences, and the sequences in ",
                    fspan,
                    " that mapped to them",
                ],
            ),
            html.Div(
                html.P(
                    "super secret placeholder text :)", style={"color": "#fff"}
                ),
                id="seqSearchResults",
                className="font-monospace",
            ),
        ]
    )


def get_results_html(inseq2graphseqs):
    paras = []
    if len(inseq2graphseqs) > 0:
        # TODO would be nice to match the ordering in the input FASTA
        for s in sorted(inseq2graphseqs):
            paras.append(
                html.P(
                    [
                        html.Span(f"{s}:", style={"font-weight": "bold"}),
                        " ",
                        ", ".join(inseq2graphseqs[s]),
                    ]
                )
            )
    else:
        paras.append(
            html.P(
                "No sequences in the graph mapped to any of the input "
                "sequence(s).",
                style={"font-weight": "bold"},
            )
        )
    return paras
