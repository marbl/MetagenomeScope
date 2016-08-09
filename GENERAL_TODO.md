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

* File more issue reports with Cytoscape.js. Remaining errors:
    * unbundled-bezier causing the need for control-point-distances attributes
      for every element in the graph
        * I need to actually work on getting this in a Minimal Working
          Example; for all I know this could just be some elaborate bug I
          accidentally introduced with data(cpd).
    * Documentation might be wrong re: the edge weights supported by
      Floyd-Warshall and Bellman-Ford algorithms (it should say "numeric,"
      instead of "positive numeric" -- would need to verify this and then
      submit a small pull request, I guess).
    * Documentation is likely wrong re: using `eles.classes()` to clear an
      element's style classes; I think it's actually `eles.classes("")`,
      since when I tried the former Cytoscape.js gave me an error and when
      I tried the latter it worked fine. I guess verify that this is the
      case and then file a pull request if so?

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
