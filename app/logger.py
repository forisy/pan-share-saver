"""
Unified logging module for PanShareSaver application.

Supports module prefixes in log messages like `[aliyun] click 保存到此处`
for better debugging and monitoring of different components.
"""
import logging
import sys
from typing import Optional
from datetime import datetime

# Global logger registry to avoid creating duplicate loggers for the same module
_logger_registry = {}

def get_logger(module_name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Get or create a logger instance with the specified module name.

    Args:
        module_name: Name of the module (e.g., 'baidu', 'aliyun', 'scheduler')
        level: Optional logging level (defaults to INFO)

    Returns:
        A configured logger instance with the specified module name
    """
    # Create a unique name for the logger to avoid conflicts
    logger_name = f"PanShareSaver.{module_name}"

    # Return cached logger if it already exists
    if logger_name in _logger_registry:
        return _logger_registry[logger_name]

    # Create new logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(level or logging.INFO)

    # Prevent duplicate handlers by checking if our specific formatter exists
    has_our_handler = False
    for handler in logger.handlers:
        # Check if this is our custom handler by looking at the formatter
        if (hasattr(handler, 'formatter') and 
            handler.formatter and 
            '%(name)s - %(levelname)s - %(message)s' in str(handler.formatter._fmt)):
            has_our_handler = True
            break
    
    # Only add handler if we don't have our custom one already
    if not has_our_handler:
        # Remove any existing handlers to avoid duplicates
        logger.handlers.clear()
        
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Add to registry for future use
    _logger_registry[logger_name] = logger
    return logger

class ModuleLogger:
    """
    A wrapper around the standard logging module that provides the ability
    to add module prefixes to log messages automatically.
    """

    def __init__(self, module_name: str, level: Optional[int] = None):
        """
        Initialize the ModuleLogger with a specific module name.

        Args:
            module_name: Name of the module (e.g., 'baidu', 'aliyun')
            level: Optional logging level (defaults to INFO)
        """
        self.module_name = module_name
        self.logger = get_logger(module_name, level)
        self.prefix = f"[{module_name}]"

    def _log_with_prefix(self, level: int, message: str, *args, **kwargs):
        """
        Internal method to log a message with the module prefix.

        Args:
            level: Logging level (e.g., logging.INFO, logging.ERROR)
            message: The message to log
            *args: Additional arguments for formatting
            **kwargs: Additional keyword arguments
        """
        formatted_message = f"{self.prefix} {message}"
        self.logger.log(level, formatted_message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs):
        """
        Log a debug message with module prefix.

        Args:
            message: The message to log
            *args: Additional arguments for formatting
            **kwargs: Additional keyword arguments
        """
        self._log_with_prefix(logging.DEBUG, message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        """
        Log an info message with module prefix.

        Args:
            message: The message to log
            *args: Additional arguments for formatting
            **kwargs: Additional keyword arguments
        """
        self._log_with_prefix(logging.INFO, message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """
        Log a warning message with module prefix.

        Args:
            message: The message to log
            *args: Additional arguments for formatting
            **kwargs: Additional keyword arguments
        """
        self._log_with_prefix(logging.WARNING, message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """
        Log an error message with module prefix.

        Args:
            message: The message to log
            *args: Additional arguments for formatting
            **kwargs: Additional keyword arguments
        """
        self._log_with_prefix(logging.ERROR, message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        """
        Log a critical message with module prefix.

        Args:
            message: The message to log
            *args: Additional arguments for formatting
            **kwargs: Additional keyword arguments
        """
        self._log_with_prefix(logging.CRITICAL, message, *args, **kwargs)

# Convenience functions that create module loggers on demand
def create_logger(module_name: str, level: Optional[int] = None) -> ModuleLogger:
    """
    Create a ModuleLogger instance for the specified module name.

    Args:
        module_name: Name of the module (e.g., 'baidu', 'aliyun')
        level: Optional logging level (defaults to INFO)

    Returns:
        A ModuleLogger instance with the specified module name
    """
    return ModuleLogger(module_name, level)

def log_debug(module_name: str, message: str, *args, **kwargs):
    """
    Log a debug message with the specified module prefix.

    Args:
        module_name: Name of the module (e.g., 'baidu', 'aliyun')
        message: The message to log
        *args: Additional arguments for formatting
        **kwargs: Additional keyword arguments
    """
    logger = create_logger(module_name)
    logger.debug(message, *args, **kwargs)

def log_info(module_name: str, message: str, *args, **kwargs):
    """
    Log an info message with the specified module prefix.

    Args:
        module_name: Name of the module (e.g., 'baidu', 'aliyun')
        message: The message to log
        *args: Additional arguments for formatting
        **kwargs: Additional keyword arguments
    """
    logger = create_logger(module_name)
    logger.info(message, *args, **kwargs)

def log_warning(module_name: str, message: str, *args, **kwargs):
    """
    Log a warning message with the specified module prefix.

    Args:
        module_name: Name of the module (e.g., 'baidu', 'aliyun')
        message: The message to log
        *args: Additional arguments for formatting
        **kwargs: Additional keyword arguments
    """
    logger = create_logger(module_name)
    logger.warning(message, *args, **kwargs)

def log_error(module_name: str, message: str, *args, **kwargs):
    """
    Log an error message with the specified module prefix.

    Args:
        module_name: Name of the module (e.g., 'baidu', 'aliyun')
        message: The message to log
        *args: Additional arguments for formatting
        **kwargs: Additional keyword arguments
    """
    logger = create_logger(module_name)
    logger.error(message, *args, **kwargs)

def log_critical(module_name: str, message: str, *args, **kwargs):
    """
    Log a critical message with the specified module prefix.

    Args:
        module_name: Name of the module (e.g., 'baidu', 'aliyun')
        message: The message to log
        *args: Additional arguments for formatting
        **kwargs: Additional keyword arguments
    """
    logger = create_logger(module_name)
    logger.critical(message, *args, **kwargs)

# Backward compatibility function that mimics print behavior for existing logs
def print_with_module(module_name: str, message: str):
    """
    Print a message with module prefix for backward compatibility.
    This can be used to replace existing print statements easily.

    Args:
        module_name: Name of the module (e.g., 'baidu', 'aliyun')
        message: The message to log
    """
    log_info(module_name, message)