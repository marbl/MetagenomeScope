define(["jquery", "underscore"], function ($, _) {
    /**
     * Enables controls that don't need to have anything drawn to be useful
     * (e.g. graph info, component selector UI).
     *
     * @param {Number} numComponents The number of components in the graph.
     *                               The component selector -/+ buttons will
     *                               only be enabled if this is greater than 1,
     *                               which is a nice way of visually indicating
     *                               to the user when the graph contains (or
     *                               doesn't contain) multiple components.
     *
     * @throws {Error} If numComponents < 1, which indicates that something is
     *                 seriously wrong...
     */
    function enablePersistentControls(numComponents) {
        if (numComponents < 1) {
            throw new Error("numComponents < 1...?");
        } else {
            var compRankBtns = ["decrCompRankButton", "incrCompRankButton"];
            $(".persistentCtrl").each(function () {
                if (numComponents > 1 || !_.contains(compRankBtns, this.id)) {
                    // TODO: use more specific enabling func based on type...?
                    enableButton(this.id);
                }
            });
        }
    }

    function disablePersistentControls() {
        $(".persistentCtrl").each(function () {
            // TODO: use more specific enabling func based on type...?
            disableButton(this.id);
        });
    }

    /**
     * Enables controls that need to have something drawn to be useful (e.g.
     * display options, node colorization, ...)
     */
    function enableDrawNeededControls() {
        $(".drawCtrl").each(function () {
            domUtils.enableButton(this.id);
        });
    }

    function disableDrawNeededControls() {
        $(".drawCtrl").each(function () {
            domUtils.disableButton(this.id);
        });
    }

    /**
     * Enables a disabled <button> element that is currently disabled: that
     * is, it has the disabled class (which covers Bootstrap styling) and
     * has the disabled="disabled" property.
     *
     * @param {String} buttonID
     */
    function enableButton(buttonID) {
        $("#" + buttonID).removeClass("disabled");
        $("#" + buttonID).prop("disabled", false);
    }

    /**
     * Disables an enabled <button> element.
     *
     * @param {String} buttonID
     */
    function disableButton(buttonID) {
        $("#" + buttonID).addClass("disabled");
        $("#" + buttonID).prop("disabled", true);
    }

    /**
     * Opposite of disableInlineRadio().
     *
     * @param {String} inputID
     */
    function enableInlineRadio(inputID) {
        $("#" + inputID).prop("disabled", false);
    }

    /**
     * Like disableButton(), but for the inline radio buttons used for node
     * colorization options. Since these don't have "disabled" as a class,
     * we use a different method for disabling them.
     *
     * @param {String} inputID
     */
    function disableInlineRadio(inputID) {
        $("#" + inputID).prop("disabled", true);
    }

    return {
        enablePersistentControls: enablePersistentControls,
        disablePersistentControls: disablePersistentControls,
        enableDrawNeededControls: enableDrawNeededControls,
        disableDrawNeededControls: disableDrawNeededControls,
        enableButton: enableButton,
        disableButton: disableButton,
        enableInlineRadio: enableInlineRadio,
        disableInlineRadio: disableInlineRadio,
    };
});
