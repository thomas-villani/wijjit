"""
Logging configuration for the Wijjit framework.

This module provides centralized logging configuration for Wijjit applications.
Since Wijjit apps are terminal-based, logging to stderr can interfere with the UI.
This module configures logging to files instead.

Environment Variables
---------------------
WIJJIT_LOG_FILE : str
    Path to log file. If not set, logging is disabled.
WIJJIT_LOG_LEVEL : str
    Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default is INFO.

Examples
--------
Configure logging to a file with DEBUG level:

    >>> from wijjit.logging_config import configure_logging
    >>> configure_logging('wijjit.log', level='DEBUG')

Configure logging with INFO level (default):

    >>> configure_logging('app.log')

Disable logging:

    >>> configure_logging(None)

Configure via environment variables:

    $ export WIJJIT_LOG_FILE=debug.log
    $ export WIJJIT_LOG_LEVEL=DEBUG
    $ python app.py
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Union


def configure_logging(
    filename: Optional[Union[str, Path]] = None,
    level: Union[str, int] = logging.INFO,
    format_string: Optional[str] = None,
) -> None:
    """
    Configure logging for Wijjit applications.

    This function sets up the logging infrastructure for all Wijjit modules.
    Logging is directed to a file to avoid interfering with terminal UI rendering.

    Parameters
    ----------
    filename : str, Path, or None, optional
        Path to the log file. If None, logging is disabled. Default is None.
    level : str or int, optional
        Logging level. Can be a string ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        or a logging constant (logging.DEBUG, etc.). Default is logging.INFO.
    format_string : str, optional
        Custom log format string. If None, uses default format with timestamp,
        logger name, level, and message. Default is None.

    Returns
    -------
    None

    Examples
    --------
    Enable DEBUG logging to a file:

        >>> configure_logging('debug.log', level='DEBUG')

    Use custom format:

        >>> configure_logging('app.log', format_string='%(asctime)s - %(message)s')

    Disable logging:

        >>> configure_logging(None)
    """
    # Get the root wijjit logger
    logger = logging.getLogger('wijjit')

    # Remove all existing handlers
    logger.handlers.clear()

    # If filename is None, disable logging
    if filename is None:
        logger.addHandler(logging.NullHandler())
        logger.setLevel(logging.CRITICAL + 1)  # Effectively disable
        return

    # Convert string level to logging constant if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper())

    # Set logger level
    logger.setLevel(level)

    # Create file handler
    file_handler = logging.FileHandler(filename, mode='a', encoding='utf-8')
    file_handler.setLevel(level)

    # Create formatter
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    formatter = logging.Formatter(format_string, datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(file_handler)

    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False

    # Log that logging has been configured
    logger.info(
        f"Logging configured: file={filename}, level={logging.getLevelName(level)}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific Wijjit module.

    This function returns a logger that is a child of the 'wijjit' logger,
    ensuring it uses the configured file handler.

    Parameters
    ----------
    name : str
        Name of the module, typically __name__. Should start with 'wijjit.'.

    Returns
    -------
    logging.Logger
        Logger instance for the specified module.

    Examples
    --------
    Get a logger in a Wijjit module:

        >>> logger = get_logger(__name__)
        >>> logger.debug("Debug message")
    """
    # Ensure the logger is under the wijjit namespace
    if not name.startswith('wijjit'):
        name = f'wijjit.{name}'

    return logging.getLogger(name)


def configure_from_environment() -> None:
    """
    Configure logging from environment variables.

    This function checks for WIJJIT_LOG_FILE and WIJJIT_LOG_LEVEL environment
    variables and configures logging accordingly. If WIJJIT_LOG_FILE is not set,
    logging is disabled.

    Environment Variables
    ---------------------
    WIJJIT_LOG_FILE : str
        Path to log file. If not set, logging is disabled.
    WIJJIT_LOG_LEVEL : str
        Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default is INFO.

    Returns
    -------
    None

    Examples
    --------
    This function is called automatically when the module is imported:

        >>> import wijjit.logging_config  # Automatically configures from env vars
    """
    log_file = os.environ.get('WIJJIT_LOG_FILE')
    log_level = os.environ.get('WIJJIT_LOG_LEVEL', 'INFO')

    if log_file:
        configure_logging(log_file, level=log_level)
    else:
        configure_logging(None)


# Configure logging from environment variables on module import
configure_from_environment()
