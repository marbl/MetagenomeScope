define([], function () {
    class DataHolder {
        constructor(dataJSON) {
            this.data = dataJSON;
        }
    }
    return { DataHolder: DataHolder };
});
