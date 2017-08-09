/* Opens a given image in a new tab/window (assumes that the event was
 * propagated from an <img> tag).
 */
function openScreenshot(event) {
    window.open(event.target.src, "_blank");
}
