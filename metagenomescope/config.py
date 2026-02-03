###############################################################################
# Miscellaneous settings
###############################################################################

# used when figuring out if we should just round a float to an int
# i did not choose this value for an intelligent reason; i just kinda eyeballed
# it. if this causes problems feel free to adjust
EPSILON = 0.000001

# Node orientations
FWD = "+"
REV = "-"
NOR = None

# Used to create lines in logging output like =====
SEPBIG = "="
SEPSML = "-"

# Used as the suffixes of split nodes.
SPLIT_SEP = "-"
SPLIT_LEFT = "L"
SPLIT_RIGHT = "R"
SPLIT_LEFT_SUFFIX = SPLIT_SEP + SPLIT_LEFT
SPLIT_RIGHT_SUFFIX = SPLIT_SEP + SPLIT_RIGHT

# This is mostly all configurable, but the JS callbacks for searching/etc
# rely on these being "-L" and "-R". That could be made more elegant by like
# passing the suffixes to the function but that seems not worth it
# Also, name_utils.get_splitname_base() assumes that these both have a length
# of 2. seriously don't change these lol
if SPLIT_LEFT_SUFFIX != "-L" or SPLIT_RIGHT_SUFFIX != "-R":
    raise ValueError(
        "Hey, you can't change that without updating the JS searching code."
    )

# Pattern types -- used internally.
PT_BUBBLE = 0
PT_CHAIN = 1
PT_CYCLICCHAIN = 2
PT_FRAYEDROPE = 3
PT_BIPARTITE = 4

# Maps pattern types to human-readable names.
PT2HR = {
    PT_BUBBLE: "Bubble",
    PT_CHAIN: "Chain",
    PT_CYCLICCHAIN: "Cyclic Chain",
    PT_FRAYEDROPE: "Frayed Rope",
    PT_BIPARTITE: "Bipartite",
}

# Maps pattern types to human-readable names without spaces. For those silly
# cases where we want to include pattern names in other IDs (e.g. in the names
# of clusters in exported DOT files)...
PT2HR_NOSPACE = {
    PT_BUBBLE: "bubble",
    PT_CHAIN: "chain",
    PT_CYCLICCHAIN: "cyclicchain",
    PT_FRAYEDROPE: "frayedrope",
    PT_BIPARTITE: "bipartite",
}

# colors for patterns, in both the Cy.js interface and in DOT outputs
# most of these were based on graphviz colors, but like the original cy.js
# styling made patterns semitransparent, so these really match graphviz colors
# at some semitransparency on a white background. history!
PT2COLOR = {
    # matches "cornflowerblue" in graphviz
    PT_BUBBLE: "#9abaf3",
    # matches "green2" in graphviz
    PT_FRAYEDROPE: "#59f459",
    # this one used to match "salmon" in graphviz (#fcaca3 i think?) and then i
    # changed it to be less flashy since there are a lot of chains involved
    # in hierarchical decomp stuff and i want people to take this seriously
    PT_CHAIN: "#eedddd",
    # matches "darkgoldenrod1" in graphviz
    PT_CYCLICCHAIN: "#ffd163",
    PT_BIPARTITE: "#c8a4ed",
}

# Whether or not to automatically flatten (i.e. reduce to basic Bezier style
# edges in Cy.js) child edges of a pattern. Note that this is "child," not
# "descendant" -- we just look at the immediate parent of a pattern in making
# this decision.
#
# Note that patterns marked with False can still have their child edges
# flattened for other reasons - this is just like, "of course if an edge is a
# child of a bipartite it should be a straight line."
#
# This is fairly conservative - I think a case could be made for flattening
# child edges of ALL patterns.
PT2FLATTEN_CHILD_EDGES = {
    # Bubbles can MAYBE have complex edge routes that benefit from fancy lines
    PT_BUBBLE: False,
    # Consider aug1 cc2. Sometimes the straight edge approach means an edge
    # passes through a corner of a really big node that "protrudes".
    PT_FRAYEDROPE: False,
    # these should already all be straight lines ._.
    PT_CHAIN: True,
    # Cyclic chains can MAYBE have fancy back edges. For 2-node cyclic chains
    # the other flattening code should already flatten the forward and back
    # edges
    PT_CYCLICCHAIN: False,
    # Bipartites are essentially always clearer with straight lines IMO
    # Consider aug1 cc6. with squiggly lines the bipartites look confusing
    PT_BIPARTITE: True,
}

# Draw types. Used internally for communicating between flush() and draw().
DRAW_ALL = "all"
DRAW_CCS = "ccs"
DRAW_AROUND = "around"

# Optional ID fields, used sometimes in the JSON output of draw() (aka
# "currDrawnInfo")
CDI_DRAWN_NODE_IDS = "drawn_node_ids"
CDI_DRAWN_EDGE_IDS = "drawn_edge_ids"

# Some context on port numbers, for anyone who stumbles upon this in the future
# (including future me):
#
# - ModDotPlot, another bio tool that is set up as a Dash app, does not
#   explicitly set a min/max port number --
#   https://github.com/marbl/ModDotPlot/blob/d7675f99536df74b95efcca56e20b09bf42e432d/src/moddotplot/moddotplot.py#L144-L149
#
# - Dash itself requires that the port is an int in the range [1, 65535] --
#   https://github.com/plotly/dash/blob/30afe785c26c2bb6f4dc56efd0c9001d4384acfc/dash/dash.py#L2428
#
# - https://linux.die.net/man/5/services says that 'Port numbers below 1024
#   (so-called "low numbered" ports) can only be bound to by root'.
#
# - https://en.wikipedia.org/wiki/List_of_TCP_and_UDP_port_numbers lists a
#   bunch of stuff about port numbers, and is how I ran into the "services" man
#   page cited above.
#
# - If you try running dash with a port number of 1023, my system complains
#   about not having permission. However, using a port number of 1024 works!
#
# So ... this all seems to suggest to me that a minimum of >= 1024 should be
# okay. And I guess we should impose a maximum of 65535 in order to
# "fail fast," rather than waiting for Dash to throw the error (after we
# spend a bunch of time processing the graph).
#
# I am sure this will not be perfect but it doesn't have to be -- this is
# gonna have to be up to the user to figure out if they don't want to use 8050
# (or whatever the default is).
MIN_PORT = 1024
MAX_PORT = 65535
