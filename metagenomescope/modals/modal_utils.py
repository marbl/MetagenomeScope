from dash import html


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


def get_modal(modal_body, title, bi_icon, modal_id):
    """Returns Dash HTML element representing a modal dialog.

    For some reason, doing the modal "manually" (without just using dbc.Modal)
    makes opening up the modal faster. I don't know why. But I don't have time
    to question that in detail.

    References
    ----------
    This is just mimicking what is done at
    https://getbootstrap.com/docs/5.3/components/modal/#live-demo
    """
    label_id = f"{modal_id}Label"
    return html.Div(
        html.Div(
            html.Div(
                [
                    html.Div(
                        [
                            html.H1(
                                [
                                    html.I(className=f"bi {bi_icon}"),
                                    html.Span(title, className="iconlbl"),
                                ],
                                className="modal-title fs-5",
                                id=label_id,
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
                    html.Div(modal_body, className="modal-body"),
                ],
                className="modal-content",
            ),
            className="modal-dialog modal-xl",
        ),
        id=modal_id,
        className="modal fade",
        # additional accessibility things from bootstrap examples that
        # may not be necessary for a visualization tool like this atm
        **{
            "aria-hidden": "true",
            "aria-labelledby": label_id,
            "tabIndex": "-1",
        },
    )
