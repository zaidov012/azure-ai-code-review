"""Logging utilities for the extension."""

import logging
import sys
import colorlog


def setup_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """
    Set up a colorized logger for better console output.

    Args:
        name: Logger name (usually __name__)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, log_level.upper()))

    # Create console handler with color formatting
    handler = colorlog.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level.upper()))

    # Color formatter
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s: %(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        secondary_log_colors={},
        style="%",
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
