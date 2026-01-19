from dash import html
from . import ui_config
from .errors import WeirdError
import dash_bootstrap_components as dbc


def get_eqn_parts(node_centric):
    if node_centric:
        n = "n"
        objs = "Nodes"
    else:
        n = "e"
        objs = "Edges"
    return n, objs


def get_total_length_latex(node_centric, incl_dollarsigns=True):
    n, objs = get_eqn_parts(node_centric)
    lenaxislatex_inner = (
        r"\sum_{"
        f"{n} "
        r"\in \text{"
        f"{objs}"
        r"}}\text{Length}("
        f"{n}"
        r")"
    )
    if incl_dollarsigns:
        return "$" + lenaxislatex_inner + "$"
    else:
        return lenaxislatex_inner


def get_weightedavg_cov_latex(node_centric, cov_field):
    n, objs = get_eqn_parts(node_centric)
    coverage = ui_config.COVATTR2TITLE[cov_field]
    totallen = get_total_length_latex(node_centric, False)
    return (
        r"$\dfrac{"
        r"\sum_{"
        f"{n} "
        r"\in \text{"
        f"{objs}"
        r"}} "
        r"\text{"
        f"{coverage}"
        r"}("
        f"{n}"
        r") \times \text{Length}("
        f"{n}"
        r")}{"
        f"{totallen}"
        r"}$"
    )


def get_unweightedavg_cov_latex(node_centric, cov_field):
    # assumes node centric, i.e. nodes have lengths and (if we are resorting
    # to not weighting covs in this plot) that edges have covs
    if not node_centric:
        raise WeirdError("we don't support this yet")
    else:
        coverage = ui_config.COVATTR2TITLE[cov_field]
        return (
            r"$\dfrac{"
            r"\sum_{"
            "e "
            r"\in \text{"
            "Edges"
            r"}} "
            r"\text{"
            f"{coverage}"
            r"}("
            "e"
            r")}{|"
            r"\text{Edges}"
            r"|}$"
        )


def get_plot_missing_data_msg(num, den, noun, reason):
    if num > 0:
        # now THIS is obsessive compulsive disorder
        if num == 1:
            s = ""
            are = "is"
        else:
            s = "s"
            are = "are"
        mpct = 100 * (num / den)
        missing_info = [
            html.Span(
                f"{num:,} / {den:,} ({mpct:.2f}%) {noun}{s}",
                className="fw-bold",
            ),
            f" {are} omitted from this plot due to {reason}.",
        ]
    else:
        missing_info = None
    return missing_info


def prettify_go_fig(fig):
    """Adjusts a plotly.graph_objects figure to make it a bit nicer.

    ...at least for our purposes, and in my opinion.
    """
    fig.update_layout(
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


def get_num_bins_option(val_id, btn_id):
    return dbc.InputGroup(
        [
            dbc.InputGroupText(
                "Maximum # bins", className="input-group-text-next-to-button"
            ),
            dbc.Input(
                placeholder="# bins", id=val_id, style={"max-width": "10em"}
            ),
            dbc.Button("Apply", id=btn_id, color="dark"),
        ],
        size="sm",
    )


def get_scale_options(html_obj_id, desc):
    return dbc.InputGroup(
        [
            dbc.InputGroupText(
                desc, className="input-group-text-next-to-button"
            ),
            html.Div(
                dbc.RadioItems(
                    options=[
                        {
                            "label": "Linear",
                            "value": "linear",
                        },
                        {
                            "label": "Logarithmic",
                            "value": "log",
                        },
                    ],
                    value="linear",
                    className="btn-group",
                    inputClassName="btn-check",
                    labelClassName="btn btn-sm btn-outline-dark",
                    labelCheckedClassName="active",
                    id=html_obj_id,
                ),
                className="btn-opt-group",
            ),
        ],
        size="sm",
    )


def get_hist_options(nbins_id, nbins_btn_id, y_scale_id):
    return html.Div(
        [
            get_num_bins_option(nbins_id, nbins_btn_id),
            html.Div(style={"margin-top": "0.3em"}),
            get_scale_options(y_scale_id, "y-axis scale"),
        ],
    )
