import os


def create_output_dir(output_dir):
    # NOTE this is ostensibly vulnerable to a race condition in which this
    # directory is removed after it's either created or shown to already exist
    # as a directory. In this case, though, the user would just get an error
    # when the script tries to write the first output file -- shouldn't cause
    # any side effects.
    os.makedirs(output_dir)
