define(["jquery", "bootstrap", "cytoscape", "util"], function (
    $,
    bootstrap,
    cy,
    util
) {
    class AppManager {
        constructor(dataHolder) {
            this.dataHolder = dataHolder;
            $(this.doThingsWhenDOMReady);
        }

        doThingsWhenDOMReady() {
            console.log("hi");
        }
    }
    return { AppManager: AppManager };
});
