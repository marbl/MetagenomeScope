from . import cy_config, ui_config


def get_cyjs_stylesheet(
    node_coloring=ui_config.DEFAULT_NODE_COLORING,
    edge_coloring=ui_config.DEFAULT_EDGE_COLORING,
):
    stylesheet = [
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
            "selector": "edge",
            "style": {
                "curve-style": "bezier",
                "target-arrow-shape": "triangle",
                "line-color": cy_config.EDGE_COLOR,
                "target-arrow-color": cy_config.EDGE_COLOR,
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
        {
            "selector": "node.pattern",
            "style": {
                "shape": "rectangle",
                "border-width": "0",
                "border-color": "#000000",
                "padding-top": "0",
                "padding-right": "0",
                "padding-left": "0",
                "padding-bottom": "0",
            },
        },
        {
            "selector": "node.bubble",
            "style": {
                "background-color": cy_config.BUBBLE_COLOR,
            },
        },
        {
            "selector": "node.frayedrope",
            "style": {
                "background-color": cy_config.FRAYEDROPE_COLOR,
            },
        },
        {
            "selector": "node.chain",
            "style": {
                "background-color": cy_config.CHAIN_COLOR,
            },
        },
        {
            "selector": "node.cyclicchain",
            "style": {
                "background-color": cy_config.CYCLICCHAIN_COLOR,
            },
        },
    ]

    if node_coloring == ui_config.COLORING_RANDOM:
        for i, c in enumerate(cy_config.RANDOM_COLORS):
            stylesheet.append(
                {
                    "selector": f"node.noderand{i}",
                    "style": {
                        "background-color": c,
                    },
                }
            )
    # yeah yeah yeah this is slightly inefficient if both nodes and edges have
    # random coloring because then we're iterating through
    # cy_config.RANDOM_COLORS twice instead of once. there is no way that will
    # ever be a bottleneck.
    if edge_coloring == ui_config.COLORING_RANDOM:
        for i, c in enumerate(cy_config.RANDOM_COLORS):
            stylesheet.append(
                {
                    "selector": f"edge.edgerand{i}",
                    "style": {
                        "line-color": c,
                        "target-arrow-color": c,
                    },
                }
            )

    # Apply a unique color to selected edges. Do this last so it takes
    # precedence over even random edge colorings.
    stylesheet.append(
        {
            "selector": "edge:selected",
            "style": {
                "line-color": cy_config.SELECTED_EDGE_COLOR,
                "target-arrow-color": cy_config.SELECTED_EDGE_COLOR,
            },
        }
    )
    return stylesheet
