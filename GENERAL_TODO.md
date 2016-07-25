# General Things TODO related to the project

* Test using desktop Cytoscape to load Cytoscape.js-exported JSON data.
  That'll have limited functionality.

* Start thinking of scaling factors -- e.g. "up to this many thousands of
  nodes in the browser, or this many millions of nodes in the desktop
  Cytoscape version."

* CUDA angle? Using that to speed up GraphViz/Cytoscape.js/etc.

* Show interesting biological information extracted from a graph.

* Use collator to, optionally, generate a HTML page that automatically loads
  the generated neo4j database. As opposed to using a monolithic database
  viewer.

* Tutorial!!! (Add to repository)

* Talk to Jayram (shares Todd's office) re: neo4j issues (browser
  limitations, etc).
    * py2neo to generate a database, and then read the resulting database
      via javascript
    * load xdot in the browser--support both.
    * loading xdot in the browser would lose out on some of the extra data
      stored in the neo4j database--present user with requisite disclaimers.

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

* Look into using neo4j to store assembly graph data? That would allow
  communication between the Python script and the xdot parser, I guess.
  And we could have the user just select a neo4j graph database instead of
  an xdot file (or we could have both options, but with more functionality
  for the database option since there's more data available there)
    * We could even generate (from the python script) a folder containing
    a html page and the pertinent neo4j database, in which that html page
    auto-loads the neo4j database in that directory. Presumably that
    database would contain all the nodes/edges in the graph, and be able
    to load different components sequentially.

* Create a sort of graph/sequence simulator, where the user could say "give
  me a graph with a frayed rope, a bubble with 3 divergent paths, and two
  cycles" or somehting like that and a conforming graph (and an underlying
  DNA sequence) would be generated.
