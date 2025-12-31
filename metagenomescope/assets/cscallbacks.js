/* Certain operations (like calling cy.fit() to fit the display to everything
 * in the graph) are not accessible through Dash-Cytoscape's interface, as far
 * as I can tell.
 *
 * We can work around this by extracting the existing Cytoscape.js instance
 * after-the-fact and then using it to do stuff. There appears to be no
 * official, well-documented way to do this, but the secret evil way of
 * doing this is accessing the _cyreg.cy attribute of the DOM element
 * containing the Cytoscape.js instance (which we've named "cy" above).
 * This is from https://stackoverflow.com/a/52603597.
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

// https://dash.plotly.com/clientside-callbacks
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
    },
    selection: {
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
                    // BE VERY CAREFUL about escaping strings here with
                    // backslashes. This can cause Dash to jank out with
                    // this infuriatingly vague error:
                    // https://community.plotly.com/t/clientside-callback-example-with-js-function-throws-cannot-read-property-apply-of-undefined-error/44411
                    //
                    // Also, including three queries to detect split nodes is
                    // very silly. Maybe assign each node a "basename" property
                    // or something in to_cyjs() to prevent the need for this?
                    // Or maybe the space requirement from that is prohibitive.
                    //
                    // Also whenever you update this callback you have to use
                    // like ctrl+shift+R or something to get rid of Dash's
                    // cache. Otherwise you get the aforementioned terrible
                    // vague error. Writing this function raised my blood
                    // pressure i think
                    newEles = cy.nodes(
                        '[label="' +
                            nodename +
                            '"], ' +
                            '[label="' +
                            nodename +
                            '-L"], ' +
                            '[label="' +
                            nodename +
                            '-R"]',
                    );
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
                cy.filter(":selected").unselect();
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
                cy.fit(eles);
                cy.filter(":selected").unselect();
                eles.select();
            }
        },
    },
});
