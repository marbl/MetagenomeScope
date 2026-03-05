/* Certain operations (like calling cy.fit() to fit the display to everything
 * in the graph) are not accessible through Dash-Cytoscape's interface, at
 * least as of writing.
 *
 * We can work around this by extracting the existing Cytoscape.js instance
 * after-the-fact and then using it to do stuff. There appears to be no
 * official, well-documented way to do this, but the secret evil way of
 * doing this is accessing the _cyreg.cy attribute of the DOM element
 * containing the Cytoscape.js instance (which we've given the ID "cy" in
 * main.py). This workaround is from https://stackoverflow.com/a/52603597.
 *
 * I am hesitant to rely on such a silly hack for this, but it appears that
 * this has remained unbroken for 7+ years now -- and it looks like lots of
 * other Dash-Cytoscape projects use this same workaround, judging by
 * https://github.com/search?q=_cyreg.cy+dash&type=code
 *
 * So I guess we can keep this workaround for now. In the future, if this
 * suddenly breaks, maybe we can just rip out Dash-Cytoscape entirely in
 * favor of handling all of the Cytoscape.js stuff ourself in clientside
 * callbacks / etc. Or we can access the underlying cy instance in a
 * different way (e.g.
 * https://github.com/plotly/dash-cytoscape/issues/187#issuecomment-1924583683
 * which I don't really understand -- where is the "cy" variable coming from
 * there?).
 */
function getCy() {
    return document.getElementById("cy")._cyreg.cy;
}


/* Extracts data from e.g. a collection of selected nodes in Cytoscape.js. */
function getCyCollectionData(collection) {
    let objData = [];
    for (let i = 0; i < collection.length; i++) {
        let o = collection[i];
        objData.push(o.data());
    }
    return objData;
}

/* If an edge is tagged as a badLine that Cytoscape.js refuses to draw, then
 * remove the .withctrlpts class -- which should change it back to a regular
 * "bezier"-style edge.
 */
function rescueEdges(edges, edgeLabels) {
    let rescuedIDs = [];
    let rct = 0;
    edges.forEach(function (e) {
        if (e._private.rscratch.badLine) {
            // If an edge is marked as bad but doesn't have the withctrlpts
            // class, this probably indicates that the user both selected the
            // edge and a node adjacent to it. In this case, the question of
            // which rescuing callback is triggered first is arbitrary, right?
            // Both callbacks would go through the relevant edges, and the
            // first callback would rescue edges as needed and the second
            // would just see the already-rescued edge and be like dang that's
            // crazy. It looks like there is some delay between when we fix
            // the edge and when Cytoscape.js restores the badLine attribute?
            // (Or maybe the Dash callbacks just fire too quickly together
            // or something.)
            //
            // I guess this could also indicate e.g. that the user has moved
            // stuff around in a way that breaks the edge display, e.g.
            // smushing a node into another node or something. In that case
            // (and really in either case) there is nothing more we can do
            // here -- things should already be okay.
            if (e.hasClass("withctrlpts")) {
                e.removeClass("withctrlpts");
                rescuedIDs.push(e.data("id"));
                rct++;
            }
        }
    });
    if (rct > 0) {
        console.log(
            "Of the",
            edges.length,
            edgeLabels,
            "-- detected and rescued",
            rct,
            "bad edge(s):",
        );
        console.log(rescuedIDs.join("\n"));
    }
}

function tryToSetBadEdgeDragRescuer(cy) {
    // this only needs to be set once
    const SET_FLAG = "_mgscBindingsSet";
    if (!cy.data(SET_FLAG)) {
        // so far it does not look like this is a bottleneck, but we could
        // rate limit this if desired (or e.g. only do stuff when dragging
        // is done)
        cy.on("drag", "node", function (evt) {
            let node = evt.target;
            rescueEdges(
                node.connectedEdges(),
                "adjacent edge(s) to dragged node(s)",
            );
        });
        cy.data(SET_FLAG, true);
    }
}

/* For more information about clientside callbacks, see
 * https://dash.plotly.com/clientside-callbacks -- this next line
 * (window.dash_clientside...) is based on their docs.
 */
