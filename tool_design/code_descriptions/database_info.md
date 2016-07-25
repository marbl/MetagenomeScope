So, I'd imagine that (regardless of what database we end up using) --

* As we **traverse** the assembly data file, we record not only connection
  data/contig length but also biological data/metadata for nodes and edges --
  e.g. contig DNA forward/reverse strings if applicable, and edge
  multiplicity. These could be easily stored as attributes of the Node class
  I have set up in `node_objectsc.py`, but we should also store them in a
  database accessible from Python.
* We use `collate_clusters.py` to generate a .gv (DOT) file representing the
  contigs and their relationships to each other. Same as before.
* We call `dot` on the .gv file to generate .xdot files describing the
  layout of the graph for each connected component. Same as before.
* We **parse** each .xdot file generated for each connected component *within*
  `collate_clusters.py`, using basically the
  same techniques we used in `xdot2cy.js` but for each component's xdot file.
  (We could even just read the xdot files directly into memory without
  outputting them to a file, maybe??? Not sure how much support for piping
  GraphViz has.)
  As we record the generated layout
  data of nodes (and control point data of edges), we store this information
  in the database. Let's say we also store a thing pointing to where each
  connected component is (i.e. its member nodes, and how many components
  exist, and what their sizes are, etc.).
* When we're finished, we're just left with that database describing the
  entire graph: biological data/metadata, connections, and layout information.
  That's it.

This is how the Python side of things will work.

On the JS side of things:

* When the user loads a file, we check if it's .xdot or .db.
  * If .xdot, proceed
  as before (just keeping this in there for future reference; if we decide to
  ditch .xdot file support, then we ditch them [the .xdot viewer will still be
  available in the history of xdot2cy.js!]).
  * If .db, then load the graph using the layout info but also record the bio
    data:
  * Since the .db has info about all connected components, we can implement
    something that'll display all component names or sizes/something, and
    give the user option to
    choose which one to render before rendering anything. Furthermore, in
    this "loaded but not rendered" state, the user should have the option
    to run cy.json() -- which will generate an exportable JSON file that
    the user can open in desktop Cytoscape. Maybe we can, I dunno, generate
    a separate JSON file for each component???
  * Perhaps we could implement search here, also? e.g. user wants to see
    component containing node 123, so we search the database for 123's
    component
  * This part is really up to how sql.js works, honestly.
