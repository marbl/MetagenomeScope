# General Things TODO related to the project

* Test using desktop Cytoscape to load Cytoscape.js-exported JSON data.
  That'll have limited functionality.
    * Okay, so it looks like trying to use JSON.stringify() on cy.json()
      results in a "cyclic data structure" error. Not really sure how to
      export JSON instead.
    * *Maybe* run xdot2cy.js headlessly using node.js and from there
      export the JSON? That'd have a few advantages, one prominent one being
      that the user wouldn't have to open up the graph in the browser to get
      the pertinent JSON.
        * Alternatively, we could just skip Cytoscape.js in this step and
          figure out how to convert the data we have in the .db file to a JSON
          object/something else that could be loaded into desktop Cytoscape.
(There is a plugin for Cytoscape that loads .dot and .gv files---looked into it
for a bit, seemed alright but not sure how useful it could be.)

* File more issue reports with Cytoscape.js. Remaining errors:
    * unbundled-bezier causing the need for control-point-distances attributes
      for every element in the graph
        * I need to actually work on getting this in a Minimal Working
          Example; for all I know this could just be some elaborate bug I
          accidentally introduced with data(cpd).

* Start thinking of scaling factors -- e.g. "up to this many thousands of
  nodes in the browser, or this many millions of nodes in the desktop
  Cytoscape version."
    * The planned node.js thing (see #12) should rectify most of our
      concerns re: this.

* CUDA angle? Using that to speed up GraphViz/Cytoscape.js/etc.

* Show interesting biological information extracted from a graph.

* Tutorial!!! (Add to repository)

* Spend some time creating a 2-ish page Google Doc with a brief
  introduction, a description of the results obtained (i.e. what the
  application is like), and a figure (a really cool graph or something).
  And probably some more pertinent things. Todd mentioned this general
  format is often used for *Oxford Bioinformatics*, so it's worth working on.
    * We'll probably want to cite, among other things:
        * *Cytoscape.js: a graph theory library for visualization and
          analysis* (Franz et al. 2016)
        * *Assembly Algorithms for Next-Generation Sequencing Data* (Miller,
          Koren, Sutton 2010)
            * Defines the bubble/frayed rope/cycle patterns. Our concept of
            "chains" is based off their description of "spurs," as well.
        * *Bandage: interactive visualization of de novo genome assemblies*
          (Wick, Schultz, Zobel, Holt 2015)

* Create a sort of graph/sequence simulator, where the user could say "give
  me a graph with a frayed rope, a bubble with 3 divergent paths, and two
  cycles" or somehting like that and a conforming graph (and an underlying
  DNA sequence) would be generated.
