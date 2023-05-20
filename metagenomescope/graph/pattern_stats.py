class PatternStats(object):
    """Statistics about how many of each type of pattern are present somewhere.

    This is probably overkill.
    """

    def __init__(
        self,
        num_bubbles=0,
        num_chains=0,
        num_cyclicchains=0,
        num_frayedropes=0,
    ):
        self.num_bubbles = num_bubbles
        self.num_chains = num_chains
        self.num_cyclicchains = num_cyclicchains
        self.num_frayedropes = num_frayedropes

    def __add__(self, other_pattern_stats):
        return PatternStats(
            self.num_bubbles + other_pattern_stats.num_bubbles,
            self.num_chains + other_pattern_stats.num_chains,
            self.num_cyclicchains + other_pattern_stats.num_cyclicchains,
            self.num_frayedropes + other_pattern_stats.num_frayedropes,
        )

    def __repr__(self):
        return (
            f"PatternStats({self.num_bubbles:,} bubble(s), "
            f"{self.num_chains:,} chain(s), "
            f"{self.num_cyclicchains:,} cyclic chain(s), "
            f"{self.num_frayedropes:,} frayed rope(s))"
        )
