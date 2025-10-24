/* Copyright (C) 2016-- Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
 * Authored by Marcus Fedarko
 *
 * This file is part of MetagenomeScope.
 *
 * MetagenomeScope is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * MetagenomeScope is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with MetagenomeScope.  If not, see <http://www.gnu.org/licenses/>.
 ****
 * The functions in this code file provide the various features/etc. in
 * MetagenomeScope's viewer interface web application.
 * This is the primary JavaScript code file for MetagenomeScope.
 */

// We use the mgsc variable as a namespace to hold global variables in
// MetagenomeScope's JavaScript code.
// CODELINK: This practice for JS adapted from Matt Kruse's "Javascript Toolbox"
// at http://www.javascripttoolbox.com/bestpractices/#namespace
var mgsc = {};
// Cytoscape.js graph instance
var cy = null;

// Various coordinates that are used to define polygon node shapes in
// Cytoscape.js (see their documentation for the format specs of these
// coordinates).
// The suffix indicates the directionality for which the polygon should be
// used. LEFTRIGHT means that the polygon should be used for either the default
// direction (LEFT, ->) or its opposite (RIGHT, <-); UPDOWN has similar
// meaning.
mgsc.FRAYED_ROPE_LEFTRIGHTDIR = "-1 -1 0 -0.5 1 -1 1 1 0 0.5 -1 1";
mgsc.FRAYED_ROPE_UPDOWNDIR = "1 -1 0.5 0 1 1 -1 1 -0.5 0 -1 -1";
mgsc.BUBBLE_LEFTRIGHTDIR = "-1 0 -0.5 -1 0.5 -1 1 0 0.5 1 -0.5 1";
mgsc.BUBBLE_UPDOWNDIR = "-1 -0.5 0 -1 1 -0.5 1 0.5 0 1 -1 0.5";
mgsc.NODE_LEFTDIR = "1 1 -0.23587 1 -1 0 -0.23587 -1 1 -1";
mgsc.NODE_RIGHTDIR = "-1 1 0.23587 1 1 0 0.23587 -1 -1 -1";
mgsc.NODE_UPDIR = "-1 1 -1 -0.23587 0 -1 1 -0.23587 1 1";
mgsc.NODE_DOWNDIR = "-1 -1 -1 0.23587 0 1 1 0.23587 1 -1";

// Approximate conversion factor from inches (the unit used by GraphViz for
// node width/height measurements) to pixels. TODO, we might want to
// consider node size more closely to see how accurate we can get it?
// Also -- maybe multiply coordinates by this, to get things worked out?
// 72 ppi?
mgsc.INCHES_TO_PIXELS = 54;

// Misc. global variables we use to get certain functionality
// The current "view type" -- will always be one of {"SPQR", "double"}
mgsc.CURR_VIEWTYPE = undefined;
// The current "SPQR mode" -- will always be one of {"implicit", explicit"}
mgsc.CURR_SPQRMODE = undefined;
// mapping of {bicomponent ID => an array of the IDs of the visible singlenodes
// in that bicomponent}
mgsc.BICOMPONENTID2VISIBLESINGLENODEIDS = {};
// The bounding box of the graph
mgsc.CURR_BOUNDINGBOX = undefined;
// In degrees CCW from the default up->down direction
mgsc.PREV_ROTATION = undefined;
mgsc.CURR_ROTATION = undefined;
// The current colorization "value" -- used to prevent redundant applications
// of changing colorization.
mgsc.CURR_NODE_COLORIZATION = null;
// Objects containing the RGB data for the maximum/minimum color in
// colorization schemes, respectively. We precompute these values and store
// them in these variables in initGraph(). This avoids making 2|V| calls to
// .toRGB() (i.e. getting these values in util.getNodeColorization()) when just 2
// calls would suffice.
mgsc.MAX_RGB = undefined;
mgsc.MIN_RGB = undefined;
// The hex string colors for mgsc.MAX_RGB and mgsc.MIN_RGB.
mgsc.MAX_HEX = undefined;
mgsc.MIN_HEX = undefined;
// The default node color in the current colorization settings. Used when
// colorizing nodes that have no repeat data (but other nodes do have repeat
// data).
mgsc.DEFAULT_NODE_COLOR = undefined;
// The default colorization settings.
// Used for the "reset color settings to defaults" button.
// NOTE -- If the default color settings are updated, this can also be updated
// relatively easily by just loading the viewer interface, exporting the
// default settings manually, and then modifying the resulting file to replace
// newlines and tabs with their repsective control character representations
// (this can be done via the commands :%s/\n/\\n/g and :%s/\t/\\t/g in Vim).
// Ideally this process would be automated, but there have been some issues
// with that (see issue #263 on the old GitHub page, fedarko/MetagenomeScope,
// for a bit of a summary).
mgsc.DEFAULT_COLOR_SETTINGS =
    "mincncp\t#0022ff\nmaxcncp\t#ff2200\ncnlcp\t#aaaaaa\ncsnlcp\t#aaaaaa\nusncp\t#888888\nsncp\t#444444\nbubblecp\t#9abaf3\nfropecp\t#59f459\nchaincp\t#fcaca3\nychaincp\t#ffd163\nspqrscp\t#ffd644\nspqrpcp\t#eb8ef9\nspqrrcp\t#31bf6f\nbicmpcp\t#e9e9e9\ntnbcp\t#ff6600\ntngbcp\t#ff6600\nmiscpatterncp\t#c398eb\nusnlcp\t#000000\nsnlcp\t#aaaaaa\nusecp\t#555555\nsecp\t#111111\nhoecp\t#ff0000\nhosecp\t#800000\nloecp\t#0000ff\nlosecp\t#000080\ncngcccp\t#000000\nsngbcp\t#000000\ncpcp\t#994700\nbgcp\t#ffffff\n";
// The background color of the graph. Set in initGraph().
mgsc.BG_COLOR = undefined;
// Booleans for whether or not to use certain performance options
mgsc.HIDE_EDGES_ON_VIEWPORT = false;
mgsc.TEXTURE_ON_VIEWPORT = false;
// Array of edge weights in current connected component. Used when drawing a
// histogram of edge weights.
mgsc.COMPONENT_EDGE_WEIGHTS = [];
// A reference to the current SQL.Database object from which we obtain the
// graph's layout and biological data
mgsc.CURR_DB = null;
// Filetype of the assembly; used for determining bp vs. nt for nodes
mgsc.ASM_FILETYPE = undefined;
// Whether or not actual DNA sequences were provided to the preprocessing
// script (impacts the availability of GC content display and colorization)
mgsc.DNA_AVAILABLE = undefined;
// Whether or not repeat data was provided in the input to the preprocessing
// script (impacts the availability of repeat colorization)
mgsc.REPEAT_INFO_AVAILABLE = undefined;
// Whether or not SPQR mode data exists in the .db file (should only be true if
// the -spqr option was passed to the preprocessing script, or if the .db file
// predates the -spqr option)
mgsc.SPQR_INFO_AVAILABLE = undefined;
// Filename of the currently loaded .db file
mgsc.DB_FILENAME = undefined;
// Total number of nodes and edges in the current asm graph
mgsc.ASM_NODE_COUNT = 0;
mgsc.ASM_EDGE_COUNT = 0;
mgsc.CURR_NE = 0;
// How often (e.g. after how many nodes/half-edges) we update the progress
// bar with its new value. Will be set in drawComponent() for the current
// component being drawn, taking into account mgsc.PROGRESSBAR_FREQ_PERCENT.
// Higher values of this mean less timeouts are used to update the
// progress bar, which means the graph is loaded somewhat faster,
// while smaller values of this mean more timeouts are used (i.e.
// slower graph loading) but choppier progress bar progress occurs.
mgsc.PROGRESSBAR_FREQ = undefined;
// mgsc.PROGRESSBAR_FREQ = Math.floor(mgsc.PROGRESSBAR_FREQ_PERCENT * SIZE), where
// SIZE = (number of nodes to be drawn) + 0.5*(number of edges to be drawn)
mgsc.PROGRESSBAR_FREQ_PERCENT = 0.05;
// Valid protocol schemes under which we can use cross-origin requests (and
// thereby load demo .db files).
mgsc.CORS_PROTOCOL_SCHEMES = ["http:", "https:"];
// Potentially set to true during doThingsWhenDOMReady().
// If this is true, we can load demo .db files and the demoing button should be
// enabled; if not, we can't (and the demoing button should remain disabled).
mgsc.DEMOS_SUPPORTED = false;
// Numbers of selected elements, and collections of those selected elements.
mgsc.SELECTED_NODE_COUNT = 0;
mgsc.SELECTED_EDGE_COUNT = 0;
mgsc.SELECTED_CLUSTER_COUNT = 0;
mgsc.SELECTED_NODES = null;
mgsc.SELECTED_EDGES = null;
mgsc.SELECTED_CLUSTERS = null;
// Collection of removed edges (due to a minimum bundle size threshold).
mgsc.REMOVED_EDGES = null;
mgsc.PREV_EDGE_WEIGHT_THRESHOLD = null;
// Mapping of scaffold ID to labels or IDs (should depend on the assembly
// filetype, but really can refer to anything in mgsc.COMPONENT_NODE_KEYS) of the
// nodes contained within the scaffold, as an array.
// Used when highlighting nodes contained within a scaffold.
mgsc.SCAFFOLDID2NODEKEYS = {};
// Array of scaffolds in the current connected component, in the order they
// were listed in the input AGP file. Used when cycling through scaffolds.
mgsc.COMPONENT_SCAFFOLDS = [];
// Current index of the drawScaffoldButton in mgsc.COMPONENT_SCAFFOLDS. Used when
// cycling through scaffolds.
mgsc.SCAFFOLD_CYCLER_CURR_INDEX = 0;
// Used to indicate whether or not the current component has scaffolds added
// from the AGP file -- this, in turn, is used to determine what text to
// display to the user in the "View Scaffolds" area.
mgsc.COMPONENT_HAS_SCAFFOLDS = false;
// "Keys" referring to nodes in the currently-drawn connected component.
// Used in determining which scaffolds are in the current connected component.
mgsc.COMPONENT_NODE_KEYS = [];
// Flag indicating whether or not the application is in "finishing mode," in
// which the user can select nodes to manually construct a path through the
// assembly.
mgsc.FINISHING_MODE_ON = false;
// Flag indicating whether or not a previous finishing process was performed.
mgsc.FINISHING_MODE_PREVIOUSLY_DONE = false;
// String of the node IDs (in order -- the first node ID is the first ID in the
// reconstructed sequence, and so on) that are part of the constructed path.
// In the format "N1,N2,N3,N4" where N1 is the first node ID, N2 is the second
// node ID, and so on (allowing repeat duplicate IDs).
mgsc.FINISHING_NODE_IDS = "";
// Like mgsc.FINISHING_NODE_IDS, but each element in this list is the actual
// Cytoscape.js object for the corresponding node in the path
mgsc.FINISHING_NODE_OBJS = [];
// Nodes that are outgoing from the last-added node to the reconstructed path.
mgsc.NEXT_NODES = undefined;
// Maximum zoom level used in the graph display. Used in order to prevent the
// user from "getting lost" (i.e. zooming too far in). Another max zoom level
// is configurable for the user in the animation settings; that zoom level
// tries to ensure that the user has some context around tentative nodes during
// the finishing process (see issue #110 on GitHub for details).
mgsc.MAX_ZOOM_ORDINARY = 9;
// List of mappings of cluster ID to "top" attribute
// (corresponds to left position in graph)
mgsc.CLUSTERID2TOP = [];
// Current "position" of cluster in the graph (so 0 is the leftmost cluster, 1
// is the second-from-the-leftmost cluster, and so on). As the user moves along
// clusters in the graph with the arrow keys, this value is
// incremented/decremented accordingly.
mgsc.CLUSTER_X = -1;
// Whether or not to allow keyboard navigation through clusters in std. mode
mgsc.USE_CLUSTER_KBD_NAV = false;
// Indicates if any Bootstrap modal dialogs are active. If so, we ignore
// keyboard inputs for cluster navigation until the dialog in question is
// closed.
mgsc.MODAL_ACTIVE = false;
// Indicates if any input fields outside of modal dialogs (i.e. usable
// alongside the graph functionality of the viewer interface) are focused on.
// If so, we ignore keyboard inputs until the input in question is un-focused.
mgsc.INPUT_ACTIVE = false;

// Current search type (configurable in the dropdown menu in the "Search for
// Nodes" section). The value of this corresponds to what's shown in the
// contents of the #searchTypeButton <button> -- hence the capitalization
// (e.g. "Label"), as opposed to that in mgsc.SEARCH_TYPE_HREADABLE (e.g. "label").
mgsc.CURR_SEARCH_TYPE = "ID";
// Mapping of the search type to something in the middle of a sentence (allows
// us to frivolously adjust capitalization so we can be picky about it)
mgsc.SEARCH_TYPE_HREADABLE = { ID: "ID", Label: "label" };

// HTML snippets used while auto-creating info tables about selected elements
mgsc.TD_CLOSE = "</td>";
mgsc.TD_START = "<td>";
// Regular expression we use when matching integers.
mgsc.INTEGER_RE = /^\d+$/;

