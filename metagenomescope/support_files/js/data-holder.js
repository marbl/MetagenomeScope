define([], function () {
    class DataHolder {
        constructor(dataJSON) {
            this.data = dataJSON;
        }

        numComponents() {
            return this.data.components.length;
        }

        fileType() {
            return this.data.input_file_type;
        }

        fileName() {
            return this.data.input_file_basename;
        }
    }
    return { DataHolder: DataHolder };
});
