from . import config


def get_gv_header(graphname="thing"):
    gv_input = "digraph " + graphname + "{\n"
    if config.GRAPH_STYLE != "":
        gv_input += "\t{};\n".format(config.GRAPH_STYLE)
    if config.GLOBALNODE_STYLE != "":
        gv_input += "\tnode [{}];\n".format(config.GLOBALNODE_STYLE)
    if config.GLOBALEDGE_STYLE != "":
        gv_input += "\tedge [{}];\n".format(config.GLOBALEDGE_STYLE)
    return gv_input
