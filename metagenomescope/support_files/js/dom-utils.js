define(["jquery"], function ($) {
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
        enableButton: enableButton,
        disableButton: disableButton,
        enableInlineRadio: enableInlineRadio,
        disableInlineRadio: disableInlineRadio,
    };
});
