define(["jquery", "bootstrap", "cytoscape"], function ($, bootstrap, cy) {
    class AppManager {
        constructor(dataHolder) {
            this.dataHolder = dataHolder;
        }
    }
    return { AppManager: AppManager };
});
