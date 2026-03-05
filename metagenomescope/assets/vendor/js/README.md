# Third-party JS libraries

## Why are the JS files numbered like that?

The reason I've prefixed each of these files with a number is to control
the order in which Dash includes them, per
https://dash.plotly.com/external-resources#how-dash-loads-assets. Mainly,
we want to include Cytoscape.js before its extensions.

That being said, it looks like this only matters for Cytoscape-SVG -- the
layout extensions (Dagre and fCOSE) appear to still work fine, even if
you purposefully make force them to be included before Cytoscape.js.
Anyway, to be safe, let's ensure that all of these extensions are included
after Cytoscape.js...