// Initializes the Cytoscape.js graph instance.
// Takes as argument the "view type" of the graph to be drawn (see top of file
// defn. of mgsc.CURR_VIEWTYPE for details).
function initGraph(viewType) {
    mgsc.CURR_VIEWTYPE = viewType;
    // mgsc.MAX_RGB and mgsc.MIN_RGB will only be computed if they haven't been set
    // already (i.e. if the user hasn't changed the default colors and hasn't
    // drawn any connected components yet).
    // We take this approach (instead of just giving mgsc.MAX_RGB and mgsc.MIN_RGB their
    // default values here) in order to reduce redundancy, to thus make
    // changing the default values easier in the future (only have to change
    // the HTML, instead of both HTML and JS).
    var tmpColor;
    if (mgsc.MAX_RGB === undefined) {
        tmpColor = $("#maxcncp").data("colorpicker").color;
        mgsc.MAX_RGB = tmpColor.toRGB();
        mgsc.MAX_HEX = tmpColor.toHex();
    }
    if (mgsc.MIN_RGB === undefined) {
        tmpColor = $("#mincncp").data("colorpicker").color;
        mgsc.MIN_RGB = tmpColor.toRGB();
        mgsc.MIN_HEX = tmpColor.toHex();
    }
    mgsc.BG_COLOR = $("#bgcp").colorpicker("getValue");
    mgsc.DEFAULT_NODE_COLOR = $("#usncp").colorpicker("getValue");
    $("#cy").css("background", mgsc.BG_COLOR);
    cy = cytoscape({
        container: document.getElementById("cy"),
        layout: {
            // We parse GraphViz' generated xdot files to copy the layout
            // provided by GraphViz. To manually specify node positions, we
            // use the "preset" Cytoscape.js layout.
            name: "preset",
        },
        // We set minZoom based on the zoom level obtained by cy.fit().
        // maxZoom, however, is defined based on the zoom level of zooming to
        // fit around a single node -- which usually has an upper bound of 9 or
        // so, based on some tests. (Hence why we just set maxZoom here.)
        maxZoom: mgsc.MAX_ZOOM_ORDINARY,
        // Setting the pixelRatio to 1.0 can yield (slight) performance
        // improvements, according to the Cytoscape.js docs
        // (http://js.cytoscape.org/#core/initialisation).
        //
        // UPDATE: I'm commenting this out for the time being since, at least
        // from my experience testing the viewer interface out on a "high
        // density display," the performance improvements aren't very
        // noticeable and the visualization looks notably blurrier than on
        // other devices (the latter of which is to be expected). The docs
        // mention that use of this option is "much less necessary on recent
        // browser releases," so it should be ok to do this.
        //
        //pixelRatio: 1.0,
        hideEdgesOnViewport: mgsc.HIDE_EDGES_ON_VIEWPORT,
        textureOnViewport: mgsc.TEXTURE_ON_VIEWPORT,
        // options we use to prevent user from messing with the graph before
        // it's been fully drawn
        userPanningEnabled: false,
        userZoomingEnabled: false,
        boxSelectionEnabled: false,
        autounselectify: true,
        autoungrabify: true,
        style: [
            {
                selector: "node",
                style: {
                    width: "data(w)",
                    height: "data(h)",
                },
            },
            // The following few classes are used to set properties of
            // compound nodes (analogous to clusters in GraphViz)
            {
                selector: "node.cluster",
                style: {
                    shape: "rectangle",
                    "border-width": 0,
                },
            },
            {
                selector: "node.cluster.spqrMetanode",
                style: {
                    "background-opacity": 0.65,
                },
            },
            {
                selector: "node.cluster.structuralPattern",
                style: {
                    "padding-top": 0,
                    "padding-right": 0,
                    "padding-left": 0,
                    "padding-bottom": 0,
                    width: "data(w)",
                    height: "data(h)",
                },
            },
            {
                // Give collapsed variants a number indicating child count
                selector: "node.cluster.structuralPattern[?isCollapsed]",
                style: {
                    "min-zoomed-font-size": 12,
                    "font-size": 48,
                    label: "data(interiorNodeCount)",
                    "text-valign": "center",
                    "font-weight": "bold",
                    color: $("#cngcccp").colorpicker("getValue"),
                },
            },
            {
                selector: "node.F",
                style: {
                    // default color matches 'green2' in graphviz
                    // (but honestly I just picked what I considered to be
                    // the least visually offensive shade of green)
                    "background-color": $("#fropecp").colorpicker("getValue"),
                    shape: "polygon",
                },
            },
            {
                selector: "node.B",
                style: {
                    // default color matches 'cornflowerblue' in graphviz
                    "background-color": $("#bubblecp").colorpicker("getValue"),
                    shape: "polygon",
                },
            },
            {
                selector: "node.B.leftrightdir",
                style: {
                    "shape-polygon-points": mgsc.BUBBLE_LEFTRIGHTDIR,
                },
            },
            {
                selector: "node.B.updowndir",
                style: {
                    "shape-polygon-points": mgsc.BUBBLE_UPDOWNDIR,
                },
            },
            {
                selector: "node.F.leftrightdir",
                style: {
                    "shape-polygon-points": mgsc.FRAYED_ROPE_LEFTRIGHTDIR,
                },
            },
            {
                selector: "node.F.updowndir",
                style: {
                    "shape-polygon-points": mgsc.FRAYED_ROPE_UPDOWNDIR,
                },
            },
            {
                selector: "node.C",
                style: {
                    // default color matches 'salmon' in graphviz
                    "background-color": $("#chaincp").colorpicker("getValue"),
                },
            },
            {
                selector: "node.Y",
                style: {
                    // default color matches 'darkgoldenrod1' in graphviz
                    "background-color": $("#ychaincp").colorpicker("getValue"),
                    shape: "ellipse",
                },
            },
            {
                selector: "node.M",
                style: {
                    "background-color": $("#miscpatterncp").colorpicker(
                        "getValue"
                    ),
                },
            },
            {
                selector: "node.cluster.pseudoparent",
                style: {
                    "z-index-compare": "manual",
                    "z-index": 0,
                },
            },
            {
                selector: "node.I",
                style: {
                    "background-color": $("#bicmpcp").colorpicker("getValue"),
                },
            },
            {
                selector: "node.S",
                style: {
                    "background-color": $("#spqrscp").colorpicker("getValue"),
                },
            },
            {
                selector: "node.P",
                style: {
                    "background-color": $("#spqrpcp").colorpicker("getValue"),
                },
            },
            {
                selector: "node.R",
                style: {
                    "background-color": $("#spqrrcp").colorpicker("getValue"),
                },
            },
            {
                selector: "node.bb_enforcing",
                style: {
                    // Make these nodes invisible
                    "background-opacity": 0,
                    // A width/height of zero just results in Cytoscape.js not
                    // drawing these nodes -- hence a width/height of one
                    width: 1,
                    height: 1,
                },
            },
            {
                selector: "node.noncluster",
                style: {
                    label: "data(label)",
                    "text-valign": "center",
                    // rendering text is computationally expensive, so if
                    // we're zoomed out so much that the text would be
                    // illegible (or hard-to-read, at least) then don't
                    // render the text.
                    "min-zoomed-font-size": 12,
                    "z-index": 2,
                    "z-index-compare": "manual",
                },
            },
            {
                // Used for individual nodes in a SPQR-integrated view
                // (these nodes lack orientation, so they're drawn as just
                // rectangles)
                selector: "node.noncluster.singlenode",
                style: {
                    shape: "rectangle",
                },
            },
            {
                selector: "node.noncluster.noncolorized",
                style: {
                    "background-color": mgsc.DEFAULT_NODE_COLOR,
                    color: $("#usnlcp").colorpicker("getValue"),
                },
            },
            {
                selector: "node.noncluster.gccolorized",
                style: {
                    "background-color": "data(gc_color)",
                    color: $("#cnlcp").colorpicker("getValue"),
                },
            },
            {
                selector: "node.noncluster.repeatcolorized",
                style: {
                    "background-color": "data(repeat_color)",
                    color: $("#cnlcp").colorpicker("getValue"),
                },
            },
            {
                selector: "node.noncluster.updir",
                style: {
                    "shape-polygon-points": mgsc.NODE_UPDIR,
                    shape: "polygon",
                },
            },
            {
                selector: "node.noncluster.downdir",
                style: {
                    "shape-polygon-points": mgsc.NODE_DOWNDIR,
                    shape: "polygon",
                },
            },
            {
                selector: "node.noncluster.leftdir",
                style: {
                    "shape-polygon-points": mgsc.NODE_LEFTDIR,
                    shape: "polygon",
                },
            },
            {
                selector: "node.noncluster.rightdir",
                style: {
                    "shape-polygon-points": mgsc.NODE_RIGHTDIR,
                    shape: "polygon",
                },
            },
            {
                selector: "node.noncluster.tentative",
                style: {
                    "border-width": 5,
                    "border-color": $("#tnbcp").colorpicker("getValue"),
                },
            },
            {
                selector: "node.cluster.tentative",
                style: {
                    "border-width": 5,
                    "border-color": $("#tngbcp").colorpicker("getValue"),
                },
            },
            {
                selector: "node.currpath",
                style: {
                    "background-color": $("#cpcp").colorpicker("getValue"),
                },
            },
            {
                selector: "node.noncluster:selected",
                style: {
                    "background-color": $("#sncp").colorpicker("getValue"),
                },
            },
            {
                selector: "node.noncluster.noncolorized:selected",
                style: {
                    color: $("#snlcp").colorpicker("getValue"),
                },
            },
            {
                selector: "node.noncluster.gccolorized:selected",
                style: {
                    color: $("#csnlcp").colorpicker("getValue"),
                },
            },
            {
                selector: "node.cluster:selected",
                style: {
                    "border-width": 5,
                    "border-color": $("#sngbcp").colorpicker("getValue"),
                },
            },
            {
                selector: "edge",
                style: {
                    width: "data(thickness)",
                    "line-color": $("#usecp").colorpicker("getValue"),
                    "target-arrow-color": $("#usecp").colorpicker("getValue"),
                    "loop-direction": "30deg",
                    "z-index": 1,
                    "z-index-compare": "manual",
                },
            },
            {
                selector: "edge:selected",
                style: {
                    "line-color": $("#secp").colorpicker("getValue"),
                    "target-arrow-color": $("#secp").colorpicker("getValue"),
                },
            },
            {
                selector: "edge.oriented",
                style: {
                    "target-arrow-shape": "triangle",
                    "target-endpoint": "-50% 0%",
                    "source-endpoint": "50% 0",
                },
            },
            {
                selector: "edge:loop",
                style: {
                    "z-index": 5,
                },
            },
            {
                selector: "edge.unoriented_loop",
                style: {
                    "target-endpoint": "-50% 0%",
                    "source-endpoint": "50% 0",
                },
            },
            {
                // Used for edges that were assigned valid (i.e. not
                // just a straight line or self-directed edge)
                // cpd/cpw properties from the xdot file.
                selector: "edge.unbundledbezier",
                style: {
                    "curve-style": "unbundled-bezier",
                    "control-point-distances": "data(cpd)",
                    "control-point-weights": "data(cpw)",
                    "edge-distances": "node-position",
                },
            },
            {
                // Used for:
                //  -Self-directed edges
                //  -Lines that are determined upon parsing the xdot file to
                //   be sufficiently close to a straight line
                //  -Temporary edges, for which we have no control point
                //   data (i.e. any edges directly from/to compound nodes
                //   during the collapsing process)
                selector: "edge.basicbezier",
                style: {
                    "curve-style": "bezier",
                },
            },
            {
                selector: "edge.virtual",
                style: {
                    "line-style": "dashed",
                },
            },
            {
                selector: "edge.high_outlier",
                style: {
                    "line-color": $("#hoecp").colorpicker("getValue"),
                    "target-arrow-color": $("#hoecp").colorpicker("getValue"),
                },
            },
            {
                selector: "edge.high_outlier:selected",
                style: {
                    "line-color": $("#hosecp").colorpicker("getValue"),
                    "target-arrow-color": $("#hosecp").colorpicker("getValue"),
                },
            },
            {
                selector: "edge.low_outlier",
                style: {
                    "line-color": $("#loecp").colorpicker("getValue"),
                    "target-arrow-color": $("#loecp").colorpicker("getValue"),
                },
            },
            {
                selector: "edge.low_outlier:selected",
                style: {
                    "line-color": $("#losecp").colorpicker("getValue"),
                    "target-arrow-color": $("#losecp").colorpicker("getValue"),
                },
            },
            {
                // Used to differentiate edges without an overlap between nodes
                // in graphs where overlap data is given
                // this conflicts with virtual edges' style, so we may want to
                // change this in the future
                // (using "dotted" lines was really slow)
                selector: "edge.nooverlap",
                style: {
                    "line-style": "dashed",
                },
            },
        ],
    });
}

/* Given a cluster, either collapses it (if already uncollapsed) or
 * uncollapses it (if already collapsed).
 */
function toggleCluster(cluster) {
    cy.startBatch();
    if (cluster.data("isCollapsed")) {
        uncollapseCluster(cluster);
    } else {
        collapseCluster(cluster);
    }
    cy.endBatch();
}

/* Collapses a given single cluster, making use of the
 * cluster's actual and canonical exterior edge data.
 *
 * NOTE that this can result in the presence of codirected edges, if a
 * single node connects to multiple edges within the cluster (e.g. a
 * node has two outgoing edges, to both starting nodes of a frayed rope).
 */
function collapseCluster(cluster, moveMap) {
    var children = cluster.children();
    // Prevent this cluster from being collapsed if any of its children are
    // tentative nodes in finishing mode
    if (mgsc.FINISHING_MODE_ON) {
        for (var ci = 0; ci < children.length; ci++) {
            if (children[ci].hasClass("tentative")) {
                return;
            }
        }
    }
    // For each edge with a target in the compound node...
    var oldIncomingEdge;
    for (var incomingEdgeID in cluster.data("incomingEdgeMap")) {
        oldIncomingEdge = cy.getElementById(incomingEdgeID);
        oldIncomingEdge.removeClass("unbundledbezier");
        oldIncomingEdge.addClass("basicbezier");
        oldIncomingEdge.move({ target: cluster.id() });
    }
    // For each edge with a source in the compound node...
    var oldOutgoingEdge;
    for (var outgoingEdgeID in cluster.data("outgoingEdgeMap")) {
        oldOutgoingEdge = cy.getElementById(outgoingEdgeID);
        oldOutgoingEdge.removeClass("unbundledbezier");
        oldOutgoingEdge.addClass("basicbezier");
        oldOutgoingEdge.move({ source: cluster.id() });
    }
    cluster.data("isCollapsed", true);
    // Update list of locally collapsed nodes (useful for global toggling)
    cy.scratch("_collapsed", cy.scratch("_collapsed").union(cluster));
    cy.scratch("_uncollapsed", cy.scratch("_uncollapsed").difference(cluster));
    if (cy.scratch("_uncollapsed").empty()) {
        if ($("#collapseButtonText").text()[0] === "C") {
            changeCollapseButton(true);
        }
    }
    // Unselect the elements before removing them (fixes #158 on GitHub)
    cluster.scratch("_interiorEles").unselect();
    // "Remove" the elements (they can be added back to the graph upon
    // uncollapsing this cluster, of course)
    cluster.scratch("_interiorEles").remove();
}

/* Uncollapses a given single cluster, making use of the cluster's actual
 * and canonical exterior edge data.
 */
function uncollapseCluster(cluster) {
    // Prevent this cluster from being uncollapsed if it's a "tentative" node
    // in finishing mode
    if (mgsc.FINISHING_MODE_ON) {
        if (cluster.hasClass("tentative")) {
            return;
        }
    }
    // Restore child nodes + interior edges
    cluster.scratch("_interiorEles").restore();
    // "Reset" edges to their original target/source within the cluster
    var oldIncomingEdge, newTgt;
    for (var incomingEdgeID in cluster.data("incomingEdgeMap")) {
        if (mgsc.REMOVED_EDGES.is('[id="' + incomingEdgeID + '"]')) {
            // The edge has probably been removed from the graph due to
            // the edge weight thing -- ignore it
            continue;
        }
        newTgt = cluster.data("incomingEdgeMap")[incomingEdgeID][1];
        oldIncomingEdge = cy.getElementById(incomingEdgeID);
        // If the edge isn't connected to another cluster, and the edge
        // wasn't a basicbezier to start off with (i.e. it has control point
        // data), then change its classes to update its style.
        if (
            !oldIncomingEdge.source().hasClass("cluster") &&
            oldIncomingEdge.data("cpd")
        ) {
            if (!oldIncomingEdge.hasClass("reducededge")) {
                oldIncomingEdge.removeClass("basicbezier");
                oldIncomingEdge.addClass("unbundledbezier");
            }
        }
        oldIncomingEdge.move({ target: newTgt });
    }
    var oldOutgoingEdge, newSrc;
    for (var outgoingEdgeID in cluster.data("outgoingEdgeMap")) {
        if (mgsc.REMOVED_EDGES.is('[id="' + outgoingEdgeID + '"]')) {
            continue;
        }
        newSrc = cluster.data("outgoingEdgeMap")[outgoingEdgeID][0];
        oldOutgoingEdge = cy.getElementById(outgoingEdgeID);
        if (
            !oldOutgoingEdge.target().hasClass("cluster") &&
            oldOutgoingEdge.data("cpd")
        ) {
            if (!oldOutgoingEdge.hasClass("reducededge")) {
                oldOutgoingEdge.removeClass("basicbezier");
                oldOutgoingEdge.addClass("unbundledbezier");
            }
        }
        oldOutgoingEdge.move({ source: newSrc });
    }
    // Update local flag for collapsed status (useful for local toggling)
    cluster.data("isCollapsed", false);
    // Update list of locally collapsed nodes (useful for global toggling)
    cy.scratch("_collapsed", cy.scratch("_collapsed").difference(cluster));
    cy.scratch("_uncollapsed", cy.scratch("_uncollapsed").union(cluster));
    if (cy.scratch("_collapsed").empty()) {
        if ($("#collapseButtonText").text()[0] === "U") {
            changeCollapseButton(false);
        }
    }
}

