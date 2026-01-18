from dash import html
from . import ui_config
from .errors import WeirdError


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
            "Edges"
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
