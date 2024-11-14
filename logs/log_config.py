"""
This module sets up the logging configuration for the bot. It ensures that logs are
stored in a specified logs directory and are formatted for readability. The logs are
saved both to a file and output to the console for easy monitoring.

The log configuration includes:
- Custom formatting for different log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Log storage in the 'logs' directory
- Both console and file handlers for comprehensive logging
"""

import logging
import logging.config
import os  # Import os for directory and path management

class CustomFormatter(logging.Formatter):
    """Custom Formatter without emojis to ensure compatibility across various systems."""

    reset = "\x1b[0m"
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Define color codes for different log levels for console output
    FORMATS = {
        logging.DEBUG: "\x1b[34m" + fmt + reset,  # Blue for DEBUG
        logging.INFO: "\x1b[32m" + fmt + reset,  # Green for INFO
        logging.WARNING: "\x1b[33m" + fmt + reset,  # Yellow for WARNING
        logging.ERROR: "\x1b[31m" + fmt + reset,  # Red for ERROR
        logging.CRITICAL: "\x1b[41m" + fmt + reset,  # Red background for CRITICAL
    }

    def format(self, record):
        """Override the format method to apply custom formatting."""
        log_fmt = self.FORMATS.get(record.levelno, self.fmt)  # Get the format for the log level
        formatter = logging.Formatter(log_fmt)  # Apply the format
        return formatter.format(record)

# Ensure the logs directory exists
log_dir = "logs"  # Directory where logs will be stored
if not os.path.exists(log_dir):
    os.makedirs(log_dir)  # Create the directory if it does not exist

# Define the logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,  # Do not disable existing loggers
    'formatters': {
        'standard': {
            '()': CustomFormatter,  # Use the custom formatter
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',  # Log DEBUG and higher levels to the console
            'class': 'logging.StreamHandler',  # Output logs to the console
            'formatter': 'standard',  # Use the standard formatter
        },
        'file': {
            'level': 'DEBUG',  # Log DEBUG and higher levels to the file
            'class': 'logging.FileHandler',  # Save logs to a file
            'filename': os.path.join(log_dir, 'app.log'),  # Log file path in the logs directory
            'formatter': 'standard',  # Use the standard formatter
            'encoding': 'utf-8'  # Use UTF-8 encoding for the log file
        },
    },
    'loggers': {
        '': {  # Root logger configuration
            'handlers': ['console', 'file'],  # Use both console and file handlers
            'level': 'DEBUG',  # Log DEBUG and higher levels
            'propagate': True,  # Allow logs to propagate to other loggers
        },
        'discord': {  # Discord-specific logger configuration
            'handlers': ['console', 'file'],  # Use both console and file handlers
            'level': 'WARNING',  # Log WARNING and higher levels for the discord logger
            'propagate': False,  # Do not propagate to other loggers
        },
    }
}

def setup_logging():
    """Apply the logging configuration."""
    logging.config.dictConfig(LOGGING_CONFIG)