function addSelectedNodeInfo(ele) {
    var lengthEntry = ele.data("length").toLocaleString();
    if (mgsc.ASM_FILETYPE === "GML" || mgsc.CURR_VIEWTYPE === "SPQR") {
        // These are oriented contigs (in a GML file), or they're directionless
        // contigs (in the undirected SPQR view).
        lengthEntry += " bp";
    } else {
        // These are unoriented contigs; each contig represents a piece of DNA,
        // but since the contigs are unoriented we don't know which strand of
        // DNA the contigs arise from. Therefore we represent them as two
        // separate contigs, referred to as +/-.
        lengthEntry += " nt";
    }
    var eleID = ele.id();
    var nodeRowHTML = "<tr class='nonheader' id='row" + eleID + "'><td>";
    // Add node ID here. If we're in the SPQR viewing mode, nodes' IDs are
    // unambiguous, but contain extra info (they're suffixed by the name of
    // their parent metanode, if present). However, there's not really a need
    // to show the user this information, so we truncate the displayed IDs
    // accordingly. (Otherwise, we just show the user the entire node ID.)
    if (mgsc.CURR_VIEWTYPE === "SPQR") {
        nodeRowHTML += eleID.split("_")[0];
    } else {
        nodeRowHTML += eleID;
    }
    nodeRowHTML += mgsc.TD_CLOSE;
    if (mgsc.ASM_FILETYPE === "GML") {
        nodeRowHTML += mgsc.TD_START + ele.data("label") + mgsc.TD_CLOSE;
    }
    nodeRowHTML += mgsc.TD_START + lengthEntry + mgsc.TD_CLOSE;
    if (mgsc.ASM_FILETYPE === "LastGraph" || mgsc.ASM_FILETYPE === "FASTG") {
        // Round to two decimal places
        var depthEntry = Math.round(ele.data("depth") * 100) / 100 + "x";
        nodeRowHTML += mgsc.TD_START + depthEntry + mgsc.TD_CLOSE;
    }
    if (mgsc.DNA_AVAILABLE) {
        // Round to two decimal places
        // we multiply by 10000 because we're really multiplying by 100
        // twice: first to convert to a percentage, then to start the
        // rounding process
        var gcEntry = Math.round(ele.data("gc_content") * 10000) / 100 + "%";
        nodeRowHTML += mgsc.TD_START + gcEntry + mgsc.TD_CLOSE;
    }
    if (mgsc.REPEAT_INFO_AVAILABLE) {
        var is_repeat = ele.data("is_repeat");
        var repeatEntry;
        if (is_repeat === 1) {
            repeatEntry = "True";
        } else if (is_repeat === 0) {
            repeatEntry = "False";
        } else {
            repeatEntry = "N/A";
        }
        nodeRowHTML += mgsc.TD_START + repeatEntry + mgsc.TD_CLOSE;
    }
    nodeRowHTML += "</tr>";
    $("#nodeInfoTable").append(nodeRowHTML);
}

function addSelectedEdgeInfo(ele) {
    // returns an array of two elements: [source node id, target node id]
    var displaySourceID, displayTargetID;
    if (mgsc.CURR_VIEWTYPE === "SPQR" && ele.data("dispsrc") !== undefined) {
        displaySourceID = ele.data("dispsrc");
        displayTargetID = ele.data("disptgt");
    } else {
        //var canonicalSourceAndTargetNode = ele.id().split("->");
        //displaySourceID = canonicalSourceAndTargetNode[0];
        //displayTargetID = canonicalSourceAndTargetNode[1];
        displaySourceID = ele.source().id();
        displayTargetID = ele.target().id();
    }
    var edgeRowHTML =
        "<tr class='nonheader' id='row" +
        ele.id().replace(">", "") +
        "'><td>" +
        displaySourceID +
        "</td><td>" +
        displayTargetID +
        mgsc.TD_CLOSE;
    if (mgsc.ASM_FILETYPE === "GML" || mgsc.ASM_FILETYPE === "LastGraph")
        edgeRowHTML += mgsc.TD_START;
    if (mgsc.CURR_VIEWTYPE !== "SPQR") {
        edgeRowHTML += ele.data("multiplicity");
    } else {
        edgeRowHTML += "N/A";
    }
    edgeRowHTML += mgsc.TD_CLOSE;
    if (mgsc.ASM_FILETYPE === "GML") {
        if (mgsc.CURR_VIEWTYPE === "SPQR") {
            edgeRowHTML += "<td>N/A</td>N/A<td>N/A</td>N/A<td>N/A</td>";
        } else {
            // Round mean and stdev entries both to two decimal places
            // These values are just estimates so this rounding is okay
            var meanEntry = Math.round(ele.data("mean") * 100) / 100;
            var stdevEntry = Math.round(ele.data("stdev") * 100) / 100;
            edgeRowHTML +=
                mgsc.TD_START + ele.data("orientation") + mgsc.TD_CLOSE;
            edgeRowHTML += mgsc.TD_START + meanEntry + mgsc.TD_CLOSE;
            edgeRowHTML += mgsc.TD_START + stdevEntry + mgsc.TD_CLOSE;
        }
    }
    edgeRowHTML += "</tr>";
    $("#edgeInfoTable").append(edgeRowHTML);
}

function addSelectedClusterInfo(ele) {
    var clustID = ele.data("id");
    var clustType;
    switch (clustID[0]) {
        case "C":
            clustType = "Chain";
            break;
        case "Y":
            clustType = "Cyclic Chain";
            break;
        case "B":
            clustType = "Bubble";
            break;
        case "F":
            clustType = "Frayed Rope";
            break;
        case "M":
            clustType = ele.data("cluster_type");
            break;
        case "I":
            clustType = "Bicomponent";
            break;
        case "S":
            clustType = "Series Metanode";
            break;
        case "P":
            clustType = "Parallel Metanode";
            break;
        case "R":
            clustType = "Rigid Metanode";
            break;
        default:
            clustType = "Invalid (error)";
    }
    var clustSize = ele.data("interiorNodeCount");
    $("#clusterInfoTable").append(
        "<tr class='nonheader' id='row" +
            ele.id() +
            "'><td>" +
            clustType +
            "</td><td>" +
            clustSize +
            "</td></tr>"
    );
}

function removeSelectedEleInfo(ele) {
    "use strict";
    // supports edges in old HTML versions, where > isn't allowed but - is
    $("#row" + ele.id().replace(">", "")).remove();
}

/* Sets bindings for certain DOM elements on the page.
 * To be called when the DOM is ready to be manipulated.
 */
function doThingsWhenDOMReady() {
    "use strict";
    /* Enable demo button and remove its explanatory titletext if the viewer
     * interface is being accessed with a protocol scheme that supports
     * cross-origin requests (i.e. XMLHttpRequests, which are how the .db files
     * are loaded to demo them).
     *
     * Loading the viewer interface locally means that the "file:" protocol
     * will be used, and browsers don't support cross-origin requests
     * originating from local protocols like that. So to avoid the user
     * getting frustrated with trying to demo a file and repeatedly getting
     * an error, we just automatically disable the demo button and only
     * enable it if we know cross-origin requests are supported with the
     * current protocol.
     *
     * NOTE we use button transitions (particularly on opacity) to avoid
     * flashing from, e.g., enabled -> disabled -> enabled when reloading
     * the viewer interface using a protocol in mgsc.CORS_PROTOCOL_SCHEMES.
     *
     * Apparently checking if something is "in" an array in Javascript doesn't
     * actually work; "in" works on the array's indices instead of its actual
     * contents. Hence why we iterate based on mgsc.CORS_PROTOCOL_SCHEMES
     * instead of just saying something like
     * "if (windowProtocol in CORS_..._SCHEMES)".
     */
    for (var i = 0; i < mgsc.CORS_PROTOCOL_SCHEMES.length; i++) {
        if (window.location.protocol === mgsc.CORS_PROTOCOL_SCHEMES[i]) {
            $("#xmlFileselectButton").prop("title", "");
            enableButton("xmlFileselectButton");
            mgsc.DEMOS_SUPPORTED = true;
            break;
        }
    }
    // Set various bindings so that pressing the Enter key on some text fields
    // does something (makes certain actions quicker and easier for the user)
    setEnterBinding("searchInput", searchForEles);
    setEnterBinding("layoutInput", testLayout);
    setEnterBinding("componentselector", function () {
        startDrawComponent("double");
    });
    setEnterBinding("SPQRcomponentselector", function () {
        startDrawComponent("SPQR");
    });
    setEnterBinding("binCountInput", drawEdgeWeightHistogram);
    setEnterBinding("cullEdgesInput", cullEdges);
    // Update mgsc.MODAL_ACTIVE when dialogs are opened/closed.
    var dialogIDs = ["settingsDialog", "infoDialog", "edgeFilteringDialog"];
    function onModalShow() {
        mgsc.MODAL_ACTIVE = true;
    }
    function onModalHide() {
        mgsc.MODAL_ACTIVE = false;
    }
    function onSettingsModalHide() {
        // Ensure that all colorpickers (the pop-up things where
        // you can select a color with the mouse) get closed when
        // the settings dialog is closed.
        $(".colorpicker-component").colorpicker("hide");
        onModalHide();
    }
    for (var d = 0; d < dialogIDs.length; d++) {
        $("#" + dialogIDs[d]).on("show.bs.modal", onModalShow);
        if (dialogIDs[d] === "settingsDialog") {
            $("#settingsDialog").on("hide.bs.modal", onSettingsModalHide);
        } else {
            $("#" + dialogIDs[d]).on("hide.bs.modal", onModalHide);
        }
    }
    // Also update mgsc.INPUT_ACTIVE when non-dialog input fields are
    // focused/unfocused.
    var inputIDs = [
        "componentselector",
        "SPQRcomponentselector",
        "searchInput",
        "layoutInput",
    ];
    function onInputFocusIn() {
        mgsc.INPUT_ACTIVE = true;
    }
    function onInputFocusOut() {
        mgsc.INPUT_ACTIVE = false;
    }
    for (var ii = 0; ii < inputIDs.length; ii++) {
        $("#" + inputIDs[ii]).on("focusin", onInputFocusIn);
        $("#" + inputIDs[ii]).on("focusout", onInputFocusOut);
    }
    // Initialize colorpickers
    $(".colorpicker-component").colorpicker({ format: "hex" });
    $("#mincncp").on("changeColor", function (e) {
        redrawGradientPreview(e.color.toHex(), -1);
    });
    $("#maxcncp").on("changeColor", function (e) {
        redrawGradientPreview(e.color.toHex(), 1);
    });
    // Update the gradient preview to whatever the default colorization values
    // are. Note that we have to manually set either the min or max color
    // ourselves since redrawGradientPreview only handles one change at a time.
    $("#100gp").css("background-color", $("#maxcncp").colorpicker("getValue"));
    redrawGradientPreview($("#mincncp").colorpicker("getValue"), -1);
    // If we add any tooltips, use this line to initialize them
    //$("[data-toggle='tooltip']").tooltip();
}

/* Function that is bound to the jQuery "keydown" event when a standard-mode
 * graph containing at least one cluster is drawn.
 * When the left/right arrow keys are pressed, the viewport is zoomed to the
 * next left/right cluster in the graph (starting at the leftmost cluster
 * in the graph).
 *
 * jQuery normalizes key code values (which can vary across different
 * browsers), so this function should be portable for most desktop browsers.
 */
function moveThroughClusters(e) {
    "use strict";
    if (!mgsc.MODAL_ACTIVE && !mgsc.INPUT_ACTIVE) {
        if (e.which === 37 || e.which === 65) {
            // Left arrow key or "A"
            // Move to the next left node group
            if (mgsc.CLUSTER_X <= 0) {
                mgsc.CLUSTER_X = mgsc.CLUSTERID2TOP.length - 1;
            } else {
                mgsc.CLUSTER_X--;
            }
            moveToCurrentCluster();
        } else if (e.which === 39 || e.which === 68) {
            // Right arrow key or "D"
            // Move to the next right node group
            if (mgsc.CLUSTER_X === mgsc.CLUSTERID2TOP.length - 1) {
                mgsc.CLUSTER_X = 0;
            } else {
                mgsc.CLUSTER_X++;
            }
            moveToCurrentCluster();
        }
    }
}

/* Move to the cluster indicated by mgsc.CLUSTER_X as part of the keyboard
 * navigation feature.
 */
function moveToCurrentCluster() {
    "use strict";
    cy.fit(cy.getElementById(mgsc.CLUSTERID2TOP[mgsc.CLUSTER_X].id));
}

// Sets bindings for certain objects in the graph.
function setGraphBindings() {
    "use strict";
    // Enable right-clicking to collapse/uncollapse compound nodes
    // We store added edges + removed nodes/edges in element-level
    // data, to facilitate only doing the work of determining which
    // elements to remove/etc. once (the first time around)
    cy.on("cxttap", "node.cluster.structuralPattern", function (e) {
        // Prevent collapsing being done during iterative drawing
        // NOTE: In retrospect, I think that thanks to the use of
        // autoungrabify/autounselectify while drawing the graph that
        // this is arguably not needed, but there isn't really any harm
        // in keeping it around for the time being
        if (!$("#fitButton").hasClass("disabled")) {
            toggleCluster(e.target);
        }
    });
    // Autozoom on clusters that the user taps on, if the user explicitly
    // requested it (i.e. checked the settings box).
    if ($("#autozoomClusterCheckbox").prop("checked")) {
        cy.on("tap", "node.cluster.structuralPattern", function (e) {
            cy.animate({ fit: { eles: e.target } });
        });
    }

    // Enable SPQR tree expansion/compression
    // User can click on an uncollapsed metanode to reveal its immediate
    // children
    // User can click on a collapsed metanode to remove its immediate children
    cy.on("cxttap", "node.cluster.spqrMetanode", function (e) {
        if (!$("#fitButton").hasClass("disabled")) {
            var mn = e.target;
            if (mn.data("descendantCount") > 0) {
                if (mn.data("isCollapsed")) {
                    cy.batch(function () {
                        uncollapseSPQRMetanode(mn);
                    });
                } else {
                    cy.batch(function () {
                        collapseSPQRMetanode(mn);
                    });
                }
            }
        }
    });

    cy.on("select", "node.noncluster, edge, node.cluster", function (e) {
        var x = e.target;
        if (x.hasClass("noncluster")) {
            mgsc.SELECTED_NODE_COUNT += 1;
            mgsc.SELECTED_NODES = mgsc.SELECTED_NODES.union(x);
            $("#selectedNodeBadge").text(mgsc.SELECTED_NODE_COUNT);
            addSelectedNodeInfo(x);
        } else if (x.isEdge()) {
            mgsc.SELECTED_EDGE_COUNT += 1;
            mgsc.SELECTED_EDGES = mgsc.SELECTED_EDGES.union(x);
            $("#selectedEdgeBadge").text(mgsc.SELECTED_EDGE_COUNT);
            addSelectedEdgeInfo(x);
        } else {
            mgsc.SELECTED_CLUSTER_COUNT += 1;
            mgsc.SELECTED_CLUSTERS = mgsc.SELECTED_CLUSTERS.union(x);
            $("#selectedClusterBadge").text(mgsc.SELECTED_CLUSTER_COUNT);
            addSelectedClusterInfo(x);
        }

        // If this is the first selected element, enable the
        // fitSelected button
        if (
            mgsc.SELECTED_NODE_COUNT +
                mgsc.SELECTED_EDGE_COUNT +
                mgsc.SELECTED_CLUSTER_COUNT ===
            1
        ) {
            enableButton("fitSelectedButton");
        }
    });
    cy.on("unselect", "node.noncluster, edge, node.cluster", function (e) {
        var x = e.target;
        if (x.hasClass("noncluster")) {
            mgsc.SELECTED_NODE_COUNT -= 1;
            mgsc.SELECTED_NODES = mgsc.SELECTED_NODES.difference(x);
            $("#selectedNodeBadge").text(mgsc.SELECTED_NODE_COUNT);
            removeSelectedEleInfo(x);
        } else if (x.isEdge()) {
            mgsc.SELECTED_EDGE_COUNT -= 1;
            mgsc.SELECTED_EDGES = mgsc.SELECTED_EDGES.difference(x);
            $("#selectedEdgeBadge").text(mgsc.SELECTED_EDGE_COUNT);
            removeSelectedEleInfo(x);
        } else {
            mgsc.SELECTED_CLUSTER_COUNT -= 1;
            mgsc.SELECTED_CLUSTERS = mgsc.SELECTED_CLUSTERS.difference(x);
            $("#selectedClusterBadge").text(mgsc.SELECTED_CLUSTER_COUNT);
            removeSelectedEleInfo(x);
        }

        // Not sure how we'd have a negative amount of selected
        // elements, but I figure we might as well cover our bases with
        // the <= 0 here :P
        if (
            mgsc.SELECTED_NODE_COUNT +
                mgsc.SELECTED_EDGE_COUNT +
                mgsc.SELECTED_CLUSTER_COUNT <=
            0
        ) {
            disableButton("fitSelectedButton");
        }
    });
    // TODO look into getting this more efficient in the future, if possible
    // (Renders labels only on tapping elements; doesn't really save that
    // much time, and might actually be less efficient due to the time taken
    // to register a tap event)
    //cy.on('tapstart', 'node',
    //    function(e) {
    //        var node = e.target;
    //        console.log(node);
    //        cy.style().selector("[id = '" + node.id() + "']").style({
    //            'label': 'data(id)'
    //        }).update();
    //    }
    //);
}

