// Tests the weird chain thing seen with nodes 8367, 18265, and 20284 in
// the RF_oriented dataset.
// That is, a chain of 2 nodes in which one of the exterior nodes is
// connected to a node which has a single edge back to the exterior node.
// So, something like 1 -> 2, 2 -> 3, 3 -> 2.
// We still want to recognize [1,2] as a chain, but we want to disqualify 3
// from being in it.
graph [
  directed 1
  node [
   id 8367
   label "contig-100_27312"
   orientation "FOW"
  ]
  node [
   id 18265
   label "contig-100_4616"
   orientation "FOW"
  ]
  node [
   id 20284
   label "contig-100_7232"
   orientation "FOW"
  ]
  edge [
   source 8367
   target 18265
   orientation EB
   mean "-3091.34"
   stdev 57.6185
  ]
  edge [
   source 18265
   target 8367
   orientation EB
   mean "-2230.67"
   stdev 99.7982
  ]
  edge [
   source 18265
   target 20284
   orientation EB
   mean "-2547.67"
   stdev 70.568
  ]
