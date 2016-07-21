# Converts a string of points (e.g. "x1 y1 x2 y2 ... xn yn") separated by spaces
# to a printed sequence of tuples. Used for debugging control points.
# (...where "debugging" means "feed it into Wolfram Alpha to see if it looks
# right")
def conv(pts):
	c = 0
	a = pts.strip().split()
	for i in a:
		if c % 2 == 0:
			print "(%g, %g)," % (float(a[c]), float(a[c + 1]))
		c += 1