// If toUncollapseReady is false, changes the collapse button to say
// "Collapse all node groups" with a minus icon.
// If toUncollapseReady is true, changes the collapse button to say
// "Uncollapse all node groups" with a plus icon.
function changeCollapseButton(toUncollapseReady) {
    "use strict";
    if (toUncollapseReady) {
        $("#collapseButtonText").text("Uncollapse all node groups");
        $("#collapseButtonIcon")
            .removeClass("glyphicon-minus-sign")
            .addClass("glyphicon-plus-sign");
    } else {
        $("#collapseButtonText").text("Collapse all node groups");
        $("#collapseButtonIcon")
            .removeClass("glyphicon-plus-sign")
            .addClass("glyphicon-minus-sign");
    }
}

/* Loads a .db file from the user's local system. */
function loadLocalDB() {
    "use strict";
    var fr = new FileReader();
    var inputfile = document.getElementById("fileselector").files[0];
    if (inputfile === undefined) {
        return;
    }
    if (inputfile.name.toLowerCase().endsWith(".db")) {
        mgsc.DB_FILENAME = inputfile.name;
        // Important -- remove old DB from memory if it exists
        closeDB();
        disableVolatileControls();
        $("#selectedNodeBadge").text(0);
        $("#selectedEdgeBadge").text(0);
        $("#selectedClusterBadge").text(0);
        disableButton("infoButton");
        $("#currComponentInfo").html(
            "No connected component has been drawn yet."
        );
        fr.onload = function (e) {
            if (e.target.readyState === FileReader.DONE) {
                initDB(e.target.result);
                document.getElementById("fileselector").value = "";
            }
        };
        // set progress bar to indeterminate state while we close
        // the old DB (if needed) and load the new DB file.
        // This isn't really that helpful on computers/fast-ish
        // systems, but for large DB files or mobile devices
        // (basically, anywhere sql.js might run slowly) this is
        // useful.
        // worth noting: we store this function call in an anonymous
        // function in order to delay its execution to when the
        // timeout happens
        // (javascript can be strange sometimes)
        startIndeterminateProgressBar();
        window.setTimeout(function () {
            fr.readAsArrayBuffer(inputfile);
        }, 50);
    } else {
        alert("Please select a valid .db file to load.");
    }
}

/* Runs prep. tasks for loading the database file and parsing its assembly +
 * component information
 *
 * CODELINK: Here, we use sql.js to parse the database file (which is stored in
 * memory as an arraybuffer -- either we've obtained the file from the server
 * using an XMLHttpRequest (from loadHostedDB()), or we've obtained the file from
 * the user's system using the HTML FileReader API (from loadLocalDB()). In
 * either case, at this point the data is stored the the same way, and we can
 * convert it to a SQL.Database object and read it later.
 *
 * See the README for sql.js (at https://github.com/kripken/sql.js/) for
 * information on using the library, as well as examples for integrating the
 * library into these and other use cases. Our use of sql.js in MetagenomeScope
 * is generally based on these examples -- in particular, the "Creating a
 * database from a file chosen by the user" and "Loading a database from a
 * server" examples.
 */
function initDB(fileData) {
    "use strict";
    // Temporarily store .db file as array of 8-bit unsigned ints
    var uIntArr = new Uint8Array(fileData);
    mgsc.CURR_DB = new SQL.Database(uIntArr);
    parseDBcomponents();
    // Set progress bar to "finished" state
    finishProgressBar();
}

/* Retrieves assembly-wide and component information from the database,
 * adjusting UI elements to prepare for component drawing accordingly.
 */
function parseDBcomponents() {
    "use strict";
    // Get assembly-wide info from the graph
    if (cy !== null) {
        destroyGraph();
    }
    var stmt = mgsc.CURR_DB.prepare("SELECT * FROM assembly;");
    stmt.step();
    var graphInfo = stmt.getAsObject();
    stmt.free();
    var fnInfo = graphInfo.filename;
    mgsc.ASM_FILETYPE = graphInfo.filetype;
    mgsc.ASM_NODE_COUNT = graphInfo.node_count;
    var nodeInfo = mgsc.ASM_NODE_COUNT.toLocaleString();
    var bpCt = graphInfo.total_length;
    var bpInfo = bpCt.toLocaleString();
    mgsc.ASM_EDGE_COUNT = graphInfo.all_edge_count;
    var edgeCount = graphInfo.edge_count;
    var edgeInfo = edgeCount.toLocaleString();
    var compCt = graphInfo.component_count;
    var compInfo = compCt.toLocaleString();
    var smallestViewableComp = graphInfo.smallest_viewable_component_rank;
    var sccCt = graphInfo.single_component_count;
    var sccInfo = sccCt.toLocaleString();
    var bicmpCt = graphInfo.bicomponent_count;
    var bicmpInfo = bicmpCt.toLocaleString();
    // Record N50
    var n50 = graphInfo.n50;
    var n50Info = n50.toLocaleString();
    // Record Assembly G/C content (not available for GML files)
    var asmGC = graphInfo.gc_content;
    mgsc.DNA_AVAILABLE = Boolean(graphInfo.dna_given);
    mgsc.REPEAT_INFO_AVAILABLE = Boolean(graphInfo.repeats_given);
    var spqrDataFlag = Boolean(graphInfo.spqr_given);
    /* CODELINK: This method for checking if a table exists in a SQLite
     * database c/o user "PoorLuzer"'s answer to this Stack Overflow question:
     * https://stackoverflow.com/questions/1601151/how-do-i-check-in-sqlite-whether-a-table-exists
     * Link to the user's SO profile:
     * https://stackoverflow.com/users/53884/poorluzer
     */
    // TODO remove the check involving spqrInfoStmt eventually.
    // For now it's helpful because there exist .db files floating around
    // without the spqr_given column in "assembly", but eventually I'll stop
    // using those and we can just rely on spqr_given without incurring extra
    // computational costs
    // When that happens, instead of using spqrDataFlag just set
    // mgsc.SPQR_INFO_AVAILABLE to that
    var spqrInfoStmt = mgsc.CURR_DB.prepare(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=" +
            "'singlecomponents';"
    );
    spqrInfoStmt.step();
    var spqrTableExistence = spqrInfoStmt.getAsObject();
    spqrInfoStmt.free();
    mgsc.SPQR_INFO_AVAILABLE =
        spqrDataFlag || !$.isEmptyObject(spqrTableExistence);
    if (mgsc.SPQR_INFO_AVAILABLE) {
        $("#spqrConnectedComponentControls").removeClass("notviewable");
        $("#sccCountTH").removeClass("notviewable");
        $("#sccCountEntry").removeClass("notviewable");
        $("#bicmpCountTH").removeClass("notviewable");
        $("#bicmpCountEntry").removeClass("notviewable");
        $("#connCmpCtTH").text("Standard Mode Connected Component Count");
    } else {
        $("#spqrConnectedComponentControls").addClass("notviewable");
        $("#sccCountTH").addClass("notviewable");
        $("#sccCountEntry").addClass("notviewable");
        $("#bicmpCountTH").addClass("notviewable");
        $("#bicmpCountEntry").addClass("notviewable");
        $("#connCmpCtTH").text("Connected Component Count");
    }
    if (
        mgsc.ASM_FILETYPE === "LastGraph" ||
        mgsc.ASM_FILETYPE === "GFA" ||
        mgsc.ASM_FILETYPE === "FASTG"
    ) {
        // Since the nodes in these graphs are unoriented (i.e. we draw both
        // strands of each sequence of DNA included in the assembly graph),
        // the individual nodes' units are in nucleotides (nt).
        $("#asmNodeCtTH").text("Positive Node Count");
        $("#asmEdgeCtTH").text("Positive Edge Count");
        $("#asmNodeLenTH").text("Total Positive Node Length");
        n50Info += " nt";
        bpInfo += " nt";
    } else {
        // The nodes in these graphs are oriented (i.e. each contig has a
        // specified orientation), so we just draw one node per sequence.
        // Thus, the individual nodes' units are in base pairs (bp).
        $("#asmNodeCtTH").text("Node Count");
        $("#asmEdgeCtTH").text("Edge Count");
        $("#asmNodeLenTH").text("Total Node Length");
        n50Info += " bp";
        bpInfo += " bp";
    }
    if (mgsc.DNA_AVAILABLE) {
        // Round to two decimal places
        var asmGCInfo = Math.round(asmGC * 100 * 100) / 100 + "%";
        $("#asmGCEntry").text(asmGCInfo);
        $("#asmGCTH").removeClass("notviewable");
        $("#asmGCEntry").removeClass("notviewable");
    } else {
        $("#asmGCTH").addClass("notviewable");
        $("#asmGCEntry").addClass("notviewable");
    }
    // Adjust UI elements
    document.title = mgsc.DB_FILENAME + " (" + fnInfo + ")";
    // TODO add back in eventually? once it plays nicely with the no drawing
    // status text stuff?
    //updateTextStatus("Loaded .db file for the assembly graph file " +fnInfo+
    //                    ".<br />You can draw a connected component using" +
    //                    " the \"Draw Connected Component\" buttons below.",
    //                    true);
    $("#filenameEntry").text(fnInfo);
    $("#filetypeEntry").text(mgsc.ASM_FILETYPE);
    $("#nodeCtEntry").text(nodeInfo);
    $("#totalBPLengthEntry").text(bpInfo);
    $("#edgeCountEntry").text(edgeInfo);
    $("#sccCountEntry").text(sccInfo);
    $("#bicmpCountEntry").text(bicmpInfo);
    $("#connCmpCtEntry").text(compInfo);
    $("#n50Entry").text(n50Info);
    // Reset connected component in the selector to smallest viewable component
    // (or just 1, for the SPQR case, since we don't support skipping
    // components there yet)
    $("#componentselector").prop("value", smallestViewableComp);
    $("#componentselector").prop("max", compCt);
    $("#componentselector").prop("disabled", false);
    $("#SPQRcomponentselector").prop("value", 1);
    $("#SPQRcomponentselector").prop("max", sccCt);
    $("#SPQRcomponentselector").prop("disabled", false);
    enableCompRankControlsIfNecessary();
    enableButton("drawButton");
    enableButton("drawSPQRButton");
    enableButton("implicitSPQROption");
    enableButton("explicitSPQROption");
    mgsc.SCAFFOLDID2NODEKEYS = {};
    mgsc.BICOMPONENTID2VISIBLESINGLENODEIDS = {};
    $("#agpLoadedFileName").addClass("notviewable");
    $("#scaffoldInfoHeader").addClass("notviewable");
    $("#scaffoldCycler").addClass("notviewable");
    mgsc.COMPONENT_NODE_KEYS = [];
    $("#assembledNodes").empty();
    mgsc.FINISHING_MODE_ON = false;
    mgsc.FINISHING_MODE_PREVIOUSLY_DONE = false;
    mgsc.FINISHING_NODE_IDS = "";
    mgsc.FINISHING_NODE_OBJS = [];
    togglePauseFinishingButtonStyle(-1);
    // This'll get changed to this anyway when drawing a component, but this
    // way we prevent something else from being checked in the "in-between"
    // state when no components have been drawn
    $("#noneColorization").prop("checked", true);
    if (mgsc.DEMOS_SUPPORTED) {
        enableButton("xmlFileselectButton");
    }
    enableButton("fileselectButton");
    enableButton("loadDBbutton");
    enableButton("infoButton");
    enableButton("dir0");
    enableButton("dir90");
    enableButton("dir180");
    enableButton("dir270");
    enableButton("settingsButton");
    // Adjust selected info tables based on what info is available
    var extraNodeCols = 0;
    if (mgsc.DNA_AVAILABLE) {
        $("#gcContentCol").removeClass("notviewable");
        extraNodeCols++;
    } else {
        $("#gcContentCol").addClass("notviewable");
    }
    if (mgsc.REPEAT_INFO_AVAILABLE) {
        $("#repeatCol").removeClass("notviewable");
        extraNodeCols++;
    } else {
        $("#repeatCol").addClass("notviewable");
    }
    if (mgsc.ASM_FILETYPE === "GML") {
        // Node info adjustments
        // All contigs in GML files have at minimum ID, label, length given
        $("#nodeTH").prop("colspan", 3 + extraNodeCols);
        $("#depthCol").addClass("notviewable");
        $("#labelCol").removeClass("notviewable");
        // Adjust search options to indicate that both labels and IDs available
        enableSearchOption("Label");
        // Edge info adjustments
        $("#edgeTH").prop("colspan", 6);
        $("#multiplicityCol").text("B. size");
        $("#multiplicityCol").removeClass("notviewable");
        $("#orientationCol").removeClass("notviewable");
        $("#meanCol").removeClass("notviewable");
        $("#stdevCol").removeClass("notviewable");
    } else if (mgsc.ASM_FILETYPE === "LastGraph") {
        // Node info adjustments
        // All contigs in LastGraph files have at min. ID, length, depth given
        // (they also always have GC content given, since LastGraph files seem
        // to always have sequences given, but we use extraNodeCols anyway to
        // make this more flexible)
        $("#nodeTH").prop("colspan", 3 + extraNodeCols);
        $("#depthCol").removeClass("notviewable");
        $("#labelCol").addClass("notviewable");
        // Adjust search option to indicate that labels aren't available, and
        // switch back to the default search type if it isn't already set to ID
        disableSearchOption("Label");
        toggleSearchType("ID");
        // Edge info adjustments
        $("#edgeTH").prop("colspan", 3);
        $("#multiplicityCol").text("Multiplicity");
        $("#multiplicityCol").removeClass("notviewable");
        $("#orientationCol").addClass("notviewable");
        $("#meanCol").addClass("notviewable");
        $("#stdevCol").addClass("notviewable");
    } else if (mgsc.ASM_FILETYPE === "GFA") {
        // Node info adjustments
        // All contigs in GFA files have at minimum ID, length given
        $("#nodeTH").prop("colspan", 2 + extraNodeCols);
        $("#depthCol").addClass("notviewable");
        $("#labelCol").addClass("notviewable");
        disableSearchOption("Label");
        toggleSearchType("ID");
        // Edge info adjustments
        $("#edgeTH").prop("colspan", 2);
        $("#multiplicityCol").addClass("notviewable");
        $("#orientationCol").addClass("notviewable");
        $("#meanCol").addClass("notviewable");
        $("#stdevCol").addClass("notviewable");
    } else if (mgsc.ASM_FILETYPE === "FASTG") {
        // Node info adjustments
        // All contigs in FASTG files have ID, length, depth, GC content given
        $("#nodeTH").prop("colspan", 3 + extraNodeCols);
        $("#depthCol").removeClass("notviewable");
        $("#labelCol").addClass("notviewable");
        disableSearchOption("Label");
        toggleSearchType("ID");
        // Edge info adjustments
        // Edges in SPAdes FASTG files are like those in GFA files -- no
        // apparent metadata (multiplicity, etc) aside from source/sink IDs
        $("#edgeTH").prop("colspan", 2);
        $("#multiplicityCol").addClass("notviewable");
        $("#orientationCol").addClass("notviewable");
        $("#meanCol").addClass("notviewable");
        $("#stdevCol").addClass("notviewable");
    }
}

