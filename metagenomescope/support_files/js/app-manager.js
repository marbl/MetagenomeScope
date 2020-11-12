define(["jquery", "bootstrap", "cytoscape", "util"], function (
    $,
    bootstrap,
    cy,
    util
) {
    class AppManager {
        constructor(dataHolder) {
            this.dataHolder = dataHolder;
            $(this.doThingsWhenDOMReady.bind(this));
        }

        doThingsWhenDOMReady() {
            console.log(
                "This is a " +
                    this.dataHolder.fileType() +
                    " file named " +
                    this.dataHolder.fileName() +
                    " with " +
                    this.dataHolder.numComponents() +
                    " components."
            );
        }
    }
    return { AppManager: AppManager };
});
