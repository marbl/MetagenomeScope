import logging
from . import __version__, config, ui_utils
from .errors import WeirdError


def log_lines_with_sep(lines, sepchar=config.SEPSML, endsepline=False):
    # Accounts for the "{HH:MM:SS.mmm} " prefix before each logging message.
    # Note that this is brittle; it will break if the call to
    # logging.basicConfig() in start_log() is changed.
    seplen = len(lines[0]) + 15
    sepline = sepchar * seplen
    out = f"{lines[0]}\n{sepline}"
    if len(lines) > 1:
        # in older python versions, backslashes (like that in "\n") inside
        # f-string {}s are not supported; this prevents that
        linelist = "\n".join(lines[1:])
        out += f"\n{linelist}"
    if endsepline:
        out += f"\n{sepline}"
    logger = logging.getLogger(__name__)
    # NOTE: defaults to using info-level logging because all the places that
    # use this function need that lol. Can make configurable if needed
    logger.info(out)


def start_log(verbose: bool):
    # in any case, stop logging every time a request or something happens:
    # https://community.plotly.com/t/logging-debug-messages-suppressed-in-callbacks/17854/4
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    if verbose:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO
    # use datefmt for pretty timestamps: https://stackoverflow.com/a/14226251
    # msecs corresponds to milliseconds, which should be in the range [000, 999]:
    # https://docs.python.org/3/library/logging.html#logrecord-attributes
    logging.basicConfig(
        level=logging_level,
        style="{",
        format="{{{asctime}.{msecs:03.0f}}} {message}",
        datefmt="%H:%M:%S",
    )
    # Log the version, just for reference -- based on this blog post:
    # http://lh3.github.io/2022/09/28/additional-recommendations-for-creating-command-line-interfaces
    log_lines_with_sep(
        [f"Running MetagenomeScope (version {__version__})..."],
        config.SEPBIG,
    )


def log_layout_start(done_flushing, ag):
    draw_settings = done_flushing["draw_settings"]
    ptext = ""
    for pk, pv in done_flushing["layout_params"].items():
        ptext += f"{pk} = {pv}"
    if len(ptext) > 0 and len(draw_settings) > 0:
        ptext = "; " + ptext

    thing = ui_utils.get_curr_drawn_text(done_flushing, ag)

    logging.debug(
        f"  Laying out {thing} with {done_flushing['layout_alg']} "
        f"({'; '.join(draw_settings)}{ptext})..."
    )
