define(["jquery", "underscore", "drawer", "utils", "dom-utils"], function (
    $,
    _,
    Drawer,
    utils,
    domUtils
) {
    class AppManager {
        constructor(dataHolder) {
            // Holds all of the actual graph data (nodes, edges, etc.)
            this.dataHolder = dataHolder;

            this.numComponents = this.dataHolder.numComponents();

            // Set up the Drawer, which'll interface with Cytoscape.js.
            // We pass a few callbacks to the Drawer so that the Drawer can let
            // the App Manager know when various things happen in the graph.
            this.drawer = new Drawer.Drawer(
                "cy",
                this.onSelect.bind(this),
                this.onUnselect.bind(this),
                this.onTogglePatternCollapse.bind(this),
                this.onDestroy.bind(this)
            );

            this.controlsDiv = $("#controls");

            $(this.doThingsWhenDOMReady.bind(this));

            this.cmpSelectionMethod = undefined;
            // Set the component selection method to whatever the
            // currently-selected value in the component selection method
            // dropdown menu is, and sort out the UI accordingly
            this.updateCmpSelectionMethod();

            // Sets of IDs of selected elements (nodes/edges/patterns).
            // We could probably get away with using Arrays here instead,
            // but using Sets accounts for silly corner cases where e.g. a node
            // is somehow selected twice without being unselected in the
            // middle. (I don't... think that should be possible in
            // Cytoscape.js, but let's just be defensive from the start, ok?)
            this.selectedNodes = new Set();
            this.selectedEdges = new Set();
            this.selectedPatterns = new Set();

            // Set of IDs of collapsed patterns.
            this.collapsedPatterns = new Set();

            // Attributes described in the columns of the selected node info
            // and selected edge info tables. These'll be updated in
            // initSelectedEleInfoTables(). (They're used to figure out how to
            // structure a row of node/edge data to add to these tables.)
            this.nodeInfoTableAttrs = [];
            this.edgeInfoTableAttrs = [];
        }

        /**
         * Set various bindings, enable elements that don't need to have
         * something drawn on the screen, etc.
         */
        doThingsWhenDOMReady() {
            var scope = this;
            // Make that "hamburger" button show/hide the control panel
            $("#controlsToggler").click(this.toggleControls.bind(this));

            // Make the "Graph info" button show a modal dialog
            $("#infoButton").click(function () {
                $("#infoDialog").modal();
            });
            domUtils.enableButton("infoButton");

            // Make the "Settings" button show the settings dialog
            $("#settingsButton").click(function () {
                $("#settingsDialog").modal();
            });

            // Pop open the wiki when the help button is clicked
            $("#helpButton").click(function () {
                window.open(
                    "https://github.com/marbl/MetagenomeScope/wiki",
                    "_blank"
                );
            });

            // Set up the component selector
            var svc = this.dataHolder.smallestViewableComponent();
            $("#componentselector").prop("value", svc);
            // TODO?: May be ok to always allow this to go down to 1 if we
            // have very explicit error messages about cmps not having been
            // laid out, and update domUtils.compRankValidity() to not rely on
            // the "min" property of this ._.
            $("#componentselector").prop("min", svc);
            $("#componentselector").prop("max", this.numComponents);
            $("#decrCompRankButton").click(domUtils.decrCompRank);
            $("#incrCompRankButton").click(domUtils.incrCompRank);
            $("#drawButton").click(this.draw.bind(this));

            // On a new component selection method being, well, selected,
            // update this.cmpSelectionMethod.
            $("#cmpSelectionMethod").change(
                this.updateCmpSelectionMethod.bind(this)
            );

            domUtils.enablePersistentControls(this.numComponents);

            this.populateGraphInfoMain();

            this.initSelectedEleInfoTables();

            _.each(["node", "edge", "pattern"], function (eleType) {
                $("#" + eleType + "Header").click(function () {
                    scope.toggleEleInfo(eleType);
                });
            });

            // Set up colorpickers
            $(".colorpicker-component").colorpicker({ format: "hex" });

            // Set up "fit" buttons
            $("#fitButton").click(function () {
                scope.drawer.fit(false);
            });
            $("#fitSelectedButton").click(function () {
                scope.drawer.fit(true);
            });
        }

        /**
         * Toggles whether or not the controls div is shown, adjusting the
         * size of the Cytoscape.js div if applicable.
         */
        toggleControls() {
            this.controlsDiv.toggleClass("notviewable");
            this.drawer.toggleSize();
        }

        /**
         * Toggles a "Selected Element" section of the control panel.
         *
         * There are three of these sections -- nodes, edges, and patterns.
         *
         * @param {String} eleType One of "node", "edge", "pattern".
         *
         * @throws {Error} if eleType is invalid
         */
        toggleEleInfo(eleType) {
            var validEleTypes = ["node", "edge", "pattern"];
            if (_.contains(validEleTypes, eleType)) {
                var openerID = "#" + eleType + "Opener";
                var infoDivID = "#" + eleType + "Info";
                if ($(openerID).hasClass("glyphicon-triangle-right")) {
                    $(openerID).removeClass("glyphicon-triangle-right");
                    $(openerID).addClass("glyphicon-triangle-bottom");
                } else {
                    $(openerID).removeClass("glyphicon-triangle-bottom");
                    $(openerID).addClass("glyphicon-triangle-right");
                }
                $(infoDivID).toggleClass("notviewable");
            } else {
                throw new Error("Unrecognized eleType: " + eleType);
            }
        }

        /**
         * Updates the component selection method (e.g. "draw just a single
         * component", "draw all components", etc.) based on the option that
         * is currently selected, and shows/hides certain UI elements within
         * the "Drawing" control panel section accordingly.
         *
         * By hiding all UI elements, rather than trying to maintain a record
         * of whatever the previously-selected method was (if any was
         * selected), we can get around some corner cases -- see the HTML
         * for some details. There are only, like, three of these options
         * anyway, so this shouldn't be a performance problem.
         */
        updateCmpSelectionMethod() {
            var newMethod = $("#cmpSelectionMethod").val();
            $("#cmpSelectionMethod")
                .children()
                .each(function (i, e) {
                    if (e.value !== newMethod) {
                        // Hide other selection UIs
                        $("#" + e.value + "-draw-eles").addClass("notviewable");
                    } else {
                        // Show the now-selected component selection UI
                        $("#" + newMethod + "-draw-eles").removeClass(
                            "notviewable"
                        );
                    }
                });
            this.cmpSelectionMethod = newMethod;
        }

        /**
         * Populates the "graph information" table based on the data holder.
         *
         * This should only be called once; the information applied here should
         * not change as the graph is drawn.
         */
        populateGraphInfoMain() {
            $("#filenameEntry").text(this.dataHolder.fileName());
            $("#filetypeEntry").text(this.dataHolder.fileType());
            $("#nodeCtEntry").text(this.dataHolder.totalNumNodes());
            $("#edgeCtEntry").text(this.dataHolder.totalNumEdges());
            $("#ccCtEntry").text(this.dataHolder.numComponents());
        }

        populateGraphInfoCurrComponents() {
            // TODO: populate based on the component(s) currently drawn.
        }

        /**
         * Prepares the info tables for selected elements.
         *
         * This only needs to be called once, since it's based on the data in
         * the DataHolder.
         */
        initSelectedEleInfoTables() {
            var scope = this;
            // Add columns to the tables for the extra data columns we have
            //
            // First, do this for the node info table
            var extraNodeAttrs = this.dataHolder.getExtraNodeAttrs();
            // Update the "colspan" of the table's first row
            // https://stackoverflow.com/a/1294964
            $("#nodeTH").attr(
                "colspan",
                $("#nodeTH").attr("colspan") + extraNodeAttrs.length
            );
            // Add as many header columns as needed
            // Note that each <th> id is of the format "nodeInfoTable-attrname"
            // -- this is important. (This obviously violates all kinds of best
            // practices, but sometimes it be like that.)
            _.each(extraNodeAttrs, function (attr) {
                $("#nodeInfoTable tr:nth-child(2)").append(
                    '<th id="nodeInfoTable-' +
                        attr +
                        '">' +
                        attr +
                        "</th>"
                );
            });
            // Update an internal array of attributes in the same order as
            // columns in the info table -- will help when populating the
            // tables later on
            $("#nodeInfoTable tr:nth-child(2) > th").each(function(i, th) {
                // Each <th>'s id is formatted as "nodeInfoTable-attrname".
                // The .slice(14) removes the "nodeInfoTable-".
                // Yes, this is a horrible, horrible, terrible no good very bad
                // hack. However, it's the easiest way to do this I can think
                // of and my friend I am SO TIRED right now lmao.
                var attrName = th.id.slice(14);
                scope.nodeInfoTableAttrs.push(attrName);
            });

            // Now do this for the edge info table. (TODO: merge this with the
            // node code...)
            var extraEdgeAttrs = this.dataHolder.getExtraEdgeAttrs();
            $("#edgeTH").attr(
                "colspan",
                $("#edgeTH").attr("colspan") + extraEdgeAttrs.length
            );
            _.times(extraEdgeAttrs.length, function (i) {
                $("#edgeInfoTable tr:nth-child(2)").append(
                    '<th id="edgeInfoTable-' +
                        extraEdgeAttrs[i] +
                        '">' +
                        extraEdgeAttrs[i] +
                        "</th>"
                );
            });
            $("#edgeInfoTable tr:nth-child(2) > th").each(function(i, th) {
                var attrName = th.id.slice(14);
                scope.edgeInfoTableAttrs.push(attrName);
            });
        }

        updateSelectedNodeInfo(eleID, selectOrUnselect) {
            if (selectOrUnselect === "select") {
                var nodeInfo = this.dataHolder.getNodeInfo(eleID);
                // TODO: cache this for this class since it doesn't change
                var nodeAttrs = this.dataHolder.getNodeAttrs();
                var rowHTML =
                    '<tr class="selectedEleRow" id="selectedEleRow' +
                    eleID +
                    '">';
                _.each(this.nodeInfoTableAttrs, function (attr) {
                    rowHTML += "<td>" + nodeInfo[nodeAttrs[attr]] + "</td>";
                });
                rowHTML += "</tr>";
                $("#nodeInfoTable").append(rowHTML);
            } else {
                this.removeSelectedEleInfo(eleID);
            }
        }

        updateSelectedEdgeInfo(eleID, selectOrUnselect) {
            if (selectOrUnselect === "select") {
            } else {
                this.removeSelectedEleInfo(eleID);
            }
        }

        updateSelectedPatternInfo(eleID, selectOrUnselect) {
            if (selectOrUnselect === "select") {
                var pattInfo = this.dataHolder.getPatternInfo(eleID);
                var pattType = utils.getHumanReadablePatternType(
                    pattInfo[this.dataHolder.getPattAttrs().pattern_type]
                );
                $("#patternInfoTable").append(
                    '<tr class="selectedEleRow" id="selectedEleRow' +
                        eleID +
                        '"><td>' +
                        pattType +
                        "</td></tr>"
                );
            } else {
                this.removeSelectedEleInfo(eleID);
            }
        }

        removeSelectedEleInfo(eleID) {
            $("#selectedEleRow" + eleID).remove();
        }

        /**
         * Removes all selected element rows from the node/edge/pattern tables.
         *
         * Also sets the "badges" containing the numbers of currently-selected
         * nodes/edges/patterns back to zero.
         *
         * Intended for use when the graph state is fundamentally changed --
         * e.g. when drawing something new (in which case the Cytoscape.js
         * instance will be destroyed and then re-initialized).
         *
         * Fun Fact: for some reason, the "badge" resetting stuff wasn't part
         * of this function back in Old MetagenomeScope. Instead, those three
         * lines of code were duplicated like four times throughout the
         * codebase. Coding While Tired: Not Even Once. (TM)
         */
        removeAllSelectedEleInfo() {
            // Remove (non-header) table rows
            $(".selectedEleRow").remove();
            // Close element info sections, if they're open
            if ($("#nodeOpener").hasClass("glyphicon-triangle-bottom")) {
                this.toggleEleInfo("node");
            }
            if ($("#edgeOpener").hasClass("glyphicon-triangle-bottom")) {
                this.toggleEleInfo("edge");
            }
            if ($("#patternOpener").hasClass("glyphicon-triangle-bottom")) {
                this.toggleEleInfo("pattern");
            }
            // Reset badges showing selected element counts to 0
            $("#selectedNodeBadge").text(0);
            $("#selectedEdgeBadge").text(0);
            $("#selectedPatternBadge").text(0);
            // Empty the Sets we maintain with actual selected node/edge/patt
            // counts, since if we leave stuff in them that'll mess up things
            // in the future
            this.selectedNodes = new Set();
            this.selectedEdges = new Set();
            this.selectedPatterns = new Set();
        }

        /**
         * Returns an array containing all of the components to draw.
         *
         * If the components to draw are invalid in some way (e.g. they refer
         * to a component or a node that does not exist), this will open an
         * alert message (letting the user know what happened) and throw an
         * error (stopping execution of draw()).
         *
         * @returns {Array} Size ranks (1-indexed) of the component(s) to draw,
         *                  stored as Numbers. This will be an Array no matter
         *                  what, so even if just one component will be drawn
         *                  this'll still return an Array with just that one
         *                  Number.
         *
         * @throws {Error} If component selection is invalid (e.g. the size
         *                 rank is out of range for method === "single", or the
         *                 node name for method === "withnode" is not in the
         *                 graph)
         */
        getComponentsToDraw() {
            if (this.cmpSelectionMethod === "single") {
                var cmpRank = $("#componentselector").val();
                if (domUtils.compRankValidity(cmpRank) !== 0) {
                    // TODO? -- give more detailed error messages listing e.g.
                    // the lowest laid out component rank
                    alert("Please enter a valid component size rank.");
                    throw new Error("Invalid component size rank.");
                } else {
                    return [parseInt(cmpRank)];
                }
            } else if (this.cmpSelectionMethod === "withnode") {
                var name = $("#nodeNameSelector").val();
                var cmpRank = this.dataHolder.findComponentContainingNodeName(
                    name
                );
                if (cmpRank === -1) {
                    alert(
                        'No laid-out components contain a node with the name "' +
                            name +
                            '".'
                    );
                    throw new Error("Invalid node name.");
                } else {
                    return [cmpRank];
                }
            } else if (this.cmpSelectionMethod === "all") {
                return this.dataHolder.getAllLaidOutComponentRanks();
            } else {
                throw new Error(
                    "Invalid cmp selection method set: " +
                        this.cmpSelectionMethod
                );
            }
        }

        /**
         * Helper function for onSelect() and onUnselect(). Based on the type
         * of the element that was selected or unselected, updates the selected
         * nodes / edges / patterns Set and updates the corresponding badge's
         * number.
         *
         * Also enables / disables the #fitSelectedButton as needed, since that
         * should only be enabled if at least one element is selected.
         *
         * Most of the code for these functions was basically the same, so
         * this function is here to mitigate code reuse.
         *
         * @param {Cytoscape.js Event} eve Event triggered by Cytoscape.js.
         *
         * @param {String} selectOrUnselect If this is "select", then this'll
         *                                  add the element described in
         *                                  eve.target to the corresponding
         *                                  selected element Set; if this is
         *                                  "unselect", then this'll remove
         *                                  that element from the Set. If this
         *                                  isn't either of those things,
         *                                  this'll raise an error.
         *
         * @throws {Error} If any of the following conditions is met:
         *                 -The element described by eve.target isn't a node
         *                  (here "node" includes both normal nodes and
         *                  patterns) or edge.
         *                 -The element described by eve.target is a node,
         *                  but it doesn't seem to be a normal or pattern node.
         *                 -selectOrUnselect isn't "select" or "unselect"
         */
        updateSelectedEles(eve, selectOrUnselect) {
            // This is the name of the Set function we want to call with the
            // element's ID. It's either .add() or .delete(), and fortunately
            // JS makes swapping out functions to be called fairly easy.
            var setFunc;
            if (selectOrUnselect === "select") {
                setFunc = "add";
            } else if (selectOrUnselect === "unselect") {
                setFunc = "delete";
            } else {
                throw new Error(
                    "Invalid selectOrUnselect value: " + selectOrUnselect
                );
            }

            var x = eve.target;
            var xID = x.id();
            if (x.isNode()) {
                if (x.hasClass("basic")) {
                    // It's a regular node (not a pattern).
                    this.selectedNodes[setFunc](xID);
                    $("#selectedNodeBadge").text(this.selectedNodes.size);
                    this.updateSelectedNodeInfo(xID, selectOrUnselect);
                } else if (x.hasClass("pattern")) {
                    // It's a pattern.
                    this.selectedPatterns[setFunc](xID);
                    $("#selectedPatternBadge").text(this.selectedPatterns.size);
                    this.updateSelectedPatternInfo(xID, selectOrUnselect);
                } else {
                    throw new Error(
                        "Unrecognized node type of target element: " + x
                    );
                }
            } else if (x.isEdge()) {
                // It's an edge.
                // NOTE: Although we don't explicitly define edge IDs,
                // Cytoscape.js initializes edges with UUIDs, which makes our
                // job here easier.
                this.selectedEdges[setFunc](xID);
                $("#selectedEdgeBadge").text(this.selectedEdges.size);
                this.updateSelectedEdgeInfo(xID, selectOrUnselect);
            } else {
                throw new Error("Target element not a node or edge: " + x);
            }

            var totalSelectedEleCt =
                this.selectedNodes.size +
                this.selectedEdges.size +
                this.selectedPatterns.size;
            if (setFunc === "add" && totalSelectedEleCt === 1) {
                // The #fitSelectedButton element should be enabled if at least
                // one element is selected.
                domUtils.enableButton("fitSelectedButton");
            } else {
                // Similarly, if we just un-selected an element, then check if
                // no elements are now selected. If so, disable the button.
                // (...Not sure how we'd have a negative amount of selected
                // elements, but I figure we might as well cover our bases with
                // the <= 0 here :P)
                if (totalSelectedEleCt <= 0) {
                    domUtils.disableButton("fitSelectedButton");
                }
            }
        }

        /**
         * Updates the selected elements section in response to an element
         * being selected.
         *
         * @param {Cytoscape.js Event} eve Event triggered by Cytoscape.js.
         */
        onSelect(eve) {
            this.updateSelectedEles(eve, "select");
        }

        /**
         * Updates the selected elements section in response to an element
         * being unselected.
         *
         * @param {Cytoscape.js Event} eve Event triggered by Cytoscape.js.
         */
        onUnselect(eve) {
            this.updateSelectedEles(eve, "unselect");
        }

        /**
         * Collapses/uncollapses a pattern.
         *
         * @param {Cytoscape.js Event} eve Event triggered by Cytoscape.js.
         */
        onTogglePatternCollapse(eve) {
            var pattern = eve.target;
            // TODO set up
            if (pattern.data("isCollapsed")) {
                this.uncollapsePattern(pattern);
            } else {
                this.collapsePattern(pattern);
            }
        }

        collapsePattern(pattern) {
            // Prevent this pattern from being collapsed if any of its children are
            // tentative nodes in finishing mode (TODO, reimplement when we get
            // finishing working again)
            //
            // var children = pattern.children();
            // if (this.finishingModeOn) {
            //     for (var ci = 0; ci < children.length; ci++) {
            //         if (children[ci].hasClass("tentative")) {
            //             return;
            //         }
            //     }
            // }
            this.drawer.collapsePattern(pattern);
            this.collapsedPatterns.add(pattern.id());
            if (this.collapsedPatterns.size === this.drawer.numDrawnPatterns) {
                // TODO: reenable when the collapse button is working again
                // if ($("#collapseButtonText").text()[0] === "C") {
                //     this.changeCollapseButton(true);
                // }
            }
        }

        uncollapsePattern(pattern) {
            // Prevent this cluster from being uncollapsed if it's a
            // "tentative" node in finishing mode (TODO, reimplement when
            // finishing working again)
            // if (mgsc.FINISHING_MODE_ON) {
            //     if (cluster.hasClass("tentative")) {
            //         return;
            //     }
            // }
            this.drawer.uncollapsePattern(pattern);
            this.collapsedPatterns.delete(pattern.id());
            if (this.collapsedPatterns.size === 0) {
                // TODO: reenable when the collapse button is working again
                // if ($("#collapseButtonText").text()[0] === "U") {
                //     this.changeCollapseButton(false);
                // }
            }
        }

        /**
         * Clears application state when the graph is destroyed.
         *
         * This should happen whenever a portion of the graph is redrawn.
         *
         * ...I will probably think of more things to add here later.
         */
        onDestroy() {
            this.removeAllSelectedEleInfo();
            // Clear collapsed pattern info
            // (... If we're drawing patterns as already collapsed, then
            // those patterns should be added to this when that happens)
            this.collapsedPatterns = new Set();
        }

        /**
         * Attempts to draw component(s) based on the component(s) selected.
         *
         * It's very possible that this.getComponentsToDraw() will fail if the
         * current component selection is invalid (e.g. an invalid size rank is
         * selected). In that case, this.getComponentsToDraw() will just throw
         * an Error, and this'll stop before it actually calls
         * this.drawer.draw().
         *
         * @throws {Error} If component selection is invalid.
         */
        draw() {
            var componentsToDraw = this.getComponentsToDraw();
            this.drawer.draw(componentsToDraw, this.dataHolder);
            // Enable controls that only have meaning when stuff is drawn (e.g.
            // the "fit graph" buttons)
            domUtils.enableDrawNeededControls();
        }
    }
    return { AppManager: AppManager };
});
