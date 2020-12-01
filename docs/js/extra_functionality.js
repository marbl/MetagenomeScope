/* Copyright (C) 2017 Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
 * Authored by Marcus Fedarko
 *
 * This file is part of MetagenomeScope.
 *
 * MetagenomeScope is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * MetagenomeScope is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with MetagenomeScope.  If not, see <http://www.gnu.org/licenses/>.
 */
/*
 * Once the user clicks on a link within the nav (when the nav is in its
 * "compressed" view, e.g. for small screens), the binding created in this
 * script automatically collapses the nav. This makes the user experience of
 * going somewhere on the page using the nav feel a lot more fluid, since they
 * don't have to manually close the nav.
 *
 * NOTE that this approach will probably cause problems if the nav contains
 * things like dropdowns, due to its indiscriminate identification of <a>s in
 * the nav [1]. This should be refined a bit if we add more "features" to the
 * nav. That being said, this approach works nicely in that it also closes the
 * nav when the navbar-brand <a> is clicked, which matches with the behavior of
 * the navbar-brand as a link to the top of the page.
 *
 * [1] See Kevin Nelson's answer to this Stack Overflow question for more
 * information on this sort of solution and its corner cases:
 * https://stackoverflow.com/questions/21203111/bootstrap-3-collapsed-menu-doesnt-close-on-click
 */
$(function () {
    $("nav a").on("click", function () {
        if ($("#main-navbar-content").hasClass("in")) {
            $("#main-navbar-content").collapse("hide");
        }
    });
});

/* Opens a given image in a new tab/window (assumes that the event was
 * propagated from an <img> tag).
 */
function openScreenshot(event) {
    window.open(event.target.src, "_blank");
}
