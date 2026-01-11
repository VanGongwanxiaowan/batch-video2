"""Enhanced logging configuration for BatchShort.

This module provides a flexible and feature-rich logging configuration that supports:
- Multiple log levels and output formats
- File rotation and compression
- JSON formatting for structured logging
- Request ID tracking
- Contextual logging
"""
import json
import logging
import logging.handlers
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pytz
from pythonjsonlogger import jsonlogger

from .config.settings import settings
from .paths import PathManager, get_path_manager


class RequestIdFilter(logging.Filter):
    """Add request_id to log records if available in the context."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, 'request_id'):
            record.request_id = getattr(record, 'request_id', 'system')
        return True


class ContextualLogger(logging.Logger):
    """Logger that supports contextual logging with additional fields."""
    
    def makeRecord(self, name: str, level: int, fn: str, lno: int, msg: str, 
                  args: Any, exc_info: Any, func: Optional[str] = None, 
                  extra: Optional[Dict[str, Any]] = None, 
                  sinfo: Optional[str] = None) -> logging.LogRecord:
        """Create a log record with additional context."""
        if extra is None:
            extra = {}
            
        # Add request ID if not provided
        if 'request_id' not in extra:
            extra['request_id'] = getattr(self, 'request_id', 'system')
            
        # Add service name
        extra['service'] = getattr(self, 'service_name', 'unknown')
        
        return super().makeRecord(name, level, fn, lno, msg, args, exc_info, 
                                func, extra, sinfo)


class JsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter that includes additional fields."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, 
                  message_dict: Dict[str, Any]) -> None:
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format with timezone
        log_record['@timestamp'] = datetime.now(pytz.utc).isoformat()
        
        # Add log level as a string
        log_record['level'] = record.levelname
        
        # Add source location
        log_record['file'] = f"{record.filename}:{record.lineno}"
        
        # Add thread and process info
        log_record['thread'] = record.thread
        log_record['process'] = record.process
        log_record['process_name'] = record.processName
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)


def setup_logging(
    service_name: str,
    *,
    log_level: str = "INFO",
    log_to_file: bool = True,
    enable_json: bool = False,
    path_manager: Optional[PathManager] = None,
) -> logging.Logger:
    """Configure logging for the application.
    
    Args:
        service_name: Name of the service for logging identification
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        enable_json: Whether to use JSON format for logs
        path_manager: Optional path manager for log file paths
        
    Returns:
        Configured logger instance
    """
    # Configure log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure the root logger
    logger = logging.getLogger(service_name)
    logger.setLevel(level)
    
    # Don't propagate to root logger to avoid duplicate logs
    logger.propagate = False
    
    # Clear existing handlers to avoid duplicates
    if logger.handlers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    # Create formatters
    if enable_json:
        formatter = JsonFormatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s',
            timestamp=True
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(request_id)s - '
            '[%(filename)s:%(lineno)d] - %(message)s'
        )
    
    # Console handler (always enabled)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_to_file:
        pm = path_manager or get_path_manager()
        log_dir = pm.logs_dir / service_name
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"{service_name}.log"
        
        # Use RotatingFileHandler with 10MB per file, keep 5 backups
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Add request ID filter
    logger.addFilter(RequestIdFilter())
    
    # Set service name as an attribute
    setattr(logger, 'service_name', service_name)
    
    # Set default request ID
    setattr(logger, 'request_id', 'system')
    
    # Configure root logger to avoid "No handlers could be found" warnings
    logging.basicConfig(level=logging.WARNING, handlers=[])
    
    return logger


def get_logger(name: str, request_id: Optional[str] = None) -> logging.Logger:
    """Get a logger with the given name and optional request ID.
    
    Args:
        name: Logger name (usually __name__)
        request_id: Optional request ID for request tracing
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set request ID if provided
    if request_id is not None:
        setattr(logger, 'request_id', request_id)
    
    return logger


# Default logger for the module
logger = get_logger(__name__)

# Example usage:
if __name__ == "__main__":
    # Configure logging
    log = setup_logging("example", log_level="DEBUG", log_to_file=True)
    
    # Basic logging
    log.info("This is an info message")
    log.warning("This is a warning")
    
    # Logging with context
    log = get_logger(__name__, request_id=str(uuid.uuid4()))
    log.info("This log has a request ID")
    
    try:
        1 / 0
    except Exception as e:
        log.exception("An error occurred")