/* Disables some "volatile" controls in the graph. Should be used when doing
 * any sort of operation, I guess. */
function disableVolatileControls() {
    "use strict";
    disableButton("settingsButton");
    $("#componentselector").prop("disabled", true);
    disableButton("decrCompRankButton");
    disableButton("incrCompRankButton");
    disableButton("drawButton");
    $("#SPQRcomponentselector").prop("disabled", true);
    disableButton("decrSPQRCompRankButton");
    disableButton("incrSPQRCompRankButton");
    disableButton("drawSPQRButton");
    disableButton("implicitSPQROption");
    disableButton("explicitSPQROption");
    disableButton("fileselectButton");
    disableButton("loadDBbutton");
    disableButton("xmlFileselectButton");
    $("#searchInput").prop("disabled", true);
    $("#layoutInput").prop("disabled", true);
    disableButton("filterEdgesButton");
    disableButton("reduceEdgesButton");
    disableButton("layoutButton");
    disableButton("scaffoldFileselectButton");
    disableButton("startFinishingButton");
    disableButton("pauseFinishingButton");
    disableButton("endFinishingButton");
    disableButton("exportPathButton");
    disableButton("agpOption");
    disableButton("csvOption");
    disableButton("floatingExportButton");
    $("#assembledNodes").empty();
    disableButton("searchButton");
    disableButton("searchTypeButton");
    disableButton("collapseButton");
    disableButton("fitSelectedButton");
    disableButton("fitButton");
    disableButton("exportImageButton");
    disableButton("dir0");
    disableButton("dir90");
    disableButton("dir180");
    disableButton("dir270");
    disableButton("pngOption");
    disableButton("jpgOption");
    disableButton("changeNodeColorizationButton");
    disableInlineRadio("noneColorization");
    disableInlineRadio("gcColorization");
    disableInlineRadio("repeatColorization");
    //disableInlineRadio("geneColorization");
    //disableInlineRadio("depthColorization");
    clearSelectedInfo();
}

/* Displays a status message in the #textStatus <div>.
 * If notDuringDrawing is false, then these messages will not be displayed if
 * the #useDrawingStatusTextCheckbox is unchecked.
 */
function updateTextStatus(text, notDuringDrawing) {
    "use strict";
    if (
        notDuringDrawing ||
        $("#useDrawingStatusTextCheckbox").prop("checked")
    ) {
        $("#textStatus").html(text);
    }
}

function toggleHEV() {
    "use strict";
    mgsc.HIDE_EDGES_ON_VIEWPORT = !mgsc.HIDE_EDGES_ON_VIEWPORT;
}
function toggleUTV() {
    "use strict";
    mgsc.TEXTURE_ON_VIEWPORT = !mgsc.TEXTURE_ON_VIEWPORT;
}

function toggleClusterNav() {
    "use strict";
    mgsc.USE_CLUSTER_KBD_NAV = !mgsc.USE_CLUSTER_KBD_NAV;
}

/* If mode == "SPQR", begins drawing the SPQR-integrated component of the
 * corresponding component rank selector; else, draws a component of the normal
 * (double) graph.
 */
function startDrawComponent(mode) {
    "use strict";
    mgsc.START_DRAW_DATE = new Date();
    var selector = "#componentselector";
    var drawFunc = drawComponent;
    if (mode == "SPQR") {
        selector = "#SPQRcomponentselector";
        drawFunc = drawSPQRComponent;
    }
    var currRank = $(selector).val();
    if (compRankValidity(currRank, selector) !== 0) {
        alert("Please enter a valid component rank using the input field.");
        return;
    }
    // Check if this component was laid out. This check should be done after
    // the compRankValidity check, since this assumes that currRank at least
    // refers to a valid component rank (so if it is invalid, the sql.js query
    // will fail).
    if (mode !== "SPQR") {
        var drawableResult = isComponentDrawable(currRank);
        if (!drawableResult[0]) {
            alert(
                "Due to its size (" +
                    drawableResult[1] +
                    " nodes and " +
                    drawableResult[2] +
                    " edges), layout was not performed " +
                    "on this component (size rank " +
                    currRank +
                    "). It is not " +
                    "drawable using the current .db file. You can control this " +
                    "behavior through the -maxn and -maxe MetagenomeScope " +
                    "preprocessing script command-line arguments, if desired."
            );
            return;
        }
    }
    // if compRankValidity === 0, then currRank must represent just an
    // integer: so parseInt is fine to run on it
    updateTextStatus("Drawing clusters...", false);
    window.setTimeout(drawFunc(parseInt(currRank)), 0);
}

/* Checks if the standard-mode component with the given size rank is drawable.
 * Returns an array of [false, component node count, component edge count] if it
 * is not drawable; returns [true, 0, 0] if it is drawable.
 * (TODO: use the node/edge counts in the drawable case? see #142 on github.)
 */
function isComponentDrawable(cmpRank) {
    "use strict";
    var isTooLargeStmt;
    try {
        isTooLargeStmt = mgsc.CURR_DB.prepare(
            "SELECT node_count, edge_count, too_large FROM components WHERE " +
                "size_rank = ? LIMIT 1",
            [cmpRank]
        );
    } catch (error) {
        // The error here is almost certainly due to an old .db file that
        // doesn't have a too_large column for this component (since we already
        // checked the validity of this component rank). So we just go ahead
        // with rendering it. As new .db files are created, this branch should
        // be visited less and less.
        return [true, 0, 0];
    }
    isTooLargeStmt.step();
    var isTooLargeObj = isTooLargeStmt.getAsObject();
    isTooLargeStmt.free();
    if (isTooLargeObj.too_large !== 0) {
        var largeCompNodeCount = isTooLargeObj.node_count.toLocaleString();
        var largeCompEdgeCount = isTooLargeObj.edge_count.toLocaleString();
        return [false, largeCompNodeCount, largeCompEdgeCount];
    }
    return [true, 0, 0];
}

/* Draws the selected connected component in the .db file -- its nodes, its
 * edges, its clusters -- to the screen.
 */
function drawComponent(cmpRank) {
    "use strict";
    disableVolatileControls();
    // Okay, we can draw this component!
    if (cy !== null) {
        // If we already have a graph instance, clear that graph before
        // initializing another one
        // This should have already been called in parseDBcomponents(),
        // but since you can draw multiple components for the same .db file
        // we include this here as well
        destroyGraph();
    }
    initGraph("double");
    setGraphBindings();
    $(document).off("keydown");
    var componentNodeCount = 0;
    var componentEdgeCount = 0;
    mgsc.SELECTED_NODES = cy.collection();
    mgsc.SELECTED_EDGES = cy.collection();
    mgsc.SELECTED_CLUSTERS = cy.collection();
    mgsc.COMPONENT_EDGE_WEIGHTS = [];
    mgsc.CLUSTERID2TOP = [];
    mgsc.CLUSTER_X = -1;
    $("#scaffoldCycler").addClass("notviewable");
    // will be set to true if we find suitable scaffolds
    // the actual work of finding those scaffolds (if mgsc.SCAFFOLDID2NODEKEYS is
    // not empty, of course) is done in finishDrawComponent().
    mgsc.COMPONENT_HAS_SCAFFOLDS = false;
    $("#scaffoldInfoHeader").addClass("notviewable");
    mgsc.COMPONENT_NODE_KEYS = [];
    $("#assembledNodes").empty();
    mgsc.FINISHING_MODE_ON = false;
    mgsc.FINISHING_MODE_PREVIOUSLY_DONE = false;
    mgsc.FINISHING_NODE_IDS = "";
    mgsc.FINISHING_NODE_OBJS = [];
    mgsc.NEXT_NODES = cy.collection();
    togglePauseFinishingButtonStyle(-1);
    mgsc.SELECTED_NODE_COUNT = 0;
    mgsc.SELECTED_EDGE_COUNT = 0;
    mgsc.SELECTED_CLUSTER_COUNT = 0;
    mgsc.REMOVED_EDGES = cy.collection();
    $("#selectedNodeBadge").text(0);
    $("#selectedEdgeBadge").text(0);
    $("#selectedClusterBadge").text(0);
    mgsc.BICOMPONENTID2VISIBLESINGLENODEIDS = {};
    // Set the controls that aren't viewable in the SPQR view to be viewable,
    // since we're not drawing the SPQR view
    $("#searchForElementsControls").removeClass("notviewable");
    $("#assemblyFinishingControls").removeClass("notviewable");
    $("#viewScaffoldsControls").removeClass("notviewable");
    $("#testLayoutsControls").removeClass("notviewable");
    $("#displayOptionsControls").removeClass("notviewable");
    $("#collapseButtonControls").removeClass("notviewable");
    // Disable other node colorization settings and check the "noncolorized"
    // node colorization option by default
    $("#noneColorization").prop("checked", true);
    mgsc.CURR_NODE_COLORIZATION = "noncolorized";
    mgsc.PREV_ROTATION = 0;
    // NOTE -- DISABLED ROTATION -- to allow rotation uncomment below and
    // replace mgsc.CURR_ROTATION = 90 line
    //mgsc.CURR_ROTATION = parseInt($("#rotationButtonGroup .btn.active")
    //    .attr("value"));
    mgsc.CURR_ROTATION = 90;
    cy.scratch("_collapsed", cy.collection());
    cy.scratch("_uncollapsed", cy.collection());
    cy.scratch("_ele2parent", {});
    // Now we render the nodes, edges, and clusters of this component.
    // But first we need to get the bounding box of this component.
    // Along with the component's total node count.
    var bbStmt = mgsc.CURR_DB.prepare(
        "SELECT boundingbox_x, boundingbox_y, node_count, edge_count FROM components WHERE " +
            "size_rank = ? LIMIT 1",
        [cmpRank]
    );
    bbStmt.step();
    var fullObj = bbStmt.getAsObject();
    bbStmt.free();
    var bb = {
        boundingbox_x: fullObj.boundingbox_x,
        boundingbox_y: fullObj.boundingbox_y,
    };
    var totalElementCount = fullObj.node_count + 0.5 * fullObj.edge_count;
    // here we scale mgsc.PROGRESSBAR_FREQ to totalElementCount for the
    // component to be drawn (see top of file for reference)
    // As we draw other components later within the same session of the viewer
    // application, mgsc.PROGRESSBAR_FREQ will be updated accordingly
    mgsc.PROGRESSBAR_FREQ = Math.floor(
        mgsc.PROGRESSBAR_FREQ_PERCENT * totalElementCount
    );
    // We need a fast way to associate node IDs with their x/y positions.
    // This is for calculating edge control point weight/distance.
    // And doing 2 DB queries (src + tgt) for each edge will take a lot of
    // time -- O(2|E|) time, specifically, with the only benefit of not
    // taking up a lot of space. So we go with the mapping solution -- it's
    // not particularly pretty, but it works alright.
    var node2pos = {};
    // We check to see if the component contains >= 1 cluster. If so, we
    // enable the collapse/uncollapse button; if not, we don't bother
    // enabling the button and keep it disabled because it'd be useless
    var clustersInComponent = false;
    cy.startBatch();
    var clustersStmt = mgsc.CURR_DB.prepare(
        "SELECT * FROM clusters WHERE component_rank = ?",
        [cmpRank]
    );
    while (clustersStmt.step()) {
        clustersInComponent = true;
        renderClusterObject(clustersStmt.getAsObject(), bb, "cluster");
    }
    clustersStmt.free();
    // Draw graph "iteratively" -- display all clusters.
    drawBoundingBoxEnforcingNodes(bb);
    cy.endBatch();
    cy.fit();
    updateTextStatus("Drawing nodes...", false);
    window.setTimeout(function () {
        /* I originally didn't have this wrapped in a timeout, but for some
         * reason a few clusters in the test MetaCarvel E. coli assembly
         * weren't being rendered at the waiting point. It seemed some sort of
         * race condition was happening, and wrapping this block of code in a
         * timeout seems to solve the problem for iterative cluster drawing
         * (iterative node/edge drawing is fine, since those already use
         * timeouts to update the progress bar).
         */
        cy.startBatch();
        var nodesStmt = mgsc.CURR_DB.prepare(
            "SELECT * FROM nodes WHERE component_rank = ?",
            [cmpRank]
        );
        mgsc.CURR_NE = 0;
        drawComponentNodes(
            nodesStmt,
            bb,
            cmpRank,
            node2pos,
            clustersInComponent,
            componentNodeCount,
            componentEdgeCount,
            totalElementCount,
            "double",
            "",
            [],
            []
        );
    }, 0);
}

/* Draws nodes in the component, then switches to drawing edges.
 * If mode is "SPQR" then this will handle those nodes' IDs/etc. specially.
 * Otherwise, it's assumed that nodes are in a normal double graph.
 *
 * (If mode is "SPQR" then spqrSpecs is interpreted as a string that can be
 * suffixed to a SQLite query for selecting singlenodes/singleedges, and
 * metanodeParams is interpreted as an array of cmpRank followed by all the
 * root metanode IDs. counts will also be interpreted as an array of
 * [compressed node count, compressed edge count, uncompressed node count,
 * uncompressed edge count, bicomponent count].
 * If mode is not "SPQR" then those three values aren't used.)
 *
 * (sorry this code wound up being ugly)
 */
