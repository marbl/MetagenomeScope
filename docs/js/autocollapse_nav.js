$(function() {
    $("nav a").on("click", function() {
        if ($("#main-navbar-content").hasClass("in")) {
            $("#main-navbar-content").collapse("hide");
        }
    });
});
