/* Once the user clicks on a link within the nav (when the nav is in its
 * "compressed" view, e.g. for small screens), this automatically collapses the
 * nav. This makes the user experience of going somewhere on the page feel a
 * lot more fluid, since they don't have to manually close the nav.
 */
$(function() {
    $("nav a").on("click", function() {
        if ($("#main-navbar-content").hasClass("in")) {
            $("#main-navbar-content").collapse("hide");
        }
    });
});
