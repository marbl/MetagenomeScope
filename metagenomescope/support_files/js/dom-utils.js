define(["jquery", "underscore", "utils"], function ($, _, utils) {
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
            enableButton(this.id);
        });
    }

    function disableDrawNeededControls() {
        $(".drawCtrl").each(function () {
            disableButton(this.id);
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

    /**
     * Returns null if the value indicated by the string is not an integer.
     * Returns -1 if it is an integer but is less than the min component rank.
     * Returns 1 if it is an integer but is greater than the max component rank.
     * Returns 0 if it is an integer and is within the range [min rank, max rank].
     *
     * @param {String}
     * @returns {Number or null}
     */
    function compRankValidity(strVal) {
        if (!utils.isValidInteger(strVal)) return null;
        var intVal = parseInt(strVal);
        if (intVal < parseInt($("#componentselector").prop("min"))) return -1;
        if (intVal > parseInt($("#componentselector").prop("max"))) return 1;
        return 0;
    }

    /**
     * Decrements the size rank of the component selector by 1. If the current
     * value of the component selector is not an integer, then the size rank is set
     * to the minimum size rank; if the current value is an integer that is greater
     * than the maximum size rank, then the size rank is set to the maximum size
     * rank.
     *
     * Also, if the size rank is equal to the minimum size rank, nothing happens.
     */
    function decrCompRank() {
        var csIDstr = "#componentselector";
        var currRank = $(csIDstr).val();
        var minRank = parseInt($(csIDstr).prop("min"));
        var validity = compRankValidity(currRank);
        if (validity === null || parseInt(currRank) < minRank + 1) {
            $(csIDstr).val(minRank);
        } else if (validity === 1) {
            $(csIDstr).val($(csIDstr).prop("max"));
        } else {
            $(csIDstr).val(parseInt(currRank) - 1);
        }
    }

    /**
     * Increments the size rank of the component selector by 1. Same "limits" as
     * in the first paragraph of decrCompRank()'s comments.
     *
     * Also, if the size rank is equal to the maximum size rank, nothing happens.
     */
    function incrCompRank() {
        var csIDstr = "#componentselector";
        var currRank = $(csIDstr).val();
        var maxRank = parseInt($(csIDstr).prop("max"));
        var validity = compRankValidity(currRank);
        if (validity === null || validity === -1) {
            $(csIDstr).val($(csIDstr).prop("min"));
        } else if (currRank > maxRank - 1) {
            $(csIDstr).val(maxRank);
        } else {
            $(csIDstr).val(parseInt(currRank) + 1);
        }
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
        compRankValidity: compRankValidity,
        decrCompRank: decrCompRank,
        incrCompRank: incrCompRank,
    };
});
