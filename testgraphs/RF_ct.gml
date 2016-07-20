// Tests the chain -> rope bug found in an earlier version of
// collate_clusters.py. If the output from this file is a rope and an
// incorrect chain, with C1410_14645, then the program is wrong; if the
// output is only either a rope or a chain (which is expressed depends on
// ordering, I think) and not both, then the program is correct.
  node [
   id 533
   label "contig-100_11072"
   orientation "FOW"
  ]
  node [
   id 1410
   label "contig-100_1287"
   orientation "FOW"
  ]
  node [
   id 1703
   label "contig-100_13579"
   orientation "FOW"
  ]
  node [
   id 8792
   label "contig-100_28154"
   orientation "FOW"
  ]
  node [
   id 14645
   label "contig-100_39455"
   orientation "FOW"
  ]
  node [
   id 16598
   label "contig-100_43786"
   orientation "FOW"
  ]
  edge [
   source 533
   target 1703
   orientation EB
   mean "-291.916"
   stdev 49.8991
  ]
  edge [
   source 1410
   target 14645
   orientation EB
   mean "-165.666"
   stdev 99.7982
  ]
  edge [
   source 1703
   target 8792
   orientation EB
   mean "-279.066"
   stdev 44.6311
  ]
  edge [
   source 1703
   target 16598
   orientation EB
   mean "-225.399"
   stdev 25.7678
  ]
  edge [
   source 14645
   target 1703
   orientation EB
   mean "-287.11"
   stdev 33.2661
  ]