function drawComponentNodes(
    nodesStmt,
    bb,
    cmpRank,
    node2pos,
    clustersInComponent,
    componentNodeCount,
    componentEdgeCount,
    totalElementCount,
    mode,
    spqrSpecs,
    metanodeParams,
    counts
) {
    "use strict";
    if (nodesStmt.step()) {
        var currNode = nodesStmt.getAsObject();
        var currNodeID = currNode.id;
        var parentMetaNodeID = currNode.parent_metanode_id;
        // Render the node object and save its position
        if (mode === "SPQR" && parentMetaNodeID !== null) {
            // It's possible for us to have duplicates of this node, in this
            // case. We construct this node's ID in Cytoscape.js as its actual
            // ID suffixed by its parent metanode ID in order to disambiguate
            // it from other nodes with the same ID in different metanodes.
            currNodeID += "_" + parentMetaNodeID;
        }
        node2pos[currNodeID] = renderNodeObject(currNode, currNodeID, bb, mode);
        componentNodeCount += 1;
        mgsc.CURR_NE += 1;
        if (mgsc.CURR_NE % mgsc.PROGRESSBAR_FREQ === 0) {
            updateProgressBar((mgsc.CURR_NE / totalElementCount) * 100);
            window.setTimeout(function () {
                drawComponentNodes(
                    nodesStmt,
                    bb,
                    cmpRank,
                    node2pos,
                    clustersInComponent,
                    componentNodeCount,
                    componentEdgeCount,
                    totalElementCount,
                    mode,
                    spqrSpecs,
                    metanodeParams,
                    counts
                );
            }, 0);
        } else {
            drawComponentNodes(
                nodesStmt,
                bb,
                cmpRank,
                node2pos,
                clustersInComponent,
                componentNodeCount,
                componentEdgeCount,
                totalElementCount,
                mode,
                spqrSpecs,
                metanodeParams,
                counts
            );
        }
    } else {
        nodesStmt.free();
        // Second part of "iterative" graph drawing: draw all edges
        cy.endBatch();
        cy.fit();
        updateTextStatus("Drawing edges...", false);
        cy.startBatch();
        // NOTE that we intentionally only consider edges within this component
        // Multiplicity is an inherently relative measure, so outliers in other
        // components will just mess things up in the current component.
        var edgesStmt;
        var edgeType = "doubleedge";
        if (mode !== "SPQR") {
            edgesStmt = mgsc.CURR_DB.prepare(
                "SELECT * FROM edges WHERE component_rank = ?",
                [cmpRank]
            );
        } else {
            // Our use of spqrSpecs and metanodeParams in constructing this
            // query is the only reason we bother passing them to
            // drawComponentNodes() after we used them earlier to construct the
            // query on singlenodes. Now that we have edgesStmt ready, we don't
            // need to bother saving spqrSpecs and metanodeParams.
            edgeType = "singleedge";
            edgesStmt = mgsc.CURR_DB.prepare(
                "SELECT * FROM singleedges " + spqrSpecs,
                metanodeParams
            );
            // NOTE don't draw metanodeedges by default due to autocollapsing
        }
        drawComponentEdges(
            edgesStmt,
            bb,
            node2pos,
            cmpRank,
            clustersInComponent,
            componentNodeCount,
            componentEdgeCount,
            totalElementCount,
            edgeType,
            mode,
            counts
        );
    }
}

// If edgeType !== "double" then draws edges accordingly
// related: if mode === "SPQR" then draws edges accordingly
// also if mode === "SPQR" then passes counts on to finishDrawComponent()
function drawComponentEdges(
    edgesStmt,
    bb,
    node2pos,
    cmpRank,
    clustersInComponent,
    componentNodeCount,
    componentEdgeCount,
    totalElementCount,
    edgeType,
    mode,
    counts
) {
    "use strict";
    if (edgesStmt.step()) {
        renderEdgeObject(
            edgesStmt.getAsObject(),
            node2pos,
            bb,
            edgeType,
            mode,
            {}
        );
        componentEdgeCount += 1;
        mgsc.CURR_NE += 0.5;
        if (mgsc.CURR_NE % mgsc.PROGRESSBAR_FREQ === 0) {
            updateProgressBar((mgsc.CURR_NE / totalElementCount) * 100);
            window.setTimeout(function () {
                drawComponentEdges(
                    edgesStmt,
                    bb,
                    node2pos,
                    cmpRank,
                    clustersInComponent,
                    componentNodeCount,
                    componentEdgeCount,
                    totalElementCount,
                    edgeType,
                    mode,
                    counts
                );
            }, 0);
        } else {
            drawComponentEdges(
                edgesStmt,
                bb,
                node2pos,
                cmpRank,
                clustersInComponent,
                componentNodeCount,
                componentEdgeCount,
                totalElementCount,
                edgeType,
                mode,
                counts
            );
        }
    } else {
        edgesStmt.free();
        mgsc.CURR_BOUNDINGBOX = bb;
        finishDrawComponent(
            cmpRank,
            componentNodeCount,
            componentEdgeCount,
            clustersInComponent,
            mode,
            counts
        );
    }
}

// Updates a paragraph contained in the assembly info dialog with some general
// information about the current connected component.
function updateCurrCompInfo(
    cmpRank,
    componentNodeCount,
    componentEdgeCount,
    mode,
    counts
) {
    "use strict";
    var intro = "The ";
    var nodePercentage, edgePercentage;
    if (mode !== "SPQR") {
        nodePercentage = (componentNodeCount / mgsc.ASM_NODE_COUNT) * 100;
        if (mgsc.ASM_EDGE_COUNT !== 0) {
            edgePercentage = (componentEdgeCount / mgsc.ASM_EDGE_COUNT) * 100;
        } else {
            edgePercentage = "None";
        }
    }
    var all_nodes_edges_modifier = "the";
    if (mode !== "SPQR" && $("#filetypeEntry").text() !== "GML") {
        intro =
            "Including <strong>both positive and negative</strong>" +
            " nodes and edges, the ";
        nodePercentage /= 2;
        all_nodes_edges_modifier = "all positive and negative";
    }
    // This is incredibly minor, but I always get annoyed at software that
    // doesn't use correct grammar for stuff like this nowadays :P
    var bodyText =
        intro +
        "current connected component (size rank <strong>" +
        cmpRank +
        "</strong>) ";
    if (mode === "SPQR") {
        bodyText +=
            "in the SPQR view, when fully collapsed, has <strong>" +
            counts[0] +
            " " +
            getSuffix(counts[0], "node") +
            "</strong> and " +
            "<strong>" +
            counts[1] +
            " " +
            getSuffix(counts[1], "edge") +
            "</strong>. When fully " +
            mgsc.CURR_SPQRMODE +
            "ly uncollapsed, " +
            "the connected component has <strong>" +
            counts[2] +
            " " +
            getSuffix(counts[2], "node") +
            "</strong> and " +
            "<strong>" +
            counts[3] +
            " " +
            getSuffix(counts[3], "edge") +
            "</strong>. The connected component has <strong>" +
            counts[4] +
            " " +
            getSuffix(counts[4], "biconnected component") +
            "</strong>. ";
        if (mgsc.CURR_SPQRMODE === "explicit") {
            bodyText +=
                "(These figures do not include SPQR tree metanodes, " +
                "although they do include the edges between them when " +
                "uncollapsed.)";
        }
    } else {
        var nodeNoun = getSuffix(componentNodeCount, "node");
        var edgeNoun = getSuffix(componentEdgeCount, "edge");
        bodyText +=
            "has <strong>" +
            componentNodeCount +
            " " +
            nodeNoun +
            "</strong> and <strong>" +
            componentEdgeCount +
            " " +
            edgeNoun +
            "</strong>. This connected component contains <strong>" +
            nodePercentage.toFixed(2) +
            "% of " +
            all_nodes_edges_modifier +
            " nodes</strong> in the assembly";
        if (edgePercentage !== "None") {
            bodyText +=
                " and <strong>" +
                edgePercentage.toFixed(2) +
                "% of " +
                all_nodes_edges_modifier +
                " edges</strong> in the assembly.";
        } else {
            bodyText += ". There are no edges in the assembly.";
        }
    }
    $("#currComponentInfo").html(bodyText);
}

function getSuffix(countOfSomething, noun) {
    "use strict";
    return countOfSomething === 1 ? noun : noun + "s";
}

function finishDrawComponent(
    cmpRank,
    componentNodeCount,
    componentEdgeCount,
    clustersInComponent,
    mode,
    counts
) {
    "use strict";
    updateCurrCompInfo(
        cmpRank,
        componentNodeCount,
        componentEdgeCount,
        mode,
        counts
    );
    // NOTE modified initClusters() to do cluster height after the fact.
    // This represents an inefficiency when parsing xdot files, although it
    // shouldn't really affect anything major.
    if (mode !== "SPQR") {
        initClusters();
    }
    cy.endBatch();
    cy.fit();
    // we do this after fitting to ensure the best precision possible
    // (also, this helps when drawing collapsed SPQR trees. See the MaryGold
    // test graph as a good example of why this is needed)
    cy.batch(function () {
        removeBoundingBoxEnforcingNodes();
    });
    // Set minZoom to whatever the zoom level when viewing the entire drawn
    // component at once (i.e. right now) is
    cy.minZoom(cy.zoom());
    updateTextStatus("Preparing interface...", false);
    window.setTimeout(function () {
        // If we have scaffold data still loaded for this assembly, use it
        // for the newly drawn connected component.
        if (!$.isEmptyObject(mgsc.SCAFFOLDID2NODEKEYS)) {
            updateScaffoldsInComponentList();
        }
        // At this point, all of the hard work has been done. All that's left
        // to do now is re-enable controls, enable graph interaction, etc.
        $("#componentselector").prop("disabled", false);
        $("#SPQRcomponentselector").prop("disabled", false);
        enableCompRankControlsIfNecessary();
        enableButton("drawButton");
        enableButton("drawSPQRButton");
        enableButton("implicitSPQROption");
        enableButton("explicitSPQROption");
        enableButton("fileselectButton");
        enableButton("loadDBbutton");
        if (mgsc.DEMOS_SUPPORTED) {
            enableButton("xmlFileselectButton");
        }
        $("#searchInput").prop("disabled", false);
        $("#layoutInput").prop("disabled", false);
        if (mode !== "SPQR" && componentEdgeCount > 0) {
            enableButton("reduceEdgesButton");
            if (
                mgsc.ASM_FILETYPE === "LastGraph" ||
                mgsc.ASM_FILETYPE === "GML"
            ) {
                // Only enable the edge filtering features for graphs that have
                // edge weights (multiplicity or bundle size)
                enableButton("filterEdgesButton");
            }
        }
        enableButton("layoutButton");
        enableButton("scaffoldFileselectButton");
        enableButton("startFinishingButton");
        enableButton("agpOption");
        enableButton("csvOption");
        enableButton("searchButton");
        enableButton("searchTypeButton");
        enableButton("fitButton");
        enableButton("exportImageButton");
        enableButton("floatingExportButton");
        enableButton("dir0");
        enableButton("dir90");
        enableButton("dir180");
        enableButton("dir270");
        enableButton("pngOption");
        enableButton("jpgOption");
        if (mgsc.DNA_AVAILABLE || mgsc.REPEAT_INFO_AVAILABLE) {
            enableButton("changeNodeColorizationButton");
            enableInlineRadio("noneColorization");
            if (mgsc.DNA_AVAILABLE) {
                // GC content is available
                enableInlineRadio("gcColorization");
            }
            if (mgsc.REPEAT_INFO_AVAILABLE) {
                enableInlineRadio("repeatColorization");
            }
        }
        enableButton("settingsButton");
        cy.userPanningEnabled(true);
        cy.userZoomingEnabled(true);
        cy.boxSelectionEnabled(true);
        cy.autounselectify(false);
        cy.autoungrabify(false);
        if (clustersInComponent) {
            enableButton("collapseButton");
            if (mode !== "SPQR" && mgsc.USE_CLUSTER_KBD_NAV) {
                $(document).on("keydown", moveThroughClusters);
            }
        } else {
            disableButton("collapseButton");
        }
        updateTextStatus("&nbsp;", false);
        finishProgressBar();
        // Log the time it took to draw this component; useful for benchmarking
        mgsc.END_DRAW_DATE = new Date();
        var drawTime =
            mgsc.END_DRAW_DATE.getTime() - mgsc.START_DRAW_DATE.getTime();
        var consoleMsg = "Drawing ";
        if (mode !== "SPQR") {
            consoleMsg += "standard";
        } else {
            consoleMsg += mgsc.CURR_SPQRMODE + " SPQR";
        }
        consoleMsg += " component #" + cmpRank + " took " + drawTime + "ms";
        console.log(consoleMsg);
    }, 0);
}

function changeDropdownVal(arrowHTML) {
    "use strict";
    $("#rotationDropdown").html(arrowHTML + " <span class='caret'></span>");
}

/* Loads a .db file using an XML HTTP Request. */
function loadHostedDB() {
    "use strict";
    // Important -- remove old DB from memory if it exists
    closeDB();
    // usually we won't have the luxury of ID === filename, but this is a
    // demo so might as well
    $("#fsDialog").modal("hide");
    disableVolatileControls();
    $("#selectedNodeBadge").text(0);
    $("#selectedEdgeBadge").text(0);
    $("#selectedClusterBadge").text(0);
    disableButton("infoButton");
    $("#currComponentInfo").html("No connected component has been drawn yet.");
    // Figure out where the hosted .db files are
    var db_filename_prefix = $("#demoDir").attr("data-mgscdbdirectory");
    if (db_filename_prefix.length > 0 && !db_filename_prefix.endsWith("/")) {
        db_filename_prefix += "/";
    }
    mgsc.DB_FILENAME =
        db_filename_prefix + $("input[name=fs]:checked").attr("id");
    // jQuery doesn't support arraybuffer responses so we have to manually
    // use an XMLHttpRequest(), strange capitalization and all
    // CODELINK: Credit to this approach goes here, btw:
    // http://www.henryalgus.com/reading-binary-files-using-jquery-ajax/
    var xhr = new XMLHttpRequest();
    xhr.open("GET", mgsc.DB_FILENAME, true);
    xhr.responseType = "arraybuffer";
    xhr.onload = function (eve) {
        if (this.status === 200) {
            initDB(this.response);
        }
    };
    startIndeterminateProgressBar();
    xhr.send();
}

// Given percentage lies within [0, 100]
function updateProgressBar(percentage) {
    "use strict";
    $(".progress-bar").css("width", percentage + "%");
    $(".progress-bar").attr("aria-valuenow", percentage);
}

function finishProgressBar() {
    "use strict";
    // We call updateProgressBar since, depending on the progress bar update
    // frequency in the process that was ongoing before finishProgressBar() is
    // called, the progress bar could be at a value less than 100%. So we call
    // updateProgressBar(100) as a failsafe to make sure the progress bar
    // always ends up at 100%, regardless of the update frequency.
    updateProgressBar(100);
    if (!$(".progress-bar").hasClass("notransitions")) {
        $(".progress-bar").addClass("notransitions");
    }
    if ($(".progress-bar").hasClass("progress-bar-striped")) {
        $(".progress-bar").removeClass("progress-bar-striped");
    }
    if ($(".progress-bar").hasClass("active")) {
        $(".progress-bar").removeClass("active");
    }
}

/* Assumes the progress bar is not already indeterminate and that the
 * progress bar is already at 100% width.
 */
function startIndeterminateProgressBar() {
    "use strict";
    if ($("#useProgressBarStripesCheckbox").prop("checked")) {
        $(".progress-bar").addClass("active");
        $(".progress-bar").addClass("progress-bar-striped");
        $(".progress-bar").removeClass("notransitions");
    }
}

function toggleFinishingAnimationSettings() {
    "use strict";
    $("#maxFinishingZoomDiv").toggleClass("notviewable");
}

/* Inverts all colors in the color settings. Here we define "inversion" of
 * a color with RGB channel values R, G, B where each value is an integer
 * in the range [0, 255] as inv((R, G, B)) -> (255 - R, 255 - G, 255 - B).
 */
function invertColorSettings() {
    "use strict";
    $(".colorpicker-component").each(function (i) {
        var oldRGB = $(this).data("colorpicker").color.toRGB();
        var newRGB =
            "rgb(" +
            (255 - oldRGB.r) +
            "," +
            (255 - oldRGB.g) +
            "," +
            (255 - oldRGB.b) +
            ")";
        $(this).colorpicker("setValue", newRGB);
    });
}

/* If toDownload is true, calls downloadDataURI(); otherwise, just returns the
 * color settings string. (NOTE -- at present, no other places in the code use
 * this function with toDownload === false; I'm retaining this functionality
 * in case that need comes up in the future, though.)
 */
function exportColorSettings(toDownload) {
    "use strict";
    var textToExport = "";
    $(".colorpicker-component").each(function (i) {
        textToExport += this.id + "\t" + $(this).colorpicker("getValue") + "\n";
    });
    if (toDownload) {
        downloadDataURI("color_settings.tsv", textToExport, true);
    } else {
        return textToExport;
    }
}

/* Resets the color settings to mgsc.DEFAULT_COLOR_SETTINGS, defined above. */
function resetColorSettings() {
    "use strict";
    integrateColorSettings(mgsc.DEFAULT_COLOR_SETTINGS);
}

