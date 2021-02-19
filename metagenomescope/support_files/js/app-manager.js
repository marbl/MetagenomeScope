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

            // Array of the size ranks of the currently drawn components.
            // Only updated when this.draw() is called.
            this.currentlyDrawnComponents = [];

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

            // Maps scaffold ID to an array of node IDs within this scaffold.
            this.scaffoldID2NodeNames = {};
            // Array of scaffolds in the currently drawn component(s), in the
            // same order as listed in the input AGP file. Used when cycling
            // through scaffolds.
            this.currComponentsScaffolds = [];
            // Current "index" of the drawScaffoldButton in
            // this.currComponentsScaffolds. Updated as the user cycles through
            // scaffolds.
            this.scaffoldCyclerCurrIndex = 0;
            // Set to true if the currently drawn component(s) have any nodes
            // within scaffolds in an uploaded AGP file; false otherwise.
            this.currComponentsHaveScaffolds = false;

            // Text shown in selected element info tables for attributes not
            // given for a node / edge / pattern.
            this.ATTR_NA = "N/A";

            // How many bytes to read at once from an AGP file.
            // For now, we set this to 1 MiB. The maximum Blob size in most
            // browsers (... at least when I implemented this code originally
            // in 2017, might have increased since) is around 500 - 600 MiB, so
            // this should be well within that range.
            //
            // (We want to strike a balance between a small Blob size -- which
            // causes lots of reading operations to be done, which takes a lot
            // of time -- and a huge Blob size, which can potentially run out
            // of memory, causing the read operation to fail.)
            this.BLOB_SIZE = 1048576;
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
            // TODO: set enter bindings for the <input>s here
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

            // When the node search button is clicked, or when Enter is
            // pressed in the node search input, start a search
            var searchFunc = this.searchForNodes.bind(this);
            $("#searchButton").click(searchFunc);
            domUtils.setEnterBinding("searchInput", searchFunc);

            // Viewing scaffolds / AGP files
            // Clicking on the "select a file" button should trigger a click
            // event on the actual <input> element, which will prompt the user
            // to select a file. This lets us use a visually consistent style
            // for the file selection interface. Web dev is weird!
            // For more details on why these sorts of solutions are needed, see
            // e.g. https://developer.mozilla.org/en-US/docs/Learn/Forms/Advanced_form_styling#file_input_types
            $("#scaffoldFileSelectButton").click(function () {
                $("#scaffoldFileSelector").click();
            });
            var loadAGP = this.beginLoadAGPFile.bind(this);
            $("#scaffoldFileSelector").change(loadAGP);
            var cycleLeft = this.cycleScaffoldsLeft.bind(this);
            $("#scaffoldCyclerLeft").click(cycleLeft);
            var cycleRight = this.cycleScaffoldsRight.bind(this);
            $("#scaffoldCyclerRight").click(cycleRight);
            var drawScaffold = this.drawSelectedScaffold.bind(this);
            $("#drawScaffoldButton").click(drawScaffold);

            // Graph image export buttons
            // (one is in the top-right of the graph display, another is in the
            // node selection menu)
            var exportFunc = this.exportGraphView.bind(this);
            $("#floatingExportButton").click(exportFunc);
            $("#exportImageButton").click(exportFunc);
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
                    '<th id="nodeInfoTable-' + attr + '">' + attr + "</th>"
                );
            });
            // Update an internal array of attributes in the same order as
            // columns in the info table -- will help when populating the
            // tables later on
            $("#nodeInfoTable tr:nth-child(2) > th").each(function (i, th) {
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
            $("#edgeInfoTable tr:nth-child(2) > th").each(function (i, th) {
                var attrName = th.id.slice(14);
                scope.edgeInfoTableAttrs.push(attrName);
            });
        }

        updateSelectedNodeInfo(eleID, selectOrUnselect) {
            var scope = this;
            // TODO abstract across nodes/edges/patterns -- basically the same
            if (selectOrUnselect === "select") {
                var nodeInfo = this.dataHolder.getNodeInfo(eleID);
                // TODO: cache this for this class since it doesn't change
                var nodeAttrs = this.dataHolder.getNodeAttrs();
                var rowHTML =
                    '<tr class="selectedEleRow" id="selectedEleRow' +
                    eleID +
                    '">';
                _.each(this.nodeInfoTableAttrs, function (attr) {
                    // Although these extra attributes are in theory arbitrary,
                    // for certain known attributes we take some extra effort
                    // and format things a bit nicely. This makes the user
                    // experience nicer.
                    // TODO abstract this to a util function.
                    var lowercaseattr = attr.toLowerCase();
                    var val = nodeInfo[nodeAttrs[attr]];

                    if (_.isNull(val)) {
                        val = scope.ATTR_NA;
                    } else {
                        if (attr === "length") {
                            // Unlike the old version of MgSc, we just say every
                            // length measure is in bp instead of trying to
                            // distinguish nt from bp. I think this is kosher,
                            // since it's not like we can tell if contigs are
                            // oriented are not for general formats like GFA...?
                            val = val.toLocaleString() + " bp";
                        } else if (attr === "coverage" || attr === "depth") {
                            // Show coverages with at most two decimal places worth
                            // of precision, but less if possible. I will be
                            // honest, this code is from the old MgSc and I have
                            // no idea how I came up with this. wtf marcus 4 years
                            // ago lol
                            val = Math.round(val * 100) / 100 + "x";
                        } else if (attr === "gc_content") {
                            // GC content should be shown as a percentage, rounded
                            // to two decimal places. We multiply by 10,000 because
                            // we're really multiplying by 100 twice: first to
                            // convert to a percentage, then to start the rounding
                            // process.
                            val = Math.round(val * 10000) / 100 + "%";
                        }
                    }
                    rowHTML += "<td>" + val + "</td>";
                });
                rowHTML += "</tr>";
                $("#nodeInfoTable").append(rowHTML);
            } else {
                this.removeSelectedEleInfo(eleID);
            }
        }

        /**
         * Adds or removes a row in the selected edge info table.
         *
         * Note that we have an extra param here -- the Cytoscape.js edge
         * element that is being updated. This is so we can get the original
         * source/target from this element easily.
         */
        updateSelectedEdgeInfo(ele, eleID, selectOrUnselect) {
            var scope = this;
            if (selectOrUnselect === "select") {
                var edgeData = ele.data();
                var edgeInfo = this.dataHolder.getEdgeInfo(
                    edgeData.origSrcID,
                    edgeData.origTgtID
                );
                var edgeAttrs = this.dataHolder.getEdgeAttrs();
                var rowHTML =
                    '<tr class="selectedEleRow" id="selectedEleRow' +
                    eleID +
                    '">';
                _.each(this.edgeInfoTableAttrs, function (attr) {
                    var val;
                    // NOTE: this is super inefficient since getNodeName()
                    // iterates over worst-case all nodes in the graph. TODO,
                    // at minimum do both searches at once, or figure out a way
                    // to limit the components checked.
                    if (attr === "source") {
                        val = scope.dataHolder.getNodeName(edgeData.origSrcID);
                    } else if (attr === "target") {
                        val = scope.dataHolder.getNodeName(edgeData.origTgtID);
                    } else {
                        // It's a "normal" attribute stored in the edge's data.
                        val = edgeInfo[edgeAttrs[attr]];
                        if (_.isNull(val)) {
                            val = scope.ATTR_NA;
                        }
                    }
                    rowHTML += "<td>" + val + "</td>";
                });
                rowHTML += "</tr>";
                $("#edgeInfoTable").append(rowHTML);
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
         * Returns an array containing all of the components to draw, based on
         * the current UI.
         *
         * If the components to draw are invalid in some way (e.g. they refer
         * to a component or a node that does not exist), this will open an
         * alert message (letting the user know what happened) and throw an
         * error (stopping execution of draw()).
         *
         * Notably, this does *NOT* modify this.currentlyDrawnComponents --
         * that should only be updated after stuff has actually been drawn,
         * just to be on the safe side.
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
            var cmpRank;
            if (this.cmpSelectionMethod === "single") {
                cmpRank = $("#componentselector").val();
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
                this.alertAndThrowIfFails(function () {
                    utils.throwErrOnEmptyOrWhitespace(name);
                });
                cmpRank = this.dataHolder.findComponentContainingNodeName(name);
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
                this.updateSelectedEdgeInfo(x, xID, selectOrUnselect);
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

        /**
         * Utility method. Runs a function, and if it throws an error then this
         * alerts the user with the error's message and then re-throws the
         * error.
         *
         * @param {Function} func
         *
         * @throws {Error} If func throws an error
         */
        alertAndThrowIfFails(func) {
            try {
                func();
            } catch (error) {
                // Alert the user about what went wrong, then re-throw the
                // error
                alert(error.message);
                throw error;
            }
        }

        /**
         * Centers the graph on a given list of node names separated by commas,
         * with spaces optional.
         *
         * @throws {Error} If the name text is invalid.
         */
        searchForNodes() {
            var nameText = $("#searchInput").val();
            var nodeNames;
            this.alertAndThrowIfFails(function () {
                nodeNames = utils.searchNodeTextToArray(nameText);
            });
            var notFoundNames = this.drawer.searchForNodes(nodeNames);
            if (notFoundNames.length > 0) {
                var notFoundNamesReadable = utils.arrToHumanReadableString(
                    notFoundNames
                );
                alert(
                    "Node name(s) " +
                        notFoundNamesReadable +
                        " were not found in the currently-drawn component. They may " +
                        "be within collapsed patterns or in another component " +
                        "of the graph, though."
                );
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
            // Only update this.currentlyDrawnComponents once
            // this.drawer.draw() is finished.
            this.currentlyDrawnComponents = componentsToDraw;
            if (!_.isEmpty(this.scaffoldID2NodeNames)) {
                // We need to alter the scaffold UI based on what scaffolds
                // "apply" to the currently drawn nodes
                this.currComponentsHaveScaffolds = false;
                $("#scaffoldCycler").addClass("notviewable");
                this.updateAvailableScaffolds(false);
            }
            // Enable controls that only have meaning when stuff is drawn (e.g.
            // the "fit graph" buttons)
            domUtils.enableDrawNeededControls();
        }

        /**
         * Starts the process of loading an AGP file.
         */
        beginLoadAGPFile() {
            var scope = this;
            var sfr = new FileReader();
            var inFile = document.getElementById("scaffoldFileSelector")
                .files[0];
            if (_.isUndefined(inFile)) {
                // This case can be triggered if the user cancels out of the
                // file selection dialog. In practice, beginLoadAGPFile()
                // should (as of writing) only be called when the AGP file
                // selection input changes: therefore, I think ending up in
                // this spot in the code requires first uploading a file,
                // then going to upload another one (and then cancelling out
                // of the resulting file selection dialog). Anyway, we don't
                // do anything noticeable in this case; if prior AGP file
                // information exists in the app, we retain it.
                return;
            }
            if (inFile.name.toLowerCase().endsWith(".agp")) {
                // The file is valid (for a very loose definition of "valid").
                // We can load it, and also clear information from any old AGP
                // files that exists.
                this.currComponentsHaveScaffolds = false;
                this.scaffoldID2NodeKeys = {};
                // Hide the UI elements associated with loaded AGP info
                $("#scaffoldInfoHeader").addClass("notviewable");
                $("#scaffoldCycler").addClass("notviewable");
                // Set some attributes of the FileReader object that we update
                // while reading the file.
                sfr.nextStartPosition = 0;
                sfr.partialLine = "";
                sfr.readingFinalBlob = false;
                // This is called after every Blob (manageably-sized chunk of
                // the file) is loaded via this FileReader object.
                sfr.onload = function (e) {
                    if (e.target.readyState === FileReader.DONE) {
                        var blobText = e.target.result;
                        var blobLines = blobText.split("\n");
                        // Newlines located at the very start or end of
                        // blobText will cause .split() to add "" in those
                        // places, which makes integrating sfr.partialLine with
                        // this a lot easier. (As opposed to us having to
                        // manually check for newlines in those places.)
                        var c;
                        if (blobLines.length > 1) {
                            // Process first line, which may or may not include
                            // sfr.partialLine's contents (sfr.partialLine may
                            // be "", or blobLines[0] may be "").
                            c = scope.integrateAGPLine(
                                sfr.partialLine + blobLines[0]
                            );
                            if (c !== 0) {
                                scope.clearScaffoldFS(true);
                                return;
                            }
                            sfr.partialLine = "";
                            // Process "intermediate" lines
                            for (var i = 1; i < blobLines.length - 1; i++) {
                                c = scope.integrateAGPLine(blobLines[i]);
                                if (c !== 0) {
                                    scope.clearScaffoldFS(true);
                                    return;
                                }
                            }
                            // Process last line in the blob: if we know this
                            // is the last blob we can read then we treat
                            // this last line as a complete line. Otherwise,
                            // we just store it in sfr.partialLine.
                            if (sfr.readingFinalBlob) {
                                c = scope.integrateAGPLine(
                                    blobLines[blobLines.length - 1]
                                );
                                if (c !== 0) {
                                    scope.clearScaffoldFS(true);
                                    return;
                                }
                            } else {
                                sfr.partialLine =
                                    blobLines[blobLines.length - 1];
                            }
                        } else if (blobLines.length === 1) {
                            // blobText doesn't contain any newlines
                            if (sfr.readingFinalBlob) {
                                c = scope.integrateAGPLine(
                                    sfr.partialLine + blobText
                                );
                                if (c !== 0) {
                                    scope.clearScaffoldFS(true);
                                    return;
                                }
                            } else {
                                sfr.partialLine += blobText;
                            }
                        }
                        scope.loadAGPFile(this, inFile, this.nextStartPosition);
                    }
                };
                // TODO: update the progress bar to "intermediate", and
                // use a timeout on loadAGPFile() so the DOM has time to update
                $("#agpLoadedFileName").addClass("notviewable");
                // Now that we've set up the onload for the sfr FileReader,
                // we can go ahead and call loadAGPFile(), which'll start
                // reading blobs of the AGP file.
                scope.loadAGPFile(sfr, inFile, 0);
            } else {
                alert("Please select a valid AGP file to load.");
            }
        }

        /**
         * Given a line of text, adds the node referenced in that line to
         * this.scaffoldID2NodeNames. Also adds the scaffold referenced in
         * that line, if not already defined (i.e. this is the first line
         * we've called this function on that references that scaffold).
         *
         * Saves node/scaffold info for the entire (laid-out) assembly graph,
         * not just the current connected component. This will allow us to
         * reuse the same mapping for multiple components' visualizations.
         *
         * @param {String} lineText Represents a single line in an AGP file.
         * @returns {Number} returnCode This will be nonzero if something went
         *                              wrong in processing this line (i.e.
         *                              it seems invalid) -- this should be a
         *                              sign to halt processing of this AGP
         *                              file. If this line seems good, returns
         *                              0.
         */
        integrateAGPLine(lineText) {
            // Avoid processing empty lines (e.g. due to trailing newlines
            // in files). Also avoid processing comment lines (lines that start
            // with #).
            if (lineText != "" && lineText[0] !== "#") {
                var lineColumns = lineText.split("\t");
                var scaffoldID = lineColumns[0];
                var nodeName = lineColumns[5];
                if (_.isUndefined(nodeName)) {
                    alert("Invalid line in input AGP file: \n" + lineText);
                    return -1;
                }
                // Save scaffold node composition data for all scaffolds, not
                // just scaffolds pertinent to the currently drawn components.
                if (_.isUndefined(this.scaffoldID2NodeNames[scaffoldID])) {
                    this.scaffoldID2NodeNames[scaffoldID] = [nodeName];
                } else {
                    this.scaffoldID2NodeNames[scaffoldID].push(nodeName);
                }
            }
            return 0;
        }

        /**
         * Updates the UI / app-level data about a scaffold being available.
         *
         * Our definition of "available" is that all of the nodes
         * within this scaffold are currently drawn (this can change depending
         * on what connected components are drawn -- therefore, this work will
         * need to be re-done when changing components).
         */
        addAvailableScaffold(scaffoldID) {
            if (!this.currComponentsHaveScaffolds) {
                this.currComponentsHaveScaffolds = true;
                this.currComponentsScaffolds = [];
                $("#drawScaffoldButton").text(scaffoldID);
                this.scaffoldCyclerCurrIndex = 0;
                $("#scaffoldCycler").removeClass("notviewable");
            }
            this.currComponentsScaffolds.push(scaffoldID);
        }

        /**
         * Finds scaffolds located in the currently drawn component(s),
         * using the keys to this.scaffoldID2NodeNames as a list of scaffolds
         * to try. Calls addAvailableScaffold() on each of these scaffolds.
         */
        updateAvailableScaffolds(agpFileJustLoaded) {
            var scope = this;
            var availScaffs = this.drawer.getAvailableScaffolds(
                this.scaffoldID2NodeNames
            );
            _.each(availScaffs, function (s) {
                scope.addAvailableScaffold(s);
            });
            this.updateScaffoldInfoHeader(agpFileJustLoaded);
        }

        /**
         * Recursively (...sort of) loads an AGP file using Blobs.
         *
         * (Technically, this function doesn't directly call itself,
         * but after the FileReader loads a Blob, it calls this method for
         * the next Blob.)
         *
         * fileReader and file should remain constant throughout the recursive
         * loading process, while filePosition will be updated as the file is
         * loaded. The initial call to loadAGPFile() should use
         * filePosition = 0 (in order to start reading the file from its 0th
         * byte, i.e. its beginning).
         */
        loadAGPFile(fileReader, file, filePosition) {
            // Only get a Blob if it'd have some data in it
            if (filePosition <= file.size) {
                // In interval notation, the slice includes bytes in the range
                // [filePosition, endPosition). That is, the endPosition byte
                // is not included in currentBlob.
                var endPosition = filePosition + this.BLOB_SIZE;
                var currentBlob = file.slice(filePosition, endPosition);
                if (endPosition > file.size) {
                    fileReader.readingFinalBlob = true;
                }
                fileReader.nextStartPosition = endPosition;
                fileReader.readAsText(currentBlob);
            } else {
                // We're done reading the AGP file! We can now update the UI.
                this.updateAvailableScaffolds(true);
            }
        }

        /**
         * Updates scaffoldInfoHeader depending on whether or not scaffolds
         * were identified in the currently drawn connected component(s).
         *
         * If agpFileJustLoaded is true, then the agpLoadedFileName will be
         * updated and scaffoldFileSelector will have its value cleared
         * (to allow for the same AGP file to be loaded again if necessary).
         * Therefore, agpFileJustLoaded should only be set to true when this
         * function is being called after an AGP file has just been loaded;
         * it should be set to false when, for example, a new component is
         * drawn (while an AGP file is already loaded) and we want to update
         * the UI.
         */
        updateScaffoldInfoHeader(agpFileJustLoaded) {
            if (this.currComponentsHaveScaffolds) {
                $("#scaffoldInfoHeader").html(
                    "<strong>Scaffolds in Connected Component</strong><br/>" +
                        "(Click to highlight in graph)"
                );
            } else {
                $("#scaffoldInfoHeader").html(
                    "No scaffolds apply to the nodes " +
                        "in the currently drawn connected component(s)."
                );
            }
            $("#scaffoldInfoHeader").removeClass("notviewable");
            // Perform a few useful operations if the user just loaded this
            // AGP file. These operations are not useful, however, if the
            // AGP file has already been loaded and we just ran
            // updateAvailableScaffolds().
            if (agpFileJustLoaded) {
                $("#agpLoadedFileName").html(
                    document.getElementById("scaffoldFileSelector").files[0]
                        .name
                );
                $("#agpLoadedFileName").removeClass("notviewable");
                this.clearScaffoldFS(false);
            }
        }

        /**
         * Clears the scaffold file selector's value attribute and calls
         * finishProgressBar().
         *
         * If errorOnAGPLoad is true, then this also:
         *  -Clears various info fields for scaffolds
         *  -Adds the "notviewable" class to #scaffoldCycler
         */
        clearScaffoldFS(errorOnAGPLoad) {
            if (errorOnAGPLoad) {
                this.scaffoldID2NodeNames = {};
                this.currComponentsScaffolds = [];
                this.currComponentsHaveScaffolds = false;
                $("#scaffoldCycler").addClass("notviewable");
            }
            document.getElementById("scaffoldFileSelector").value = "";
            // finishProgressBar();
        }

        /**
         * Called when the < button is clicked in the scaffold cycler.
         *
         * Changes the selected scaffold, and if needed "loops around".
         */
        cycleScaffoldsLeft() {
            if (this.scaffoldCyclerCurrIndex <= 0) {
                this.scaffoldCyclerCurrIndex =
                    this.currComponentsScaffolds.length - 1;
            } else {
                this.scaffoldCyclerCurrIndex--;
            }
            this.cycleToAndDrawScaffold();
        }

        /**
         * Called when the > button is clicked in the scaffold cycler.
         *
         * Changes the selected scaffold, and if needed "loops around".
         */
        cycleScaffoldsRight() {
            if (
                this.scaffoldCyclerCurrIndex >=
                this.currComponentsScaffolds.length - 1
            ) {
                this.scaffoldCyclerCurrIndex = 0;
            } else {
                this.scaffoldCyclerCurrIndex++;
            }
            this.cycleToAndDrawScaffold();
        }

        /**
         * Updates the draw scaffold button text, and draws this new scaffold.
         *
         * Intended to be used after clicking the cycle left / right button.
         */
        cycleToAndDrawScaffold() {
            var newScaffoldID = this.currComponentsScaffolds[
                this.scaffoldCyclerCurrIndex
            ];
            $("#drawScaffoldButton").text(newScaffoldID);
            this.drawSelectedScaffold();
        }

        /**
         * Highlights the nodes within a scaffold.
         *
         * Currently, this works by just selecting these nodes.
         */
        drawSelectedScaffold() {
            var scaffoldID = this.currComponentsScaffolds[
                this.scaffoldCyclerCurrIndex
            ];
            var nodeNames = this.scaffoldID2NodeNames[scaffoldID];
            this.drawer.highlightNodesInScaffold(nodeNames);
        }

        /**
         * Exports an image of the graph, calling downloadDataURI() to prompt
         * the user.
         *
         * The image filetype is determined using a button group in the control
         * panel.
         */
        exportGraphView() {
            // Should be either "PNG" or "JPG"
            var imgType = $("#imgTypeButtonGroup .btn.active").attr("value");
            var encodedImage = this.drawer.exportImage(imgType);
            var fn =
                "mgsc-" +
                utils.getFancyTimestamp(new Date()) +
                "." +
                imgType.toLowerCase();
            domUtils.downloadDataURI(fn, encodedImage, false);
        }
    }
    return { AppManager: AppManager };
});
