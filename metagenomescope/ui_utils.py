from dash import html
from . import css_config
from .misc_utils import fmt_qty


def get_length_info(ag):
    return html.Table(
        html.Tbody(
            [
                html.Tr(
                    [
                        html.Th(f"Total {ag.seq_noun} sequence length"),
                        html.Th(f"N50 of {ag.seq_noun} sequence lengths"),
                    ]
                ),
                html.Tr(
                    [
                        html.Td(fmt_qty(ag.total_seq_len)),
                        html.Td(fmt_qty(ag.n50)),
                    ]
                ),
            ]
        ),
        className=css_config.INFO_DIALOG_TABLE_CLASSES,
    )