window.dash_clientside = Object.assign({}, window.dash_clientside, {
    toasts: {
        showNewToast: function (toasts) {
            /* It looks like Bootstrap requires us to use JS to show the toast. If we
             * try to show it ourselves (by just adding the "show" class when creating
             * the toast) then the toast never goes away and also doesn't have smooth
             * animation when appearing. As far as I can tell, using a clientside
             * callback (https://dash.plotly.com/clientside-callbacks) is the smoothest
             * way to do this.
             *
             * (The "data-mgsc-shown" attribute makes sure that we don't re-show a toast
             * that has already been shown. This is because one of the draw() callback's
             * outputs is the toastHolder's children, so even if we just draw the graph
             * successfully without triggering any new toasts then this clientside
             * callback will still be triggered. Oh no! "data-mgsc-shown" fixes things.)
             */
            var tele = document.getElementById("toastHolder").lastChild;
            if (
                tele !== null &&
                tele.getAttribute("data-mgsc-shown") === "false"
            ) {
                var toast = bootstrap.Toast.getOrCreateInstance(tele);
                toast.show();
                tele.setAttribute("data-mgsc-shown", "true");
            }
        },
    },
    cyManip: {
        init: function(onPageLoad, stylesheet) {
            let cy = cytoscape({
                container: document.getElementById("cy"),
                style: stylesheet,
                maxZoom: 9,
                boxSelectionEnabled: true
            });
            // Cytoscape.js triggers a unique event for each selected node.
            // You'd think that we should then just append the selected node
            // to a list of "currently selected nodes" that triggers a Dash
            // callback, right? Unfortunately!!! this is either impossible or
            // super obscure, because dash_clientside.set_props() exists but
            // dash_clientside.get_props() does not exist.
            //
            // We could then fix THAT by having each event callback go through
            // the full collection of selected nodes (cy.nodes(":selected")),
            // but the problem with THAAAT is that it's inefficient (we would
            // be building up the same silly list of node data O(N^2) times,
            // if the user box-selects a bunch of nodes at once).
            //
            // A nice way around this is *debouncing* the selection events, so
            // that we only build this list of selected node data (and update
            // Dash about this) once per selection event. This is based on the
            // beautiful solution in https://stackoverflow.com/a/16701044, and
            // happens to also match what Dash-Cytoscape is doing under the
            // hood (https://github.com/plotly/dash-cytoscape/blob/f96e760f3b84c3f4d7ecbfaa905e9d57c698456d/src/lib/components/Cytoscape.react.js#L189-L203).
            
            // both Max Franz' solution & Dash Cytoscape's use 100 ms, but I
            // think using a shorter interval is fine since it makes things
            // snappier (plus, even if this messes up and results in multiple
            // invocations of dash, it won't break anything - it will just be
            // slightly inefficent)
            let DEBOUNCE_TIME_MS = 50;
            //// node / pattern selection
            let selectNodeTimeout;
            cy.on("select unselect", "node", function(e) {
                clearTimeout(selectNodeTimeout);
                selectNodeTimeout = setTimeout(function() {
                    let ndata = getCyCollectionData(cy.nodes(":selected"));
                    dash_clientside.set_props(
                        "selectedNodeAndPatternJSONFromJS", { data: ndata }
                    );
                }, DEBOUNCE_TIME_MS);
            });
            //// edge selection
            // (in theory i guess we could combine this with the above stuff
            // but whatever this matches how Dash-Cytoscape separated things)
            let selectEdgeTimeout;
            cy.on("select unselect", "edge", function(e) {
                clearTimeout(selectEdgeTimeout);
                selectEdgeTimeout = setTimeout(function() {
                    let edata = getCyCollectionData(cy.edges(":selected"));
                    dash_clientside.set_props(
                        "selectedEdgeJSONFromJS", { data: edata }
                    );
                }, DEBOUNCE_TIME_MS);
            });
        },
        changeEles: function(eles) {
            let cy = getCy();
            // TODO: is there a more performant way to wipe everything? I mean
            // we COULD just call cy.destroy() but that is not recommended per
            // https://js.cytoscape.org/#performance/optimisations
            cy.remove(cy.elements());
            cy.add(eles);
            cy.fit();
        },
        changeLayoutParams: function(layoutParams) {
            let cy = getCy();
            cy.layout(layoutParams);
        },
        changeStylesheet: function(stylesheet) {
            let cy = getCy();
            cy.style(stylesheet);
        },
        rescueNewlyDrawnBadEdges: function (currDrawnInfo) {
            let cy = getCy();
            rescueEdges(cy.edges(), "edge(s) on initial draw");
            // This isn't its own function because of a Dash bug? with multiple
            // clientside callbacks with the same input and no outputs -
            // https://github.com/plotly/dash/issues/3596
            tryToSetBadEdgeDragRescuer(cy);
        },
        rescueAdjacentBadEdges: function (selectedNodes) {
            if (selectedNodes.length > 0) {
                let cy = getCy();
                let adjEdges = cy.collection();
                for (let i = 0; i < selectedNodes.length; i++) {
                    let n = selectedNodes[i];
                    adjEdges = adjEdges.union(
                        cy.getElementById(n.id).connectedEdges(),
                    );
                }
                rescueEdges(adjEdges, "adjacent edge(s) to selected node(s)");
            }
        },
        rescueSelectedBadEdges: function (selectedEdges) {
            if (selectedEdges.length > 0) {
                let cy = getCy();
                let selEdges = cy.collection();
                for (let i = 0; i < selectedEdges.length; i++) {
                    selEdges = selEdges.union(
                        cy.getElementById(selectedEdges[i].id),
                    );
                }
                rescueEdges(selEdges, "selected edge(s)");
            }
        },
        fit: function (nClicks) {
            let cy = getCy();
            cy.fit();
        },
        fitToSelected: function (nClicks) {
            let cy = getCy();
            // NOTE: in older versions of metagenomescope, we maintained a list of
            // selected nodes/edges/patterns using cy.on('select'), etc. This let us
            // avoid having to search through everything drawn in the graph when fitting
            // to all selected elements. I may do this eventually but for now it is
            // sufficient to just search through the graph in this callback.
            cy.fit(cy.$(":selected"));
        },
        takeScreenshot: function(request) {
            let cy = getCy();
            // NOTE: the first way I tried to implement this involved just
            // determining the screenshot function based on the image type.
            // so, "png" --> cy.png(), "jpg" --> cy.jpg(), etc.
            // This resulted in bizarre errors of the form
            // 'can't access property "_private", this is undefined'.
            //
            // IT TURNS OUT THAT this is because when you pass functions around
            // in JS the meaning of the "this" keyword can get messed up --
            // see https://stackoverflow.com/a/59060545.
            //
            // You apparently can sort of solve this by replacing e.g.
            // "f = cy.png;" with "f = cy.png.bind(cy);", but that's hideous,
            // isn't it?
            //
            // So ........ let's just call each function separately to avoid
            // these nightmares
            let content;
            let fnSuffix;
            let isBase64 = true;
            if (request.imageType === "png") {
                content = cy.png(request.options);
                fnSuffix = "png";
            } else if (request.imageType === "jpg") {
                content = cy.jpg(request.options);
                fnSuffix = "jpg";
            } else if (request.imageType === "svg") {
                content = cy.svg(request.options);
                fnSuffix = "svg";
                isBase64 = false;
            } else {
                alert("bad screenshot request image type - see console");
                console.log(request);
                return;
            }
            if (isBase64) {
                // slice off the "data:image/png:base64," prefix, which
                // dcc.Download does not expect -
                // https://stackoverflow.com/a/40289667
                content = content.split(",")[1];
            }
            return {
                filename: request.filename + "." + fnSuffix,
                content: content,
                base64: isBase64
            };
        }
    },
    selection: {
        /* Selects and zooms to a list of node names.
         *
         * @param {Object} nodeSelectionInfo contains information from the
         *     "nodeSelectionInfo" dcc.Store in the dash application. Basically
         *     this should contain two entries: (1) "requestGood" (maps to a
         *     bool) and (2) "nodesToSelect" (maps to an array).
         *
         * If requestGood maps to a falsy value, then this will just log that
         * we caught a bad search request and not do anything.
         *
         * Otherwise, this will unselect all currently-selected nodes in the
         * Cytoscape.js graph, select all nodes in the array of nodesToSelect,
         * and zoom to them in the graph.
         *
         * Note that node names in nodeToSelect should match up exactly with
         * the labels of currently drawn nodes in the graph (e.g. "40-L"
         * instead of "40").
         */
        showSelectedNodes: function (nodeSelectionInfo) {
            if (!nodeSelectionInfo["requestGood"]) {
                console.log("Caught a bad search request.");
            } else {
                let cy = getCy();
                let eles = cy.collection();
                for (
                    var i = 0;
                    i < nodeSelectionInfo["nodesToSelect"].length;
                    i++
                ) {
                    let nodename = nodeSelectionInfo["nodesToSelect"][i];
                    newEles = cy.nodes('[label="' + nodename + '"]');
                    if (newEles.empty()) {
                        // I think we could show a toast here but that will
                        // take some finagling
                        alert(
                            "Node with name " +
                                nodename +
                                " not currently " +
                                "drawn? This should never happen by this point.",
                        );
                        return;
                    }
                    eles = eles.union(newEles);
                }
                cy.fit(eles);
                cy.$(":selected").unselect();
                eles.select();
            }
        },
        showSelectedPath: function (pathSelectionInfo) {
            if (!pathSelectionInfo["requestGood"]) {
                console.log("Caught a bad path selection request.");
            } else {
                let cy = getCy();
                let eles = cy.collection();
                for (var i = 0; i < pathSelectionInfo["eles"].length; i++) {
                    let name = pathSelectionInfo["eles"][i];
                    if (pathSelectionInfo["nodes"]) {
                        newEles = cy.nodes(
                            '[label="' +
                                name +
                                '"], ' +
                                '[label="' +
                                name +
                                '-L"], ' +
                                '[label="' +
                                name +
                                '-R"]',
                        );
                    } else {
                        newEles = cy.edges('[edgeID="' + name + '"]');
                    }
                    if (newEles.empty()) {
                        alert(
                            "Element with name " +
                                name +
                                " not currently " +
                                "drawn? This should never happen by this point.",
                        );
                        return;
                    }
                    eles = eles.union(newEles);
                }
                // The key term "zoom" is set in ui_config.py as
                // PATH_SETTINGS_ZOOM.
                // I don't like duplicating it here, but... I mean, that's the
                // easiest way to do this.
                // I guess we COULD define some mechanism for passing
                // config variables from py -> js but whatever
                if (pathSelectionInfo["path_settings"].indexOf("zoom") >= 0) {
                    cy.fit(eles);
                }
                cy.$(":selected").unselect();
                eles.select();
            }
        },
    },
});