/* Given a string containing the entire text of a color settings .tsv file,
 * integrates each line for its respective colorpicker (so, for example,
 * a line consisting of usncp\t#ff0000 will result in the colorpicker with
 * ID "usncp" being set to the color #ff0000).
 */
function integrateColorSettings(fileText) {
    "use strict";
    var fileLines = fileText.split("\n");
    for (var n = 0; n < fileLines.length; n++) {
        var lineVals = fileLines[n].split("\t");
        if (lineVals.length !== 2) {
            // ignore lines that don't follow the ID\tCOLOR format
            continue;
        }
        // NOTE at present we don't impose any sort of validation
        // on the color inputs, since invalid colors will just map
        // to #000 (we assume that the imported color settings are
        // correct).
        $("#" + lineVals[0]).colorpicker("setValue", lineVals[1]);
    }
}

/* Imports a color settings .tsv file. Designed to work with .tsv files
 * generated by exportColorSettings(), but the format is simple enough that
 * it'd be certainly possible to create an input file for this manually.
 *
 * This loads the entire file at once instead of using Blobs to read it; this
 * is acceptable because the size of this file is expected to be relatively
 * small. We don't impose a check for file size or anything, although I suppose
 * that might be an option if we want to prevent the user from importing really
 * pointlessly large files?
 * (Granted, the fact that this checks to make sure the input is a .tsv file
 * is probably a sufficient safeguard from that scenario; since this is a
 * client-side application, if the user is really determined to somehow
 * upload a really large file here then this browser tab/instance will just
 * run out of memory, which is an inherently isolated problem.)
 */
function importColorSettings() {
    "use strict";
    var csfr = new FileReader();
    var inputfile = document.getElementById("colorSettingsFS").files[0];
    if (inputfile === undefined) {
        return;
    }
    if (inputfile.name.toLowerCase().endsWith(".tsv")) {
        csfr.onload = function (e) {
            if (e.target.readyState === FileReader.DONE) {
                var fileText = e.target.result;
                // read file, synthesize colorpickers
                integrateColorSettings(fileText);
                // Clear .value attr to allow the same file (with changes
                // made) to be uploaded twice in a row
                document.getElementById("colorSettingsFS").value = "";
            }
        };
        csfr.readAsText(inputfile);
    } else {
        alert("Please select a valid .tsv color settings file to load.");
    }
}

function clearSelectedInfo() {
    "use strict";
    $("#nodeInfoTable tr.nonheader").remove();
    $("#edgeInfoTable tr.nonheader").remove();
    $("#clusterInfoTable tr.nonheader").remove();
    if ($("#nodeOpener").hasClass("glyphicon-triangle-bottom")) {
        toggleEleInfo("node");
    }
    if ($("#edgeOpener").hasClass("glyphicon-triangle-bottom")) {
        toggleEleInfo("edge");
    }
    if ($("#clusterOpener").hasClass("glyphicon-triangle-bottom")) {
        toggleEleInfo("cluster");
    }
}

/* Opens the dialog for filtering edges. */
function openEdgeFilteringDialog() {
    "use strict";
    $("#edgeFilteringDialog").modal();
    drawEdgeWeightHistogram();
}

/* CODELINK: This code was mostly taken from Mike Bostock's example of d3.js'
 * histogram generation, available at https://gist.github.com/mbostock/3048450.
 * (Update: this example has since been moved to Observable at
 * https://beta.observablehq.com/@mbostock/d3-histogram.)
 */
function drawEdgeWeightHistogram() {
    "use strict";
    var formatCount = d3.format(",.0f");
    // note could probably find this inline to simplify computation time
    var max = d3.max(mgsc.COMPONENT_EDGE_WEIGHTS);
    //console.log(mgsc.COMPONENT_EDGE_WEIGHTS);
    var margin = { top: 10, right: 30, bottom: 50, left: 70 };
    //for (var i = 0; i < mgsc.COMPONENT_EDGE_WEIGHTS.length; i++) {
    //    console.log(mgsc.COMPONENT_EDGE_WEIGHTS[i] + "->" + data[i]);
    //}
    // Remove old histogram so that it doesn't get drawn over
    // Eventually we might want to consider only redrawing the histogram when
    // we open up a new cc, but for now it's fine
    d3.select("#edgeWeightChart *").remove();
    var chartSvg = d3.select("#edgeWeightChart");
    var width = +chartSvg.attr("width") - margin.left - margin.right;
    var height = +chartSvg.attr("height") - margin.top - margin.bottom;
    var g = chartSvg
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");
    var x = d3
        .scaleLinear()
        .domain([0, max * 1.1])
        .rangeRound([0, width]);
    var bin_count = +$("#binCountInput").val();
    var bins = d3.histogram().domain(x.domain()).thresholds(x.ticks(bin_count))(
        mgsc.COMPONENT_EDGE_WEIGHTS
    );
    var y = d3
        .scaleLinear()
        .domain([
            0,
            d3.max(bins, function (b) {
                return b.length;
            }),
        ])
        .range([height, 0]);
    var bar = g
        .selectAll(".edge_chart_bar")
        .data(bins)
        .enter()
        .append("g")
        .attr("class", "edge_chart_bar")
        .attr("transform", function (b) {
            return "translate(" + x(b.x0) + "," + y(b.length) + ")";
        });
    bar.append("rect")
        .attr("x", 1)
        .attr("width", function (d) {
            return x(d.x1) - x(d.x0) - 1;
        })
        .attr("height", function (d) {
            return height - y(d.length);
        });

    var xAxis = d3.axisBottom(x);
    var yAxis = d3.axisLeft(y);
    g.append("g")
        .attr("class", "axis axis--x")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis);
    g.append("g").attr("class", "axis axis--y").call(yAxis);
    // Add x-axis label
    g.append("text")
        .attr(
            "transform",
            "translate(" + width / 2 + "," + (height + margin.top + 30) + ")"
        )
        .style("text-anchor", "middle")
        .text("Edge multiplicity");
    // Add y-axis label
    g.append("text")
        .attr("transform", "rotate(-90)")
        .attr("y", 0 - margin.left)
        .attr("x", 0 - height / 2)
        .attr("dy", "1em")
        .style("text-anchor", "middle")
        .text("Frequency");
    // TODO: ensure that the y-axis only has ticks for integer values;
    // ensure that all bars have proper widths (?)
}

/* Hides edges below a minimum edge weight (multiplicity or bundle size,
 * depending on the assembly graph that has been loaded).
 * This should only be called if the assembly graph that has been loaded has
 * edge weights as a property (e.g. LastGraph or MetaCarvel GML graphs).
 */
function cullEdges() {
    "use strict";
    var strVal = $("#cullEdgesInput").val();
    // Check that the input is a nonnegative integer
    // (parseInt() is pretty lax)
    // TODO: use utils.isValidInteger()
    if (strVal.match(mgsc.INTEGER_RE) === null) {
        alert(
            "Please enter a valid minimum edge weight (a nonnegative " +
                "integer) using the input field."
        );
        return;
    }
    var threshold = parseInt(strVal);
    // Use mgsc.PREV_EDGE_WEIGHT_THRESHOLD to prevent redundant operations being
    // done when the user double-clicks this button
    if (mgsc.PREV_EDGE_WEIGHT_THRESHOLD !== threshold) {
        cy.startBatch();
        // Restore removed edges that would fit within a lowered threshold
        // Also, remove these edges from mgsc.REMOVED_EDGES
        var restoredEdges = cy.collection();
        mgsc.REMOVED_EDGES.each(function (e, i) {
            if (e.data("multiplicity") >= threshold) {
                // If the edge points to/from a node within a collapsed
                // cluster, then make the edge a basicbezier and move the
                // edge to point to the cluster accordingly.
                // TODO, consult point 2 on issue #161
                if (e.source().removed()) {
                    e.removeClass("unbundledbezier");
                    e.addClass("basicbezier");
                    e.move({ source: e.source().data("parent") });
                }
                if (e.target().removed()) {
                    e.removeClass("unbundledbezier");
                    e.addClass("basicbezier");
                    e.move({ target: e.target().data("parent") });
                }
                e.restore();
                restoredEdges = restoredEdges.union(e);
            }
        });
        mgsc.REMOVED_EDGES = mgsc.REMOVED_EDGES.difference(restoredEdges);
        // Remove edges that have multiplicity less than the specified
        // threshold
        cy.$("edge").each(function (e, i) {
            var mult = e.data("multiplicity");
            if (mult !== null && mult < threshold) {
                if (e.selected()) e.unselect();
                mgsc.REMOVED_EDGES = mgsc.REMOVED_EDGES.union(e.remove());
            }
        });
        cy.endBatch();
        mgsc.PREV_EDGE_WEIGHT_THRESHOLD = threshold;
    }
}

/* Called when the user clicks on a node (including clusters) when finishing
 * is ongoing. We want to add a node to the current path if and only if the
 * node to be added in question is:
 *  -directly linked to the previous node on the path via a single incoming edge
 *   extending from the previous node
 *  -either a normal non-cluster node, or (if a cluster) collapsed
 *
 * We also support "autofinishing," wherein unambiguous outgoing connections
 * are automatically travelled along -- thus reducing user effort in finishing
 * paths.
 */
function addNodeFromEventToPath(e) {
    "use strict";
    var node = e.target;
    // When "autofinishing" starts, we record a list of all nodes/node IDs
    // seen. Upon a redundant node being reached (the first time we get to a
    // node that we've already seen in this autofinishing iteration), we should
    // stop, to avoid infinite looping.
    //
    // This approach should be a consistent solution. It's not always safe to
    // rely on cyclic chain detection, for example, since cyclic chain
    // identification can be stopped by things like user-defined misc.
    // patterns. We're not 100% guaranteed cyclic chains always exist where
    // they "should" -- hence our need to do some extra exploratory work here.
    if (!(node.hasClass("cluster") && !node.data("isCollapsed"))) {
        // Don't add uncollapsed clusters, but allow collapsed clusters to be
        // added
        var nodeID = node.id();
        // Have we already selected another node in this finishing process?
        if (mgsc.FINISHING_NODE_IDS.length > 0) {
            // Is the node the user just clicked on valid, in terms of the path
            // so far?
            if (mgsc.NEXT_NODES.is("#" + nodeID)) {
                cy.startBatch();
                mgsc.NEXT_NODES.removeClass("tentative");
                cy.endBatch();
            } else {
                return;
            }
        }
        // In any case, if we've gotten here then we know that we're ok to go
        // ahead with adding node(s) to the path.
        mgsc.NEXT_NODES = node.outgoers("node");
        // Although they don't technically have an edge to themselves when
        // they're collapsed, we consider collapsed cyclic chains as
        // effectively having such an edge. This enables the user to manually
        // expand things like tandem repeats as much as they want to.
        if (node.hasClass("Y")) {
            mgsc.NEXT_NODES = mgsc.NEXT_NODES.union(node);
        }
        var size = mgsc.NEXT_NODES.size();
        // Start autofinishing, if the node we're adding to the path only has
        // one outgoing connection (and it isn't to itself)
        var reachedCycleInAutofinishing = false;
        if (size === 1 && mgsc.NEXT_NODES[0].id() !== nodeID) {
            var autofinishingSeenNodeIDs = [];
            while (size === 1) {
                if (mgsc.FINISHING_NODE_OBJS.length > 0) {
                    $("#assembledNodes").append(", " + nodeID);
                    mgsc.FINISHING_NODE_IDS += "," + nodeID;
                } else {
                    $("#assembledNodes").append(nodeID);
                    mgsc.FINISHING_NODE_IDS += nodeID;
                }
                node.addClass("currpath");
                mgsc.FINISHING_NODE_OBJS.push(node);
                autofinishingSeenNodeIDs.push(nodeID);
                node = mgsc.NEXT_NODES[0];
                nodeID = node.id();
                // Have we reached a node that we've previously visited in this
                // autofinishing iteration? If so, stop autofinishing -- we're
                // currently stuck in a cycle.
                if (autofinishingSeenNodeIDs.indexOf(nodeID) !== -1) {
                    reachedCycleInAutofinishing = true;
                    break;
                }
                // Otherwise, we can carry on with the finishing for now.
                mgsc.NEXT_NODES = node.outgoers("node");
                // Allow for cyclic chains to be considered, as above
                if (node.hasClass("Y")) {
                    mgsc.NEXT_NODES = mgsc.NEXT_NODES.union(node);
                }
                size = mgsc.NEXT_NODES.size();
            }
        }
        if (reachedCycleInAutofinishing) {
            // Don't bother adding any more nodes to the path; we stopped
            // autofinishing because we reached an unambiguous cycle.
            markTentativeNodes();
            return;
        }
        // Either add the single node the user chose (if autofinishing didn't
        // happen), or add the final node in the autofinished path (if
        // autofinishing did happen, and it ended due to the path branching).
        if (mgsc.FINISHING_NODE_OBJS.length > 0) {
            $("#assembledNodes").append(", " + nodeID);
            mgsc.FINISHING_NODE_IDS += "," + nodeID;
        } else {
            $("#assembledNodes").append(nodeID);
            mgsc.FINISHING_NODE_IDS += nodeID;
        }
        node.addClass("currpath");
        mgsc.FINISHING_NODE_OBJS.push(node);
        if (size === 0) {
            endFinishing();
        } else {
            markTentativeNodes();
        }
    }
}

function markTentativeNodes() {
    "use strict";
    cy.startBatch();
    mgsc.NEXT_NODES.addClass("tentative");
    cy.endBatch();
    if ($("#animateFinishingCheckbox").prop("checked")) {
        // We enforce a maximum zoom level before the fitting animation here so
        // that we don't zoom in *too* far to a region in the graph. If the
        // collection of mgsc.NEXT_NODES is small and densely focused in one region
        // of the drawing, then fitting to just that region won't help the user
        // get much context for the surrounding parts of the graph (which will
        // often make the user zoom out, to get some context on where these
        // paths lead before making their next choice).
        //
        // And just adding padding to the viewport after finishing isn't an
        // acceptable solution for the general case: if the collection of
        // mgsc.NEXT_NODES covers a broad enough region of the graph, we don't
        // want to zoom out even farther since the user wouldn't gain much
        // from that. (And it might make it harder for the user to see which
        // nodes are marked as mgsc.NEXT_NODES.)
        //
        // The solution (CODELINK: idea c/o Max Franz' first answer here:
        // https://github.com/cytoscape/cytoscape.js/issues/941) is to impose a
        // maxZoom limit before the fitting operation, and then reset that
        // limit to its prior value after the fitting operation.
        //
        // NOTE we use parseFloat() because cy.maxZoom() seems to require
        // numeric inputs
        cy.maxZoom(parseFloat($("#maxFinishingZoomLvl").val()));
        cy.animate({ fit: { eles: mgsc.NEXT_NODES }, complete: resetMaxZoom });
    }
}

function resetMaxZoom() {
    "use strict";
    cy.maxZoom(mgsc.MAX_ZOOM_ORDINARY);
}

/* If onOrOff >= 0, removes graph properties (pauses/stops finishing).
 * If pauseOrFinish < 0, adds graph properties (resumes/starts finishing).
 */
function toggleFinishingGraphProperties(onOrOff) {
    "use strict";
    if (onOrOff >= 0) {
        cy.autounselectify(false);
        cy.off("tap");
    } else {
        // TODO can make this more efficient -- see #115, etc.
        cy.filter(":selected").unselect();
        cy.autounselectify(true);
        cy.on("tap", "node", addNodeFromEventToPath);
    }
}

