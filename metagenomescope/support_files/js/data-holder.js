define(["underscore"], function (_) {
    class DataHolder {
        constructor(dataJSON) {
            this.data = dataJSON;
        }

        /**
         * Returns the number of connected components in the graph, including
         * those that were skipped during layout.
         *
         * @returns {Number}
         */
        numComponents() {
            return this.data.components.length;
        }

        /**
         * Returns the number of nodes in the graph.
         *
         * This doesn't draw a distinction between "positive" and "negative"
         * nodes -- so for graphs where the negative nodes are implied (e.g.
         * Velvet) the caller may want to divide these counts by 2.
         *
         * Also, this includes node counts for _all_ components, even those
         * that have not been laid out (and thus for which no data is included
         * in the data JSON we have access to). (This is doable because the
         * Python code just computes the total number of nodes specifically for
         * showing here. No point making things more confusing than they
         * already are.)
         *
         * ... And this includes duplicate nodes (e.g. those created to
         * separate adjacent bubble patterns).
         *
         * @returns {Number}
         */
        totalNumNodes() {
            return this.data.total_num_nodes;
        }

        /**
         * Returns the number of edges in the graph.
         *
         * As with totalNumNodes(), this includes "implied" edges, spans all
         * components (including non-laid-out ones), and includes "duplicate"
         * edges (non-real edges that connect a node with its duplicate).
         *
         * @returns {Number}
         */
        totalNumEdges() {
            return this.data.total_num_edges;
        }

        /**
         * Returns the filetype of the graph provided to the python script.
         *
         * @returns {String}
         */
        fileType() {
            return this.data.input_file_type;
        }

        /**
         * Returns the file name of the graph provided to the python script.
         *
         * This is just the "base name" of the file, so it doesn't have
         * directory information included -- e.g. if the file path provided to
         * the python script was /home/marcus/graphs/my_cool_graph.gfa, then
         * this should just be "my_cool_graph.gfa".
         *
         * @returns {String}
         */
        fileName() {
            return this.data.input_file_basename;
        }

        /**
         * Returns the (1-indexed) number of the first component that we were
         * able to lay out.
         *
         * The purpose of this is so that if, for example, component 1 was too
         * large to draw, we can start at component 2.
         *
         * Notes:
         *  1. There isn't a guarantee that only the first few components are
         *  not drawable (since components are sorted by nodes first, you can
         *  imagine the case where a later component has a small enough amnt of
         *  nodes but way too many edges). The purpose of this function is just
         *  to give the user a good default component to start with.
         *
         *  2. We raise an error in the python side of things if all components
         *  are too large, so at least one of the components must have been
         *  laid out already.
         *
         * @returns {Number}
         *
         * @throws {Error} If the python script messed up and all of the
         *                 components are marked as skipped. Yikes!
         */
        smallestViewableComponent() {
            for (var i = 0; i < this.data.components.length; i++) {
                if (!this.data.components[i].skipped) {
                    return i + 1;
                }
            }
            throw new Error(
                "No components were laid out -- python script broken."
            );
        }

        /**
         * Returns the size rank of the component containing a node with a
         * given name. We stop after finding a match -- so this will break if
         * multiple nodes share a name (this should never happen in practice).
         *
         * If no component contains a node with the given name, this returns
         * -1 (so the caller can throw an error / alert the user).
         *
         * This is currently case sensitive. I guess we could change that in
         * the future if people request it (although then we would run into the
         * problem of ambiguity in search results, unless we enforce that node
         * names must be unique ignoring case).
         *
         * @param {String} queryName
         *
         * @returns {Number} cmpRank (1-indexed, so the largest component is 1,
         *                           etc.)
         */
        findComponentContainingNodeName(queryName) {
            var nodeNamePos = this.data.node_attrs.name;
            // Part 1: run the  search (_.findIndex() and _.some() should both
            // use short circuiting, so potentially these won't involve
            // searching every node in the graph)
            var matchingCmpIdx = _.findIndex(this.data.components, function (
                cmp
            ) {
                if (!cmp.skipped) {
                    // Return true if any of the values in cmp.nodes (the
                    // values in this Object are Arrays of node data) has the
                    // "name" property that matches the query name
                    return _.some(cmp.nodes, function (nodeData) {
                        return nodeData[nodeNamePos] === queryName;
                    });
                }
                return false;
            });
            // Part 2: figure out if the search failed or succeeded
            if (matchingCmpIdx === -1) {
                // No components contained this node name. Sometimes it be like
                // that. Just return -1 so it's clear that the search failed.
                // (We could also simplify this by just returning
                // matchingCmpIdx + 1 regardless of the outcome, since it's not
                // like 0 is being used, but that strikes me as messy and prone
                // to errors.
                return -1;
            } else {
                // The search succeeded! One of the components contains this
                // node. Component size ranks are 1-indexed, so increment the
                // index of the component we found by 1.
                return matchingCmpIdx + 1;
            }
        }

        /**
         * Returns an Array with all component size ranks that were laid out.
         *
         * Size ranks given in the array are 1-indexed.
         *
         * @returns {Array}
         */
        getAllLaidOutComponentRanks() {
            var laidOutRanks = [];
            for (var i = 0; i < this.data.components.length; i++) {
                if (!this.data.components[i].skipped) {
                    laidOutRanks.push(i + 1);
                }
            }
            return laidOutRanks;
        }

        /**
         * Throws an error if a component size rank is invalid.
         *
         * This is not designed to be used for user-facing validation -- this
         * is an internal method, meant to catch errors that I accidentally
         * make.
         *
         * @param {Number} sizeRank
         *
         * @returns {Boolean} true if the size rank is valid. This shouldn't be
         *                    relied on, though; this function should probably
         *                    just be called without caring about the return
         *                    value.
         *
         * @throws {Error} If sizeRank is not a positive integer in the range
         *                 [1, this.data.components.length]
         *
         */
        validateComponentRank(sizeRank) {
            if (sizeRank > 0 && Number.isInteger(sizeRank)) {
                if (sizeRank <= this.data.components.length) {
                    return true;
                } else {
                    throw new Error(
                        "Size rank of " +
                            sizeRank +
                            " is too large: only " +
                            this.data.components.length +
                            " components in the graph"
                    );
                }
            } else {
                throw new Error(
                    "Size rank of " + sizeRank + " isn't a positive integer"
                );
            }
        }

        /**
         * Returns an Object with data for all patterns in a given component.
         *
         * @returns {Array}
         */
        getPatternsInComponent(sizeRank) {
            this.validateComponentRank(sizeRank);
            return this.data.components[sizeRank - 1].patts;
        }

        /**
         * Returns an Object with data for all nodes in a given component.
         *
         * @returns {Array}
         */
        getNodesInComponent(sizeRank) {
            this.validateComponentRank(sizeRank);
            return this.data.components[sizeRank - 1].nodes;
        }

        /**
         * Returns an Object with data for all edges in a given component.
         *
         * @returns {Array}
         */
        getEdgesInComponent(sizeRank) {
            this.validateComponentRank(sizeRank);
            return this.data.components[sizeRank - 1].edges;
        }
    }
    return { DataHolder: DataHolder };
});
