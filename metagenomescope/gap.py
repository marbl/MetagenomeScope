class Gap(object):
    def __init__(self, length=None, length_units="bp", gaptype=None):
        self.length = length
        self.length_units = length_units
        self.gaptype = gaptype

    def _get_fmt_str_parts(self):
        # avoiding importing ui_utils.fmt_qty() here to avoid circular import
        # nonsense...
        if self.length is not None:
            length = f"{self.length:,} {self.length_units}"
        else:
            length = "unknown length"
        if self.gaptype is not None:
            gt = f'"{self.gaptype}", '
        else:
            gt = ""
        return gt, length

    def __repr__(self):
        gt, length = self._get_fmt_str_parts()
        return f"Gap({gt}{length})"

    def __str__(self):
        # maybe i will add more distinction in the future...
        gt, length = self._get_fmt_str_parts()
        return f"Gap ({gt}{length})"

    def __eq__(self, other):
        # this is just here for testing
        #
        # NOTE: this makes Gaps not hashable, per
        # https://www.pythonmorsels.com/making-hashable-objects/ -- but they
        # should never be used in that way anyway.
        return (
            self.length == other.length
            and self.length_units == other.length_units
            and self.gaptype == other.gaptype
        )
