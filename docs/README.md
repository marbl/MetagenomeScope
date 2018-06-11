Homepage/"info site" for
[MetagenomeScope](http://github.com/marbl/MetagenomeScope), a
visualization tool for metagenomic assembly graphs.

## Acknowledgements
This site uses [Bootstrap](http://getbootstrap.com/) and
[jQuery](http://jquery.com/), both of which are licensed under the MIT License.
Copies of their licenses can be found in the `dependency_licenses/` folder,
which is located in the root of the MetagenomeScope repository.

### HTML (`index.html`)

Most of the markup defining the navigation bar ("navbar") is adapted from
Bootstrap's documentation on navbars, located
[here](https://getbootstrap.com/docs/3.3/components/#navbar).

### CSS (`css/vaguely_adequate.css`)

The basic body styling of the site was inspired by
[this website](http://bettermotherfuckingwebsite.com/)
(that site's URL/name contains some profanity), which was created by
[Drew McConville](https://twitter.com/drew_mc) and
[Gabe Hammersmith](https://twitter.com/gabehammersmith).

Additionally, this website's CSS adds a positive padding and negative margin
to each section header accessible from the navbar. This ensures that, when these
anchors are accessed, the navbar is positioned above the corresponding section's
header (instead of overlapping with it).
This general solution is described in a lot of places online, but I'm pretty
sure my implementation here was inspired by Method C in Nicolas Gallagher's
tutorial [here](http://nicolasgallagher.com/jump-links-and-viewport-positioning/demo/#method-C).
