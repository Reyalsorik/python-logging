#!/usr/bin/env python3

"""Contains configuration logic used for logging."""

import copy
import logging
import sys
from enum import Enum
from os import makedirs, path
from typing import Any, MutableMapping, Tuple

from colors import CText
from custom_logging.lib.constants import DEFAULT_LOG_FILE_NAME, DEFAULT_LOGGER_FILE_HANDLER_NAME, LOGGER_NAME


class LogFormatter(logging.Formatter):
    """Custom formatter responsible for adding color and keyword arguments from a filter."""

    colored_levels = dict(
        ERROR="magenta",
        CRITICAL="red",
        WARNING="yellow",
        INFO="green",
        DEBUG="white"
    )

    def __init__(self, fmt: str, disable_color: bool = False) -> None:
        """Initialize.

        :param fmt: message format
        :param disable_color: whether to disable color
        """
        super().__init__(fmt)
        self.disable_color = disable_color

    def format(self, _record) -> str:
        """Add color and format the record.

        :param _record: record to format
        """
        original_fmt = self._style._fmt  # Cache the original fmt
        record = copy.copy(_record)  # Corresponding logger may have children, do not alter
        record.args = record.args or dict()
        override_color = record.args.get("color")
        if not self.disable_color:
            if override_color:
                self._style._fmt = getattr(CText, override_color if hasattr(CText, override_color) else "default")("%(msg)s")
            record.levelname = getattr(CText, self.colored_levels.get(record.levelname, "default"))(f"{record.levelname:>8}")  # Color the level name
        record.levelname = f"{record.levelname:>8}"  # Format the level name
        record.msg = f"{record.name}: {record.msg}" if record.__dict__.get("name") else record.msg  # Keyword set from a filter
        result = super().format(record)
        self._style._fmt = original_fmt  # Restore the original fmt
        return result


class CustomLogAdapter(logging.LoggerAdapter):
    """Custom adapter for allowing additional attributes."""

    def __init__(self, _logger: logging.Logger, name: str) -> None:
        """Initialize.

        :param _logger: logger object
        :param name: unique name
        """
        custom_filter = dict(name=name)
        super().__init__(_logger, custom_filter)
        self.logger.addFilter(CustomFilter(custom_filter))

    def _add_custom_attributes(self, kwargs: MutableMapping[str, Any]) -> None:
        """Add custom attributes to the logger; allows the record attributes to be accessible.

        :param kwargs: additional kwargs
        """
        self.logger.addFilter(CustomFilter(kwargs or dict()))

    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> Tuple[Any, MutableMapping[str, Any]]:
        """Process the message and add custom attributes.

        :param msg: message to process
        :param kwargs: additional kwargs
        """
        self._add_custom_attributes(kwargs)
        return msg, dict()


class CustomFilter(logging.Filter):
    """Custom filter for adding additional attributes to the logger."""

    def __init__(self, custom_filter: MutableMapping[str, Any]) -> None:
        """Initialize.

        :param custom_filter: attributes to add to the logger
        """
        super().__init__()
        self.custom_filter = custom_filter

    def filter(self, record: logging.LogRecord) -> bool:
        """Add additional attributes to a record.

        :param record: record to filter
        """
        for attribute, value in self.custom_filter.items():
            setattr(record, attribute, record.args.get(attribute) if record.args else value)
        return True


def _get_custom_adapter(name: str) -> logging.LoggerAdapter:
    """Get the custom adapter with extended keyword functionality.

    :param name: unique name
    """
    return CustomLogAdapter(logging.getLogger(name.upper()), name=name)  # Extend original logger


def _get_configured_stdout_handler(level: str, disable_color: bool) -> logging.StreamHandler:
    """Configure a handler for displaying stdout.

    :param level: handler logging level
    :param disable_color: whether to disable color
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level))  # Set to the verbosity level
    handler.setFormatter(LogFormatter("%(levelname)s %(message)s", disable_color=disable_color))
    return handler


def _get_configured_file_handler(filename: str, skip_logging: bool, file_handler_name: str = DEFAULT_LOGGER_FILE_HANDLER_NAME) -> logging.Handler:
    """Configure a handler for writing to a file.

    :param filename: file that will be used for writing log output
    :param skip_logging: suppress logged messages
    :param file_handler_name: file handler name
    """
    handler = logging.NullHandler() if skip_logging else logging.FileHandler(filename=filename, delay=True)
    handler.name = file_handler_name
    handler.setLevel(logging.DEBUG)  # Default to debug
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    return handler


def _get_log_file(log_path: str = None, file: str = DEFAULT_LOG_FILE_NAME) -> str:
    """Get the log file.

    :param log_path: file path that will be used for writing log output
    :param file: file name
    """
    return path.join(log_path, file)


def get_log_file_from_handler(logger_name: str, file_handler_name: str = DEFAULT_LOGGER_FILE_HANDLER_NAME) -> str:
    """Get the log file from the handler.

    :param logger_name: logger name
    :param file_handler_name: file handler name
    """
    file_handler = list(
        filter(
            lambda handler: isinstance(handler, logging.FileHandler) and handler.name == file_handler_name,
            logging.getLogger(logger_name).handlers
        )
    )[0]
    return file_handler.__dict__.get("baseFilename", str())


def configure_logging(verbose: int = 0, disable_color: bool = False, skip_logging: bool = False, log_path: str = "logs", logger_name: str = LOGGER_NAME) -> None:
    """Configure logging.

    :param verbose: level of verbosity
    :param disable_color: whether to disable color
    :param skip_logging: skip logging messages
    :param log_path: directory path that will be used for writing log output
    :param logger_name: logger name
    """
    class VerbosityLevels(Enum):
        WARNING = 0
        INFO = 1
        DEBUG = 2

    logger = logging.getLogger(logger_name)
    makedirs(log_path, exist_ok=True)  # Ensure the log path exists
    level = VerbosityLevels(min(verbose, len(VerbosityLevels.__members__) - 1)).name
    logger.setLevel(logging.DEBUG)  # Default to debug
    logger.addHandler(_get_configured_stdout_handler(level, disable_color))  # Add a handler for stdout verbosity
    logger.addHandler(_get_configured_file_handler(_get_log_file(log_path=log_path), skip_logging))  # Add a handler for writing to a file
    logger.log(logger.level, f"Verbosity level: {logger_name} = {logging.getLevelName(logger.level)}")  # Log verbosity level


def get_custom_logger(verbose: int = 0, disable_color: bool = False, skip_logging: bool = False, name: str = "DEFAULT") -> logging.LoggerAdapter:
    """Get a custom configured logger.

    :param verbose: level of verbosity
    :param disable_color: whether to disable color
    :param skip_logging: skip logging messages
    :param name: unique name
    """
    logger = _get_custom_adapter(
        name=name
    )
    configure_logging(
        verbose=verbose,
        disable_color=disable_color,
        skip_logging=skip_logging,
        logger_name=logger.logger.name
    )
    logger.debug("Logger configured.", name=name.upper())
    return logger