function startFinishing() {
    "use strict";
    if (!mgsc.FINISHING_MODE_ON) {
        disableButton("startFinishingButton");
        if (mgsc.FINISHING_MODE_PREVIOUSLY_DONE) {
            mgsc.FINISHING_NODE_IDS = "";
            mgsc.FINISHING_NODE_OBJS = [];
            $("#assembledNodes").empty();
            disableButton("exportPathButton");
        }
        mgsc.FINISHING_MODE_ON = true;
        toggleFinishingGraphProperties(-1);
    }
    enableButton("pauseFinishingButton");
    enableButton("endFinishingButton");
}

/* Changes the style of the "pause finishing" button. Doesn't actually
 * modify any of the finishing mode's behavior -- just alters the button style.
 * If pauseOrFinish < 0, sets everything to say "Pause" (i.e. the user just
 * selected the "resume" option).
 * If pauseOrFinish >= 0, sets everything to say "Resume" (i.e. the user just
 * selected the "pause" option).
 */
function togglePauseFinishingButtonStyle(pauseOrFinish) {
    "use strict";
    if (pauseOrFinish < 0) {
        $("#pauseFinishingButtonIconSpan").addClass("glyphicon-pause");
        $("#pauseFinishingButtonIconSpan").removeClass("glyphicon-play");
        $("#pauseFinishingButton").html(
            $("#pauseFinishingButton").html().replace("Resume", "Pause")
        );
    } else {
        $("#pauseFinishingButtonIconSpan").removeClass("glyphicon-pause");
        $("#pauseFinishingButtonIconSpan").addClass("glyphicon-play");
        $("#pauseFinishingButton").html(
            $("#pauseFinishingButton").html().replace("Pause", "Resume")
        );
    }
}

/* Detects if the finishing mode is paused or unpaused, and switches its state
 * (and the pause button style, via calling togglePauseFinishingButtonStyle())
 * accordingly.
 */
function togglePauseFinishing() {
    "use strict";
    if ($("#pauseFinishingButtonIconSpan").hasClass("glyphicon-pause")) {
        togglePauseFinishingButtonStyle(1);
        toggleFinishingGraphProperties(1);
    } else {
        togglePauseFinishingButtonStyle(-1);
        toggleFinishingGraphProperties(-1);
    }
}

function endFinishing() {
    "use strict";
    mgsc.FINISHING_MODE_ON = false;
    mgsc.FINISHING_MODE_PREVIOUSLY_DONE = true;
    cy.startBatch();
    mgsc.NEXT_NODES.removeClass("tentative");
    // Remove "currpath" class from all nodes that have it (i.e. look at
    // mgsc.FINISHING_NODE_OBJS)
    for (var n = 0; n < mgsc.FINISHING_NODE_OBJS.length; n++) {
        mgsc.FINISHING_NODE_OBJS[n].removeClass("currpath");
    }
    cy.endBatch();
    mgsc.NEXT_NODES = cy.collection();
    toggleFinishingGraphProperties(1);
    if (mgsc.FINISHING_NODE_OBJS.length > 0) {
        enableButton("exportPathButton");
    }
    enableButton("startFinishingButton");
    togglePauseFinishingButtonStyle(-1);
    disableButton("pauseFinishingButton");
    disableButton("endFinishingButton");
}

function exportPath() {
    "use strict";
    var exportFileType = $("#pathExportButtonGroup .btn.active").attr("value");
    var textToExport = "";
    if (exportFileType === "AGP") {
        // export AGP
        var nextStartPos = 1;
        var nextEndPos;
        var nodeLen, nodeOrient, nodeKey;
        var componentType;
        for (var i = 0; i < mgsc.FINISHING_NODE_OBJS.length; i++) {
            nodeLen = mgsc.FINISHING_NODE_OBJS[i].data("length");
            // NOTE that we assume that nodes with the "rightdir" class must
            // all have a forward orientation. If dynamic graph rotation
            // gets added back in, that will break this.
            // (In that case, the ideal solution would be to just give
            // forward-oriented nodes a "is_fwd" data() attribute or
            // something.)
            componentType = "W"; // for "WGS contig"
            if (mgsc.FINISHING_NODE_OBJS[i].hasClass("cluster")) {
                nodeOrient = "na";
                componentType = "O"; // for "Other sequence"
            } else if (mgsc.FINISHING_NODE_OBJS[i].hasClass("rightdir")) {
                nodeOrient = "+";
            } else {
                nodeOrient = "-";
            }
            // Since node groups and nodes from non-GML inputs don't have
            // label data, use these objects' IDs instead.
            if (componentType === "W" && mgsc.ASM_FILETYPE === "GML") {
                nodeKey = mgsc.FINISHING_NODE_OBJS[i].data("label");
            } else {
                nodeKey = mgsc.FINISHING_NODE_OBJS[i].id();
            }
            // Add a line for this node
            nextEndPos = nextStartPos - 1 + nodeLen;
            // TODO: keep track of how many scaffolds the user has created
            // from this graph (not component) as a global-ish number variable,
            // then use that when populating an AGP file with many scaffolds.
            textToExport +=
                "scaffold\t" +
                nextStartPos +
                "\t" +
                nextEndPos +
                "\t" +
                (i + 1) +
                "\t" +
                componentType +
                "\t" +
                nodeKey +
                "\t1\t" +
                nodeLen +
                "\t" +
                nodeOrient +
                "\n";
            nextStartPos = nextEndPos + 1;
        }
        downloadDataURI("path.agp", textToExport, true);
    } else {
        // export CSV
        textToExport = mgsc.FINISHING_NODE_IDS;
        downloadDataURI("path.csv", textToExport, true);
    }
}

function startChangeNodeColorization() {
    "use strict";
    var newColorization = $(
        "#nodeColorizationRadioButtonGroup input:checked"
    ).attr("value");
    // We check to ensure the new colorization would be different from the
    // current one -- if not, we don't bother doing anything
    if (newColorization !== mgsc.CURR_NODE_COLORIZATION) {
        startIndeterminateProgressBar();
        window.setTimeout(function () {
            changeNodeColorization(newColorization);
            finishProgressBar();
        }, 50);
    }
}

function changeNodeColorization(newColorization) {
    "use strict";
    cy.startBatch();
    cy.filter("node.noncluster")
        .removeClass(mgsc.CURR_NODE_COLORIZATION)
        .addClass(newColorization);
    // Make sure to apply the colorization to collapsed nodes, also!
    cy.scratch("_collapsed").each(function (nodeGroup, i) {
        nodeGroup
            .scratch("_interiorNodes")
            .removeClass(mgsc.CURR_NODE_COLORIZATION)
            .addClass(newColorization);
    });
    mgsc.CURR_NODE_COLORIZATION = newColorization;
    cy.endBatch();
}

/* Redraws the gradient preview for node colorization.
 * If minOrMax is -1, then we use hexColor as the new minimum color.
 * Otherwise, we use hexColor as the new maximum color.
 */
function redrawGradientPreview(hexColor, minOrMax) {
    "use strict";
    var tmpColor;
    if (minOrMax === -1) {
        $("#0gp").css("background-color", hexColor);
        mgsc.MIN_RGB = $("#mincncp").data("colorpicker").color.toRGB();
        mgsc.MIN_HEX = hexColor;
        if (mgsc.MAX_RGB === undefined) {
            tmpColor = $("#maxcncp").data("colorpicker").color;
            mgsc.MAX_RGB = tmpColor.toRGB();
            mgsc.MAX_HEX = tmpColor.toHex();
        }
    } else {
        $("#100gp").css("background-color", hexColor);
        mgsc.MAX_RGB = $("#maxcncp").data("colorpicker").color.toRGB();
        mgsc.MAX_HEX = hexColor;
        if (mgsc.MIN_RGB === undefined) {
            tmpColor = $("#mincncp").data("colorpicker").color;
            mgsc.MIN_RGB = tmpColor.toRGB();
            mgsc.MIN_HEX = tmpColor.toHex();
        }
    }
    // Change intermediate colors in the gradient
    $("#25gp").css("background-color", util.getNodeColorization(0.25));
    $("#50gp").css("background-color", util.getNodeColorization(0.5));
    $("#75gp").css("background-color", util.getNodeColorization(0.75));
}

// Allows user to test one of Cytoscape.js' predefined layouts
function testLayout() {
    "use strict";
    if ($("#layoutInput").val() !== "") {
        startIndeterminateProgressBar();
        cy.minZoom(0);
        window.setTimeout(function () {
            // Change to simple bezier edges, since node placement
            // will be changed
            // Adjust min zoom to scope of new layout
            reduceEdgesToStraightLines(false);
            cy.layout({
                name: $("#layoutInput").val(),
                fit: true,
                padding: 0,
                stop: function () {
                    finishProgressBar();
                },
            }).run();
        }, 20);
    }
}

/* Reduces all unbundledbezier edges to basicbezier edges.
 * I guess it'd be nice to eventually add in support to revert these edges to
 * their unbundledbezier forms, but that might require some extra logic
 * (due to collapsing/uncollapsing -- similar to the issues we ran into with
 * hiding/unhiding edges below/above a certain multiplicity).
 *
 * If useProgressBar is true, then an indeterminate progress bar will be
 * started and finished before/after reducing all edges. If useProgressBar is
 * false, then the progress bar will not be triggered.
 */
function reduceEdgesToStraightLines(useProgressBar) {
    "use strict";
    if (useProgressBar) {
        startIndeterminateProgressBar();
        window.setTimeout(function () {
            doReduceEdges();
            finishProgressBar();
        }, 50);
    } else {
        doReduceEdges();
    }
}

/* Actually does the work of reducing edges. */
function doReduceEdges() {
    "use strict";
    cy.startBatch();
    var reducingFunction = function (e, i) {
        e.removeClass("unbundledbezier");
        e.addClass("reducededge");
        e.addClass("basicbezier");
    };

    // We can safely use the reducingFunction even on non-unbundledbezier
    // edges. The reason we don't restrict the first cy.filter() to
    // unbundledbezier edges is that we want to apply this even to
    // unbundledbezier edges that have been temporarily reduced to basicbezier
    // edges due to node group collapsing.
    cy.filter("edge").each(reducingFunction);
    mgsc.REMOVED_EDGES.each(reducingFunction);
    cy.endBatch();
}

/* Determines whether collapsing or uncollapsing should be performed,
 * updates the status div accordingly, and begins the (un)collasping
 * process.
 */
function startCollapseAll() {
    "use strict";
    if (mgsc.CURR_VIEWTYPE !== "SPQR") {
        var currVal = $("#collapseButtonText").text();
        startIndeterminateProgressBar();
        window.setTimeout(function () {
            collapseAll(currVal[0]);
        }, 50);
    }
}

/* Collapse/uncollapse all compound nodes in the graph.
 * This just delegates to collapseCluster() and uncollapseCluster().
 * An argument of 'U' uncollapses all nodes, and an argument of 'C' (or
 * anything that isn't 'U') collapses all nodes.
 */
function collapseAll(operationCharacter) {
    "use strict";
    cy.startBatch();
    if (operationCharacter === "U") {
        cy.scratch("_collapsed").each(function (cluster, i) {
            uncollapseCluster(cluster);
        });
    } else {
        cy.scratch("_uncollapsed").each(function (cluster, i) {
            collapseCluster(cluster);
        });
    }
    finishProgressBar();
    cy.endBatch();
}

/* NOTE -- this is an unused function right now. Could be useful in the future,
 * perhaps.
 * Initializes the adjacent edges (i.e. incoming + outgoing edges) of
 * every non-cluster node in the graph. This would be useful if we
 * enabled dynamic edge validity checking (it makes checking each node's
 * edges more efficient, since we only have to build up these collections
 * once), but for now dynamic edge validity checking is disabled due to
 * still being too slow.
 */
function initNodeAdjacents() {
    "use strict";
    cy.filter("node.noncluster").each(function (node, i) {
        node.data(
            "adjacentEdges",
            node.incomers("edge").union(node.outgoers("edge"))
        );
    });
}

// Records actual and canonical incoming/outgoing edges of clusters in the
// data of the cluster, as incomingEdges and outgoingEdges (actual
// edges in the graph) and cSource and cTarget (canonical source/target).
// This is going to involve iterating over every compound node in the graph.
// See collapse() for guidance on how to do that, I guess.
// NOTE that we delay doing this work until after everything else has been
// rendered in order to ensure that all edges/nodes necessary for this have
// already been rendered.
function initClusters() {
    "use strict";
    // For each compound node...
    cy.scratch("_uncollapsed").each(function (node, i) {
        var children = node.children();
        // Unfiltered incoming/outgoing edges
        var uIncomingEdges = children.incomers("edge");
        var uOutgoingEdges = children.outgoers("edge");
        // Actual incoming/outgoing edges -- will be move()'d as
        // this cluster/adjacent cluster(s) are collapsed/uncollapsed
        var incomingEdges = uIncomingEdges.difference(uOutgoingEdges);
        var outgoingEdges = uOutgoingEdges.difference(uIncomingEdges);
        // Mapping of edge ID to [cSource, cTarget]
        // Used since move() removes references to edges, so storing IDs
        // is more permanent
        var incomingEdgeMap = {};
        var outgoingEdgeMap = {};
        // "Canonical" incoming/outgoing edge properties -- these
        // are used to represent the ideal connections
        // between nodes regardless of collapsing
        incomingEdges.each(function (edge, j) {
            incomingEdgeMap[edge.id()] = [
                edge.source().id(),
                edge.target().id(),
            ];
        });
        outgoingEdges.each(function (edge, j) {
            outgoingEdgeMap[edge.id()] = [
                edge.source().id(),
                edge.target().id(),
            ];
        });
        // Get the "interior elements" of the cluster: all child nodes,
        // plus the edges connecting child nodes within the cluster
        // This considers cyclic edges (e.g. the edge connecting a
        // cycle's "end" and "start" nodes) as "interior elements,"
        // which makes sense as they don't connect the cycle's children
        //  to any elements outside the cycle.
        var interiorEdges = children
            .connectedEdges()
            .difference(incomingEdges)
            .difference(outgoingEdges);
        // Record incoming/outgoing edges in this
        // cluster's data. Will be useful during collapsing.
        // We also record "interiorNodes" -- having a reference to just
        // these nodes saves us the time of filtering nodes out of
        // interiorEles when rotating collapsed node groups.
        node.data({
            incomingEdgeMap: incomingEdgeMap,
            outgoingEdgeMap: outgoingEdgeMap,
            interiorNodeCount: children.size(),
            w: node.scratch("_w"),
            h: node.scratch("_h"),
        });
        node.removeScratch("_w");
        node.removeScratch("_h");
        // We store collections of elements in the cluster's scratch data.
        // Storing it in the main "data" section will mess up the JSON
        // exporting, since it isn't serializable.
        // TODO reduce redundancy here -- only store interiorEles, and in
        // rotateNodes just select nodes from interiorEles
        node.scratch({
            _interiorEles: interiorEdges.union(children),
            _interiorNodes: children,
        });
    });
    // Also set up the list of clusters sorted from left to right in the
    // component
    mgsc.CLUSTERID2TOP.sort(function (c1, c2) {
        return c2.t - c1.t;
    });
}

// Draws two nodes that "enforce" the given bounding box.
function drawBoundingBoxEnforcingNodes(boundingboxObject) {
    "use strict";
    var bb = [boundingboxObject.boundingbox_x, boundingboxObject.boundingbox_y];
    var bottomLeftPt = util.gv2cyPoint(0, 0, bb);
    var topRightPt = util.gv2cyPoint(bb[0], bb[1], bb);
    cy.add({
        classes: "bb_enforcing",
        data: { id: "bottom_left" },
        position: { x: bottomLeftPt[0], y: bottomLeftPt[1] },
    });
    cy.add({
        classes: "bb_enforcing",
        data: { id: "top_right" },
        position: { x: topRightPt[0], y: topRightPt[1] },
    });
}

function removeBoundingBoxEnforcingNodes() {
    "use strict";
    cy.$("node.bb_enforcing").remove();
}
