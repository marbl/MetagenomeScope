import os


def create_output_dir(output_dir):
    # NOTE this is ostensibly vulnerable to a race condition in which this
    # directory is removed after it's either created or shown to already exist
    # as a directory. In this case, though, the user would just get an error
    # when the script tries to write the first output file -- shouldn't cause
    # any side effects.
    os.makedirs(output_dir)


def check_dir_existence(output_dir):
    """Raises an error if a directory exists.

    This is, of course, vulnerable to race conditions -- we could check
    that output_dir does not exist, and then it could be created later on!
    However, for the vast majority of expected use cases, that won't happen.
    Plus we should be able to handle that case later if it _would_ happen.
    It makes sense to check this up front to avoid having the user waste like
    hours of time waiting for the script to finish only to realize that this
    directory already exists.
    """
    if os.path.exists(output_dir):
        # (FileExistsError is documented as "Raised when trying to create a
        # file or directory which already exists"
        # --https://docs.python.org/3/library/exceptions.html -- so even though
        # it would sound nicer if it was called DirectoryExistsError I'm
        # following convention apparently)
        raise FileExistsError(
            "Output directory {} already exists.".format(output_dir)
        )


def validate_max_counts(max_node_ct, max_edge_ct):
    nodebad = max_node_ct < 1
    edgebad = max_edge_ct < 1
    if nodebad and edgebad:
        raise ValueError(
            "Maximum node / maximum edge counts must be at least 1"
        )
    if nodebad:
        raise ValueError("Maximum node count must be at least 1")
    if edgebad:
        raise ValueError("Maximum edge count must be at least 1")
