#!/usr/bin/env python3

"""Contains constants."""

import pathlib
from os import path

LOGGER_NAME = "LOGGING"

DEFAULT_LOG_DIR_PATH = path.join(pathlib.Path(__file__).parent.parent.resolve(), "logs")
DEFAULT_LOG_FILE_NAME = "logging.log"
DEFAULT_LOGGER_FILE_HANDLER_NAME = f"{LOGGER_NAME}_FILE_HANDLER_NAME"
