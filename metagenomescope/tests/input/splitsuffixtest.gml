graph [
  directed 1
  node [
   id 1 
   label "contig-100_1"
   orientation "FOW"
   length "100"
  ]
  node [
   id 2
   label "contig-100_2"
   orientation "FOW"
   length "100"
  ]
  node [
   id 3
   label "contig-100_3-L"
   orientation "FOW"
   length "100"
  ]
  node [
   id 4
   label "contig-100_4"
   orientation "FOW"
   length "100"
  ]
  edge [
   source 1
   target 2
   orientation "EB"
   mean "-100"
   stdev 50
   bsize 5
  ]
  edge [
   source 1
   target 3
   orientation "EB"
   mean "-100"
   stdev 50
   bsize 5
  ]
  edge [
   source 2
   target 4
   orientation "EB"
   mean "-100"
   stdev 50
   bsize 5
  ]
  edge [
   source 3
   target 4
   orientation "EB"
   mean "-100"
   stdev 50
   bsize 5
  ]
]
