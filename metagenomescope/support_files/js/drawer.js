define([
    "jquery",
    "underscore",
    "cytoscape",
    "cytoscape-expand-collapse",
    "utils",
], function ($, _, cytoscape, cyEC, utils) {
    class Drawer {
        /**
         * Constructs a Drawer.
         *
         * This object is used for drawing elements and for interfacing
         * directly with Cytoscape.js. It also accepts a few callback functions
         * that we'll call when certain things in the graph happen, so that we
         * can update the state of the rest of the application.
         *
         * @param {String} cyDivID ID of the <div> which will contain the
         *                         Cytoscape.js display.
         *
         * @param {Function} onSelect Function to be called when an element in
         *                            the graph is selected.
         *
         * @param {Function} onUnselect Function to be called when an element
         *                              in the graph is unselected/deselected.
         *
         * @param {Function} onTogglePatternCollapse Function to be called when
         *                                           a pattern in the graph is
         *                                           right-clicked, to be
         *                                           either collapsed or
         *                                           uncollapsed.
         *
         * @param {Function} onDestroy Function to be called when the graph is
         *                             destroyed (i.e. when the user presses
         *                             the "Draw" button, and stuff is already
         *                             drawn that needs to be removed).
         */
        constructor(
            cyDivID,
            onSelect,
            onUnselect,
            onTogglePatternCollapse,
            onDestroy
        ) {
            this.cyDivID = cyDivID;
            this.cyDiv = $("#" + cyDivID);
            // Instance of Cytoscape.js
            this.cy = null;
            // Instance of the Cytoscape.js expand/collapse extension
            this.cyEC = null;

            // "Register" extensions with Cytoscape.js
            cyEC(cytoscape);

            this.bgColor = undefined;

            this.onSelect = onSelect;
            this.onUnselect = onUnselect;
            this.onTogglePatternCollapse = onTogglePatternCollapse;
            this.onDestroy = onDestroy;

            // Some numbers indicating the number of elements currently drawn.
            // Useful for things like figuring out whether or not all patterns
            // are currently collapsed.
            this.numDrawnNodes = 0;
            this.numDrawnEdges = 0;
            this.numDrawnPatterns = 0;

            // Maps node names to an array of their parent pattern ID(s).
            // For most node names, the array will just have a single ID, but
            // for duplicate node names split across multiple patterns this
            // array will have two elements (at most two, I think, but I don't
            // want to try to prove that to myself right now ._.).
            // This corresponds to the "_ele2parent" scratch object in the old
            // version of MetagenomeScope.
            this.nodeName2parent = {};

            // Various constants
            //
            // Anything less than this constant will be considered a "straight"
            // control point distance. This way we can approximate simple
            // B-splines with straight bezier curves (which are cheaper and
            // easier to draw).
            this.CTRL_PT_DIST_EPSILON = 5.0;
            // Edge thickness stuff, as will be rendered by Cytoscape.js. Used
            // in tandem with the "relative_weight" (formerly "thickness")
            // value associated with each edge to scale edges' displayed
            // "weights" accordingly.
            this.MIN_EDGE_THICKNESS = 3;
            this.MAX_EDGE_THICKNESS = 10;
            this.EDGE_THICKNESS_RANGE =
                this.MAX_EDGE_THICKNESS - this.MIN_EDGE_THICKNESS;

            this.COMPONENT_PADDING = 200;

            // Used for debugging
            this.VERBOSE = false;
        }

        /**
         * Destroys the instance of Cytoscape.js, in order to prepare for
         * drawing another part of the graph (or just the same part again I
         * guess, since that is the user's prerogative).
         */
        destroyGraph() {
            this.cy.destroy();
            this.numDrawnNodes = 0;
            this.numDrawnEdges = 0;
            this.numDrawnPatterns = 0;
            this.nodeName2parent = {};
            this.onDestroy();
        }

        /**
         * Creates an instance of Cytoscape.js to which we can add elements.
         *
         * Also calls setGraphBindings().
         */
        initGraph() {
            // Update the bg color only when we call initGraph(). This ensures
            // that we have the currently-used background color on hand, for
            // stuff like exporting where we need to know the background color
            this.bgColor = $("#bgcp").colorpicker("getValue");
            this.cyDiv.css("background", this.bgColor);
            this.cy = cytoscape({
                container: document.getElementById(this.cyDivID),
                layout: { name: "preset" },
                // TODO: this should be a config-level thing (should we make a
                // Config object or file or whatever?) rather than hardcoded
                // here
                maxZoom: 9,
                // TODO: hideEdgesOnViewport and textureOnViewport
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
                            "z-index-compare": "manual",
                        },
                    },
                    // The following few classes are used to set properties of
                    // patterns
                    {
                        selector: "node.pattern",
                        style: {
                            shape: "rectangle",
                            "border-width": 2,
                            "border-color": "#000000",
                            "padding-top": 0,
                            "padding-right": 0,
                            "padding-left": 0,
                            "padding-bottom": 0,
                        },
                    },
                    {
                        // Give collapsed patterns a number indicating child count
                        selector: "node.pattern[?isCollapsed]",
                        style: {
                            "min-zoomed-font-size": 12,
                            "font-size": 48,
                            label: "data(collapsedLabel)",
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
                            "background-color": $("#fropecp").colorpicker(
                                "getValue"
                            ),
                            shape: "polygon",
                            // Defines a "sideways hourglass" pattern.
                            // This is intended to be used when the graph is
                            // displayed from left to right or right to left.
                            // If the graph is rotated, these points should
                            // also be (this distinction is made in the old
                            // codebase -- see the
                            // mgsc.FRAYED_ROPE_LEFTRIGHTDIR and _UPDOWNDIR
                            // variables).
                            //
                            // |\/|
                            // |  |
                            // |/\|
                            "shape-polygon-points":
                                "-1 -1 0 -0.5 1 -1 1 1 0 0.5 -1 1",
                        },
                    },
                    {
                        selector: "node.B",
                        style: {
                            // default color matches 'cornflowerblue' in graphviz
                            "background-color": $("#bubblecp").colorpicker(
                                "getValue"
                            ),
                            shape: "polygon",
                            // Defines a hexagon pattern. Notes about the
                            // polygon points for frayed ropes above apply.
                            //  ___
                            // /   \
                            // \___/
                            "shape-polygon-points":
                                "-1 0 -0.5 -1 0.5 -1 1 0 0.5 1 -0.5 1",
                        },
                    },
                    {
                        selector: "node.C",
                        style: {
                            // default color matches 'salmon' in graphviz
                            "background-color": $("#chaincp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "node.Y",
                        style: {
                            // default color matches 'darkgoldenrod1' in graphviz
                            "background-color": $("#ychaincp").colorpicker(
                                "getValue"
                            ),
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
                        // Nodes with the "basic" class, known in old versions
                        // of MetagenomeScope as "noncluster", are just regular
                        // nodes (i.e. not collapsed patterns that behave like
                        // nodes).
                        selector: "node.basic",
                        style: {
                            label: "data(nodeName)",
                            "text-valign": "center",
                            // rendering text is computationally expensive, so if
                            // we're zoomed out so much that the text would be
                            // illegible (or hard-to-read, at least) then don't
                            // render the text.
                            "min-zoomed-font-size": 12,
                            "z-index": 2,
                            "background-color": $("#usncp").colorpicker(
                                "getValue"
                            ),
                            // Uncomment this (and comment out the entry above)
                            // to use a random color for each node, provided
                            // these random color is generated in renderNode().
                            // (Keep in mind how dup nodes are labeled...)
                            // "background-color": "data(randColor)",
                        },
                    },
                    // TODO: add a generalized "colorized" class or something
                    // for coloring by GC content, coverage, ...
                    {
                        selector: "node.basic.leftdir",
                        style: {
                            // Represents a node pointing left (i.e. in the
                            // reverse direction, if the graph flows from left
                            // to right)
                            //  ___
                            // /   |
                            // \___|
                            shape: "polygon",
                            "shape-polygon-points":
                                "1 1 -0.23587 1 -1 0 -0.23587 -1 1 -1",
                        },
                    },
                    {
                        selector: "node.basic.rightdir",
                        style: {
                            // Represents a node pointing left (i.e. in the
                            // reverse direction, if the graph flows from left
                            // to right)
                            //  ___
                            // |   \
                            // |___/
                            shape: "polygon",
                            "shape-polygon-points":
                                "-1 1 0.23587 1 1 0 0.23587 -1 -1 -1",
                        },
                    },
                    // Just for debugging. For now, at least.
                    {
                        selector: "node.is_dup",
                        style: {
                            "background-color": "#cc00cc",
                        },
                    },
                    {
                        selector: "node.basic.tentative",
                        style: {
                            "border-width": 5,
                            "border-color": $("#tnbcp").colorpicker("getValue"),
                        },
                    },
                    {
                        selector: "node.pattern.tentative",
                        style: {
                            "border-width": 5,
                            "border-color": $("#tngbcp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "node.currpath",
                        style: {
                            "background-color": $("#cpcp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "node.basic:selected",
                        style: {
                            "background-color": $("#sncp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "node.basic.noncolorized:selected",
                        style: {
                            color: $("#snlcp").colorpicker("getValue"),
                        },
                    },
                    {
                        selector: "node.basic.gccolorized:selected",
                        style: {
                            color: $("#csnlcp").colorpicker("getValue"),
                        },
                    },
                    {
                        selector: "node.pattern:selected",
                        style: {
                            "border-width": 5,
                            "border-color": $("#sngbcp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "edge",
                        style: {
                            width: "data(thickness)",
                            "line-color": $("#usecp").colorpicker("getValue"),
                            "target-arrow-color": $("#usecp").colorpicker(
                                "getValue"
                            ),
                            "loop-direction": "30deg",
                            "z-index": 1,
                            "z-index-compare": "manual",
                            "target-arrow-shape": "triangle",
                            "target-endpoint": "-50% 0%",
                            "source-endpoint": "50% 0",
                        },
                    },
                    {
                        selector: "edge:selected",
                        style: {
                            "line-color": $("#secp").colorpicker("getValue"),
                            "target-arrow-color": $("#secp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "edge:loop",
                        style: {
                            "z-index": 5,
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
                        // Used for edges incident on collapsed patterns. These
                        // edges no longer have their control point data in
                        // use, so making them hit the tailport / headport of
                        // their source / target looks really gross. So we just
                        // say "screw it, any direction is ok."
                        selector: "edge.not_using_ports",
                        style: {
                            "source-endpoint": "outside-to-node",
                            "target-endpoint": "outside-to-node",
                        },
                    },
                    {
                        selector: "edge.is_dup",
                        style: {
                            "line-style": "dashed",
                        },
                    },
                    {
                        selector: "edge.high_outlier",
                        style: {
                            "line-color": $("#hoecp").colorpicker("getValue"),
                            "target-arrow-color": $("#hoecp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "edge.high_outlier:selected",
                        style: {
                            "line-color": $("#hosecp").colorpicker("getValue"),
                            "target-arrow-color": $("#hosecp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "edge.low_outlier",
                        style: {
                            "line-color": $("#loecp").colorpicker("getValue"),
                            "target-arrow-color": $("#loecp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                    {
                        selector: "edge.low_outlier:selected",
                        style: {
                            "line-color": $("#losecp").colorpicker("getValue"),
                            "target-arrow-color": $("#losecp").colorpicker(
                                "getValue"
                            ),
                        },
                    },
                ],
            });
            // Don't do any animation or movement of the graph view upon
            // toggling collapsing -- just change the thing being collapsed.
            this.cy.expandCollapse({
                animate: false,
                cueEnabled: false,
                fisheye: false,
            });
            // http://ivis-at-bilkent.github.io/cytoscape.js-expand-collapse/#api
            this.cyEC = this.cy.expandCollapse("get");
            this.setGraphBindings();
        }

        /**
         * Records incoming/outgoing edges and all interior elements of
         * patterns.
         *
         * Basically, this function sets up a bunch of details that will make
         * collapsing and uncollapsing a lot easier later on.
         *
         * This should be called after all elements (nodes, edges, patterns)
         * have been added to the Cytoscape.js instance, but before drawing is
         * finished (i.e. before the user can interact with the graph).
         *
         * This was previously known as initClusters() in the old version of
         * MetagenomeScope. As you may have noticed if you're reading over this
         * code, I was previously being inconsistent and periodically used the
         * terms "Node Group", "Cluster", "Pattern", etc. to refer to patterns.
         * I'm trying to just be consistent and say "Pattern" now :P
         */
        initPatterns() {
            // For each pattern...
            // TODO: compute descendant node count? or store that in the data
            // holder from python. idk.
            // Right now we compute *child* count, which is ok but not ideal
            this.cy.$("node.pattern").each(function (pattern, i) {
                var children = pattern.children();
                var numChildren = children.size();
                var collapsedLabel = numChildren + " child";
                if (numChildren > 1) {
                    collapsedLabel += "ren";
                }
                pattern.data({ collapsedLabel: collapsedLabel });
            });
        }

        renderPattern(pattAttrs, pattVals, dx, dy) {
            var pattID = pattVals[pattAttrs.pattern_id];
            var pattData = {
                id: pattID,
                w: pattVals[pattAttrs.width],
                h: pattVals[pattAttrs.height],
                isCollapsed: false,
            };

            // Add parent ID, if needed.
            // This is safe, because the data export from the python code
            // ensures that, for each parent pattern in a component, this
            // parent pattern is stored earlier in the pattern array than the
            // child pattern(s) within it.
            var parentID = pattVals[pattAttrs.parent_id];
            if (!_.isNull(parentID)) {
                pattData.parent = parentID;
            }

            var classes = "pattern";
            if (pattVals[pattAttrs.pattern_type] === "chain") {
                classes += " C";
            } else if (pattVals[pattAttrs.pattern_type] === "cyclicchain") {
                classes += " Y";
            } else if (pattVals[pattAttrs.pattern_type] === "bubble") {
                classes += " B";
            } else if (pattVals[pattAttrs.pattern_type] === "frayedrope") {
                classes += " F";
            } else {
                classes += " M";
            }
            var x =
                dx + (pattVals[pattAttrs.left] + pattVals[pattAttrs.right]) / 2;
            var y =
                dy - (pattVals[pattAttrs.bottom] + pattVals[pattAttrs.top]) / 2;
            this.cy.add({
                data: pattData,
                position: { x: x, y: y },
                classes: classes,
            });
            if (this.VERBOSE) {
                console.log(
                    "Rendered pattern " + pattID + " at (" + x + ", " + y + ")"
                );
            }
            this.numDrawnPatterns++;
        }

        /**
         * Produces a random hex color.
         *
         * @param {Number} minChannelVal Minimum value, in base 10, of any
         *                               R/G/B channel. Depending on the use
         *                               case for these colors, we may or may
         *                               not want to have this be above 0.
         *                               (e.g. for coloring nodes: we currently
         *                               just use black text to label nodes,
         *                               so we use a value of 50 for this to
         *                               make node labels easier to read.)
         *
         * @param {Number} maxChannelVal Maximum value, in base 10, of any
         *                               R/G/B channel. Similar considerations
         *                               as with minChannelVal apply.
         *
         * @return {String} hexColor In the format "#rrggbb".
         */
        randomColor(minChannelVal = 100, maxChannelVal = 205) {
            var channelRange = maxChannelVal - minChannelVal;
            var hexColor = "#";
            _.times(3, function () {
                var channel =
                    minChannelVal + Math.floor(Math.random() * channelRange);
                var hexChannel = channel.toString(16);
                if (hexChannel.length === 1) {
                    hexChannel = "0" + hexChannel;
                }
                hexColor += hexChannel;
            });
            return hexColor;
        }

        renderNode(nodeAttrs, nodeVals, nodeID, dx, dy) {
            var name = nodeVals[nodeAttrs.name];
            var nodeData = {
                id: nodeID,
                // We specifically use a "nodeName" field to avoid the
                // potential for internal conflicts between labels in collapsed
                // patterns and labels in nodes: if a "node" in the graph has a
                // "nodeName" field, it's gotta be a basic node.
                nodeName: name,
                length: nodeVals[nodeAttrs.length],
                w: nodeVals[nodeAttrs.width],
                h: nodeVals[nodeAttrs.height],
                // randColor: this.randomColor(),
            };

            // Store within parent, if needed
            var parentID = nodeVals[nodeAttrs.parent_id];
            if (!_.isNull(parentID)) {
                nodeData.parent = parentID;
                if (_.has(this.nodeName2parent, name)) {
                    this.nodeName2parent[name].push(parentID);
                } else {
                    this.nodeName2parent[name] = [parentID];
                }
            }

            // Figure out node orientation and shape
            var classes = "basic";
            var orientation = nodeVals[nodeAttrs.orientation];
            if (orientation === "+") {
                classes += " rightdir";
            } else if (orientation === "-") {
                classes += " leftdir";
            } else {
                throw new Error("Invalid node orientation " + orientation);
            }

            if (nodeVals[nodeAttrs.is_dup]) {
                classes += " is_dup";
            }

            var x = dx + nodeVals[nodeAttrs.x];
            var y = dy - nodeVals[nodeAttrs.y];
            var data = {
                data: nodeData,
                position: { x: x, y: y },
                classes: classes,
            };
            this.cy.add(data);
            if (this.VERBOSE) {
                console.log(
                    "Rendered node " +
                        nodeID +
                        " (name " +
                        name +
                        ") at (" +
                        x +
                        ", " +
                        y +
                        ")"
                );
            }
            this.numDrawnNodes++;
            return [x, y];
        }

        /**
         * Given a start node position, an end node position, and the
         * control points of an edge connecting the two nodes, converts
         * the control points into arrays of "distances" and "weights" that
         * Cytoscape.js can use when drawing an unbundled Bezier edge.
         *
         * For more information about what "distances" and "weights" mean in
         * this context (it's been so long since I first wrote this code that I
         * forget the details...), see Cytoscape.js' documentation at
         * https://js.cytoscape.org/#style/unbundled-bezier-edges. The Cliff
         * Notes explanation is that this is just a way of representing
         * control points besides literally just listing the control points, as
         * GraphViz does.
         *
         * Note that all of the Array parameters below should have only Numbers
         * as their values.
         *
         * @param {Array} srcPos Of the format [x, y].
         * @param {Array} tgtPos Of the format [x, y].
         * @param {Array} ctrlPts Of the format [x1, y1, x2, y2, ...].
         * @param {Number} dx Value to add to every control point x-coordinate
         * @param {Number} dy Value to add to every control point y-coordinate
         *
         * @return {Object} Has the following keys:
         *                  -complex: Maps to a Boolean. If this is true,
         *                   then this edge cannot be easily approximated with
         *                   a straight line, and an unbundled Bezier curve
         *                   should thus be drawn for this edge. If this is
         *                   false, then we can probably just draw a straight
         *                   line (i.e. using the class "basicbezier") for this
         *                   edge, and the "dists" and "weights" keys in this
         *                   Object can probably be ignored.
         *
         *                  -dists: Maps to an Array of Numbers representing
         *                   the distances from each control point to a line
         *                   from the source to the target position. Usable as
         *                   the "cpd" data attribute for unbundled bezier
         *                   edges.
         *
         *                  -weights: Maps to an Array of Numbers representing
         *                   the "weights" of each control point along a line
         *                   from the source to the target position. Usable as
         *                   the "cpw" data attribute for unbundled bezier
         *                   edges.
         */
        convertCtrlPtsToDistsAndWeights(srcPos, tgtPos, ctrlPts, dx, dy) {
            var srcTgtDist = utils.distance(srcPos, tgtPos);
            var complex = false;
            var ctrlPtDists = "";
            var ctrlPtWeights = "";
            var currPt, pld, pldsquared, dsp, dtp, w, ws, wt;
            for (var p = 0; p < ctrlPts.length; p += 2) {
                currPt = [dx + ctrlPts[p], dy - ctrlPts[p + 1]];
                pld = utils.pointToLineDistance(currPt, srcPos, tgtPos);
                pldsquared = Math.pow(pld, 2);
                dsp = utils.distance(currPt, srcPos);
                dtp = utils.distance(currPt, tgtPos);
                // By the pythagorean thm., the interior of the square root
                // below should always be positive -- the hypotenuse must
                // always be greater than both of the other sides of a right
                // triangle.
                // However, due to Javascript's lovely (...)
                // type system, rounding errors can cause the hypotenuse (dsp
                // or dtp)
                // be represented as slightly less than d. So, to account for
                // these cases, we just take the abs. value of the sqrt body.
                // NOTE that ws = distance on line to source;
                //           wt = distance on line to target
                ws = Math.sqrt(Math.abs(Math.pow(dsp, 2) - pldsquared));
                wt = Math.sqrt(Math.abs(Math.pow(dtp, 2) - pldsquared));
                // Get the weight of the control point on the line between
                // source and sink oriented properly -- if the control point is
                // "behind" the source node, we make it negative, and if the
                // point is "past" the sink node, we make it > 1. Everything in
                // between the source and sink falls within [0, 1] inclusive.
                if (wt > srcTgtDist && wt > ws) {
                    // The ctrl. pt. is "behind" the source node
                    w = -ws / srcTgtDist;
                } else {
                    // The ctrl. pt. is anywhere past the source node
                    w = ws / srcTgtDist;
                }
                // If we detect all of the control points of an edge are less
                // than some epsilon value, we just render the edge as a normal
                // bezier (which defaults to a straight line).
                if (Math.abs(pld) > this.CTRL_PT_DIST_EPSILON) {
                    complex = true;
                }
                // Control points with a weight of 0 (as the first ctrl pt)
                // or a weight of 1 (as the last ctrl pt) aren't valid due
                // to implicit points already "existing there."
                // (See https://github.com/cytoscape/cytoscape.js/issues/1451)
                // This preemptively rectifies such control points.
                if (p === 0 && w === 0.0) {
                    w = 0.01;
                } else if (p == ctrlPts.length - 2 && w === 1.0) {
                    w = 0.99;
                }
                ctrlPtDists += pld.toFixed(2) + " ";
                ctrlPtWeights += w.toFixed(2) + " ";
            }
            return {
                complex: complex,
                dists: ctrlPtDists.trim(),
                weights: ctrlPtWeights.trim(),
            };
        }

        renderEdge(edgeAttrs, edgeVals, node2pos, srcID, tgtID, dx, dy) {
            // Scale edge thickness, and see if it's an "outlier" or not
            var edgeWidth =
                this.MIN_EDGE_THICKNESS +
                edgeVals[edgeAttrs.relative_weight] * this.EDGE_THICKNESS_RANGE;
            var classes = "oriented";
            if (edgeVals[edgeAttrs.is_outlier] === 1) {
                classes += " high_outlier";
            } else if (edgeVals[edgeAttrs.is_outlier] === -1) {
                classes += " low_outlier";
            }

            if (edgeVals[edgeAttrs.is_dup]) {
                classes += " is_dup";
            }

            var data = {
                source: srcID,
                target: tgtID,
                thickness: edgeWidth,
                // We store this so we can always connect an edge element, even
                // after collapsing, to its data in the DataHolder
                origSrcID: srcID,
                origTgtID: tgtID,
            };

            var parentID = edgeVals[edgeAttrs.parent_id];
            if (!_.isNull(parentID)) {
                data.parent = parentID;
            }

            if (srcID === tgtID) {
                // It's a self-directed edge; don't bother parsing ctrl pt
                // info, just render it as a bezier edge and be done with it
                this.cy.add({
                    classes: classes + " basicbezier",
                    data: data,
                });
            } else {
                var srcPos = node2pos[srcID];
                var tgtPos = node2pos[tgtID];
                if (!_.has(node2pos, srcID) || !_.has(node2pos, tgtID)) {
                    console.log("node2pos: ", node2pos);
                    console.log("src ID: ", srcID);
                    console.log("tgt ID: ", tgtID);
                    throw new Error("ID(s) not in node2pos...?");
                }
                var ctrlPts = edgeVals[edgeAttrs.ctrl_pt_coords];
                var ctrlPtData = this.convertCtrlPtsToDistsAndWeights(
                    srcPos,
                    tgtPos,
                    ctrlPts,
                    dx,
                    dy
                );
                if (ctrlPtData.complex) {
                    // Control points are valid
                    data.cpd = ctrlPtData.dists;
                    data.cpw = ctrlPtData.weights;
                    this.cy.add({
                        classes: classes + " unbundledbezier",
                        data: data,
                    });
                } else {
                    // Control point distances from a straight line between
                    // source and sink are small enough that we can just
                    // approximate this edge as a straight line
                    this.cy.add({
                        classes: classes + " basicbezier",
                        data: data,
                    });
                }
            }
            this.numDrawnEdges++;
        }

        /**
         * Sets bindings for various user interactions with the graph.
         *
         * These bindings cover a lot of the useful things in MetagenomeScope's
         * interface -- collapsing/uncollapsing patterns, selecting elements,
         * etc.
         *
         * This should be called every time the graph is initialized.
         */
        setGraphBindings() {
            this.cy.on(
                "select",
                "node.basic, edge, node.pattern",
                this.onSelect
            );
            this.cy.on(
                "unselect",
                "node.basic, edge, node.pattern",
                this.onUnselect
            );
            this.cy.on("cxttap", "node.pattern", this.onTogglePatternCollapse);
        }

        /**
         * Draws component(s) in the graph.
         *
         * This effectively involves remaking the instance of Cytoscape.js in
         * use, so we require that some callbacks
         *
         * @param {Array} componentsToDraw 1-indexed size rank numbers of the
         *                                 component(s) to draw.
         *
         * @param {DataHolder} dataHolder Object containing graph data.
         *
         * @throws {Error} If componentsToDraw contains duplicate values and/or
         *                 if any of the numbers within it are invalid with
         *                 respect to the dataHolder.
         */
        draw(componentsToDraw, dataHolder) {
            var scope = this;
            if (!_.isNull(this.cy)) {
                this.destroyGraph();
            }
            this.initGraph();
            this.cy.startBatch();
            // These are the "offsets" from the top-left of each component's
            // bounding box, used when drawing multiple components at once.
            var maxWidth = null;
            var dx = 0;
            var dy = 0;
            var firstCompWidth = null;
            _.each(componentsToDraw, function (sizeRank) {
                // Draw patterns
                var pattAttrs = dataHolder.getPattAttrs();
                _.each(dataHolder.getPatternsInComponent(sizeRank), function (
                    pattVals
                ) {
                    scope.renderPattern(pattAttrs, pattVals, dx, dy);
                });

                // Draw nodes
                var node2pos = {};
                var nodeAttrs = dataHolder.getNodeAttrs();
                _.each(dataHolder.getNodesInComponent(sizeRank), function (
                    nodeVals,
                    nodeID
                ) {
                    var pos = scope.renderNode(
                        nodeAttrs,
                        nodeVals,
                        nodeID,
                        dx,
                        dy
                    );
                    node2pos[nodeID] = pos;
                });

                // Draw edges
                var edgeAttrs = dataHolder.getEdgeAttrs();
                // Edges are a bit different: they're structured as
                // {srcID: {tgtID: edgeVals, tgtID2: edgeVals}, ...}
                _.each(dataHolder.getEdgesInComponent(sizeRank), function (
                    edgesFromSrcID,
                    srcID
                ) {
                    _.each(edgesFromSrcID, function (edgeVals, tgtID) {
                        scope.renderEdge(
                            edgeAttrs,
                            edgeVals,
                            node2pos,
                            srcID,
                            tgtID,
                            dx,
                            dy
                        );
                    });
                });

                // If we're drawing multiple components at once, let's update
                // dx and dy so that we can place other components somewhere
                // that doesn't interfere with previously-drawn components.
                var componentBoundingBox = dataHolder.getComponentBoundingBox(
                    sizeRank
                );
                // The way component tiling works right now is: we draw the
                // first component (assumed to be the largest, of those being
                // drawn), which has width W and height H. We then draw the
                // next component just above the top-right position of this
                // component (using some padding), and then tile components
                // from right to left. When a component's bounding box would be
                // drawn in a way that extends past the left side of the first
                // component's bounding box, we reset the horizontal offset to
                // 0 and increase the vertical offset. In this way we kind of
                // use a grid pattern.
                //
                // This code is horrendous, because coordinates are confusingly
                // stored as negative numbers and because Graphviz and
                // Cytoscape.js use different conventions as to where (0, 0) is
                // (GV has it at the bottom left; Cytoscape.js has it at the
                // top left). It would be good to sort things out in the Python
                // code so that coordinates are stored as positive numbers
                // (using Cytoscape.js-based y-coordinates), which would enable
                // 1) cleaning up this code and 2) tiling components from top
                // to bottom and left to right.
                if (_.isNull(firstCompWidth)) {
                    firstCompWidth = componentBoundingBox[0];
                    dy -= componentBoundingBox[1] + scope.COMPONENT_PADDING;
                } else {
                    dx -= componentBoundingBox[0] + scope.COMPONENT_PADDING;
                    if (Math.abs(dx) > firstCompWidth) {
                        dx = 0;
                        dy -= componentBoundingBox[1] + scope.COMPONENT_PADDING;
                    }
                }
            });
            this.initPatterns();
            this.finishDraw();
        }

        /**
         * Enables interaction with the graph interface after drawing.
         */
        finishDraw() {
            this.cy.endBatch();
            this.cy.fit();
            // Set minZoom to whatever the zoom level when viewing the entire drawn
            // component at once (i.e. right now) is, divided by 2 to give some
            // leeway for users to zoom out if they want
            this.cy.minZoom(this.cy.zoom() / 2);

            // Enable interaction with the graph
            this.cy.userPanningEnabled(true);
            this.cy.userZoomingEnabled(true);
            this.cy.boxSelectionEnabled(true);
            this.cy.autounselectify(false);
            this.cy.autoungrabify(false);
        }

        /**
         * Adjusts the size of the Cytoscape.js area.
         *
         * Should be called whenever the page dimensions are changed (i.e. the
         * control panel is hidden / un-hidden).
         */
        toggleSize() {
            this.cyDiv.toggleClass("nosubsume");
            this.cyDiv.toggleClass("subsume");
            if (!_.isNull(this.cy)) {
                this.cy.resize();
            }
        }

        /**
         * Fits the graph: either to all elements or just to those selected.
         *
         * @param {Boolean} toSelected If true, fit to just the currently-
         *                             selected elements in the graph; if
         *                             false, fit to all drawn elements.
         */
        fit(toSelected) {
            // TODO: use progress bar
            if (toSelected) {
                // Right now, we don't throw any sort of error here if
                // no elements are selected. This is because the fit-selected
                // button should only be enabled when >= 1 elements are
                // selected.
                this.cy.fit(this.cy.$(":selected"));
            } else {
                this.cy.fit();
            }
        }

        /**
         * Makes an edge "basic" -- if it isn't already a basicbezier, makes it
         * a basicbezier (i.e. makes it basically a straight line), and also
         * adds the not_using_ports class (no longer constrains it to hitting
         * the exact end / start of its source / end nodes).
         *
         * @param {Cytoscape.js edge Element} edgeEle
         */
        makeEdgeBasic(edgeEle) {
            if (edgeEle.data("cpd")) {
                edgeEle.removeClass("unbundledbezier");
                edgeEle.addClass("basicbezier");
            }
            edgeEle.addClass("not_using_ports");
        }

        /**
         * Reverses what makeEdgeBasic() does.
         *
         * Intended to be called on an edge that has already had its incident
         * node uncollapsed, so now its source and target point to the "next"
         * node down. This next node may still be a pattern, so we have a check
         * here that sees if we REALLY can make this edge not basic yet.
         *
         * @param {Cytoscape.js edge Element} edgeEle
         */
        makeEdgeNonBasic(edgeEle) {
            if (edgeEle.data("cpd")) {
                if (
                    !edgeEle.source().data("isCollapsed") &&
                    !edgeEle.target().data("isCollapsed")
                ) {
                    edgeEle.removeClass("basicbezier");
                    edgeEle.addClass("unbundledbezier");
                }
            }
            edgeEle.removeClass("not_using_ports");
        }

        /**
         * Collapses a pattern, taking care of the display-level details.
         *
         * @param {Cytoscape.js node Element} pattern
         */
        collapsePattern(pattern) {
            this.cyEC.collapse(pattern);
            pattern.connectedEdges().each(this.makeEdgeBasic);
            pattern.data("isCollapsed", true);
        }

        /**
         * Reverses collapsePattern().
         *
         * @param {Cytoscape.js node Element} Pattern
         */
        uncollapsePattern(pattern) {
            // Importantly, we retrieve the edges incident on this pattern
            // BEFORE uncollapsing it. This is so that we can evaluate for each
            // of these edges whether or not we should make it non-basic.
            var incidentEdges = pattern.connectedEdges();
            this.cyEC.expand(pattern);
            // Now, let's try to make these edges non-basic -- this'll involve
            // looking at their new (well, really, old) source/target, and
            // seeing if both of these are real nodes.
            incidentEdges.each(this.makeEdgeNonBasic);
            pattern.data("isCollapsed", false);
        }

        /**
         * Given an array of node names, attempts to select them.
         *
         * NOTE / TODO: There are various inefficiencies and corner-cases that
         * should be fixed for this.
         *
         * @param {Array} nodeNames Node names to search for. These should have
         *                          already had leading/trailing whitespace and
         *                          duplicates removed.
         *
         * @return {Array} notFoundNames Node names that the search couldn't
         *                               find. If all names were found, this
         *                               array will be empty. The user should
         *                               be warned if this array isn't empty.
         */
        searchForNodes(nodeNames) {
            var scope = this;
            var eles = this.cy.collection(); // empty collection (for now)
            var newEle;
            var parentID;
            var notFoundNames = [];
            var atLeastOneNameFound = false;
            _.each(nodeNames, function (name) {
                newEle = scope.cy.nodes('[nodeName="' + name + '"]');
                // TODO: If we don't find the node(s), they might be within
                // collapsed pattern(s). Check this.nodeName2parent (or the
                // data holder? get it from AppManager?) and use
                // that to figure things out. (Complicating things: a node
                // might be present in one uncollapsed pattern while its
                // duplicate might be present in another (collapsed) pattern.)
                // I'm not 100% sure how to do this best right now, so for the
                // time being searching only works for shown nodes in currently
                // drawn components.
                if (newEle.empty()) {
                    notFoundNames.push(name);
                } else {
                    atLeastOneNameFound = true;
                    eles = eles.union(newEle);
                }
            });
            if (atLeastOneNameFound) {
                // Fit the graph to the identified nodes
                this.cy.fit(eles);
                // Unselect all previously-selected elements (including edges
                // and patterns)
                this.unselectAll();
                // Select all identified nodes
                eles.select();
            }
            return notFoundNames;
        }

        /**
         * Takes as input an array of node names, and highlights them.
         *
         * @param {Array} nodeNames Array of node names. This will fail if any of
         *                          these names do not map to a node in the graph.
         */
        highlightNodesInScaffold(nodeNames) {
            var scope = this;
            this.unselectAll();
            var nodesToHighlight = this.cy.collection();
            var nodeToAdd;
            var prefix;
            _.each(nodeNames, function (name) {
                nodeToAdd = scope.cy.nodes('[nodeName="' + name + '"]');
                if (nodeToAdd.empty()) {
                    // TODO: check nodeName2parent instead of just immediately
                    // throwing this error -- the node could still be contained
                    // within a collapsed pattern (could also be duplicated,
                    // complicating things -- and if it is duplicated we should
                    // highlight both instances of it, accounting for either
                    // potentially being in a collapsed pattern).
                    throw new Error("Couldn't find node(s) in this scaffold.");
                }
                nodesToHighlight = nodesToHighlight.union(nodeToAdd);
            });
            nodesToHighlight.select();
        }

        /**
         * Finds scaffolds that apply to the currently drawn part of the graph.
         *
         * The current definition of "apply" is "the first node listed in this
         * scaffold is currently drawn." Ideally, we should tighten this up
         * to say "all nodes in this scaffold are currently drawn." -- and also
         * account for other wack things like nodes in collapsed patterns,
         * duplicates, etc. Currently this is an early draft of this
         * functionality in New MetagenomeScope (tm).
         *
         * @param {Object} scaffoldID2NodeNames Maps scaffold IDs (Strings) to
         *                                      an Array of node names within
         *                                      this scaffold.
         *
         * @returns {Array} availableScaffolds A subset of the keys in
         *                                     scaffoldID2NodeNames, limited
         *                                     to just scaffolds that "apply"
         *                                     to the currently drawn part of
         *                                     the graph. If no scaffolds
         *                                     apply, this will be [].
         */
        getAvailableScaffolds(scaffoldID2NodeNames) {
            // Avoid storing all node names in memory, and avoid searching
            // node names once for every node name to query, by just going
            // through all drawn node names once up front.
            // Based on https://js.cytoscape.org/#eles.map
            var drawnNodeNames = this.cy.nodes().map(function (n) {
                return n.data("nodeName");
            });
            var availableScaffolds = [];
            _.each(scaffoldID2NodeNames, function (nodeNames, scaffoldID) {
                // NOTE: definitely possible to speed this up, e.g. by sorting
                // drawnNodeNames then using the binary search stuff with
                // _.indexOf()
                if (_.contains(drawnNodeNames, nodeNames[0])) {
                    availableScaffolds.push(scaffoldID);
                }
            });
            return availableScaffolds;
        }

        /**
         * Returns a base64-encoded image of the graph.
         *
         * This is basically just a wrapper for cy.png() or cy.jpg().
         *
         * @param {String} imgType Should be either "PNG" or "JPG".
         *
         * @returns {String} encodedImage
         *
         * @throws {Error} if imgType is not "PNG" or "JPG".
         */
        exportImage(imgType) {
            var options = { bg: this.bgColor };
            if (imgType === "PNG") {
                return this.cy.png(options);
            } else if (imgType === "JPG") {
                return this.cy.jpg(options);
            } else {
                throw new Error("Unrecognized imgType: " + imgType);
            }
        }

        /**
         * Unselects all currently-selected nodes / edges / patterns.
         *
         * I've made this its own function for convenience and because
         * it should be possible to speed this up if desired: see
         * https://github.com/fedarko/MetagenomeScope/issues/115#issuecomment-294407711
         */
        unselectAll() {
            this.cy.filter(":selected").unselect();
        }
    }
    return { Drawer: Drawer };
});
