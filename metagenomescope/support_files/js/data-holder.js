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
    }
    return { DataHolder: DataHolder };
});
