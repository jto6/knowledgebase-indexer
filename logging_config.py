#!/usr/bin/env python3
"""
Debug logging facility with multiple detail levels and file output support.

Provides structured logging for debugging and issue triaging with support for:
- Multiple log levels (DEBUG, INFO, WARNING, ERROR)  
- Console and file output modes
- Automatic file logging to /tmp for issue reproduction
- Component-specific logger creation
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import os
import tempfile


class AppLogger:
    """Enhanced logging facility for the Knowledgebase Indexer application."""
    
    _loggers: Dict[str, logging.Logger] = {}
    _log_file: Optional[str] = None
    _console_level = logging.WARNING
    _file_level = logging.DEBUG
    _initialized = False
    
    @classmethod
    def setup_logging(cls, console_level: str = "WARNING", 
                     enable_file_logging: bool = True,
                     log_file: Optional[str] = None) -> str:
        """
        Initialize the logging system.
        
        Args:
            console_level: Console logging level (DEBUG, INFO, WARNING, ERROR)
            enable_file_logging: Whether to enable file logging
            log_file: Specific log file path (default: auto-generated in /tmp)
        
        Returns:
            Path to the log file if file logging is enabled
        """
        if cls._initialized:
            return cls._log_file
        
        # Convert string level to logging constant
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO, 
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR
        }
        cls._console_level = level_map.get(console_level.upper(), logging.WARNING)
        
        # Set up root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # Capture everything
        
        # Clear any existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(cls._console_level)
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler (always captures DEBUG level)
        if enable_file_logging:
            if not log_file:
                # Generate unique filename in /tmp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                pid = os.getpid()
                cls._log_file = f"/tmp/kbi_debug_{timestamp}_{pid}.log"
            else:
                cls._log_file = log_file
            
            try:
                file_handler = logging.FileHandler(cls._log_file, mode='w')
                file_handler.setLevel(cls._file_level)
                file_formatter = logging.Formatter(
                    '%(asctime)s [%(levelname)8s] %(name)s:%(lineno)d: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(file_formatter)
                root_logger.addHandler(file_handler)
                
                # Log startup message directly to avoid circular dependency
                init_logger = logging.getLogger('kbi.startup')
                init_logger.info(f"Logging initialized - File: {cls._log_file}")
                init_logger.info(f"Console level: {console_level}, File level: DEBUG")
                
            except Exception as e:
                # If file logging fails, continue with console only
                console_logger = logging.getLogger('logging_setup')
                console_logger.warning(f"Could not set up file logging: {e}")
                cls._log_file = None
        
        cls._initialized = True
        return cls._log_file
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get or create a logger for a specific component.
        
        Args:
            name: Component name (e.g., 'config', 'search', 'handlers.freeplane')
        
        Returns:
            Logger instance for the component
        """
        if not cls._initialized:
            cls.setup_logging()
        
        if name not in cls._loggers:
            cls._loggers[name] = logging.getLogger(f'kbi.{name}')
        
        return cls._loggers[name]
    
    @classmethod
    def log_algorithm_step(cls, logger_name: str, step: str, details: Dict[str, Any]):
        """
        Log a key algorithm step with structured details.
        
        Args:
            logger_name: Component logger name
            step: Description of the algorithm step
            details: Dictionary of relevant details
        """
        logger = cls.get_logger(logger_name)
        detail_str = ', '.join(f"{k}={v}" for k, v in details.items())
        logger.debug(f"ALGORITHM_STEP: {step} | {detail_str}")
    
    @classmethod
    def log_performance_metric(cls, logger_name: str, operation: str, 
                             duration_ms: float, details: Optional[Dict[str, Any]] = None):
        """
        Log performance metrics for optimization.
        
        Args:
            logger_name: Component logger name
            operation: Description of the operation
            duration_ms: Duration in milliseconds
            details: Additional details dictionary
        """
        logger = cls.get_logger(logger_name)
        detail_str = ""
        if details:
            detail_str = f" | {', '.join(f'{k}={v}' for k, v in details.items())}"
        
        logger.info(f"PERFORMANCE: {operation} took {duration_ms:.2f}ms{detail_str}")
    
    @classmethod
    def log_error_context(cls, logger_name: str, error: Exception, 
                         context: Dict[str, Any], operation: str):
        """
        Log error with full context for debugging.
        
        Args:
            logger_name: Component logger name
            error: The exception that occurred
            context: Dictionary of relevant context
            operation: Description of what was being attempted
        """
        logger = cls.get_logger(logger_name)
        context_str = ', '.join(f"{k}={v}" for k, v in context.items())
        
        logger.error(f"ERROR in {operation}: {type(error).__name__}: {error}")
        logger.error(f"ERROR_CONTEXT: {context_str}")
        logger.debug(f"ERROR_TRACEBACK:", exc_info=True)
    
    @classmethod
    def get_log_file_path(cls) -> Optional[str]:
        """Get the current log file path."""
        return cls._log_file
    
    @classmethod
    def set_component_level(cls, component_name: str, level: str):
        """
        Set logging level for a specific component.
        
        Args:
            component_name: Name of the component
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING, 
            'ERROR': logging.ERROR
        }
        
        logger = cls.get_logger(component_name)
        logger.setLevel(level_map.get(level.upper(), logging.WARNING))


def create_component_logger(component_name: str) -> logging.Logger:
    """
    Convenience function to create a component logger.
    
    Args:
        component_name: Name of the component
    
    Returns:
        Configured logger instance
    """
    return AppLogger.get_logger(component_name)


# Context manager for timing operations
class LoggedOperation:
    """Context manager for logging timed operations."""
    
    def __init__(self, logger_name: str, operation: str, details: Optional[Dict[str, Any]] = None):
        self.logger_name = logger_name
        self.operation = operation
        self.details = details or {}
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        logger = AppLogger.get_logger(self.logger_name)
        logger.debug(f"Starting operation: {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration_ms = (time.time() - self.start_time) * 1000
        
        if exc_type is None:
            AppLogger.log_performance_metric(
                self.logger_name, self.operation, duration_ms, self.details
            )
        else:
            AppLogger.log_error_context(
                self.logger_name, exc_val, 
                {**self.details, 'duration_ms': duration_ms},
                self.operation
            )


# Example usage patterns for components:
"""
# In a component file:
from logging_config import create_component_logger, LoggedOperation, AppLogger

logger = create_component_logger('search')

def search_sequence(files, keywords):
    with LoggedOperation('search', 'hierarchical_search', {'files': len(files), 'keywords': len(keywords)}):
        logger.info(f"Starting search with {len(keywords)} keywords across {len(files)} files")
        
        # Key algorithm steps
        AppLogger.log_algorithm_step('search', 'first_keyword_search', {
            'keyword': keywords[0], 
            'pattern': pattern.pattern,
            'files_to_search': len(files)
        })
        
        # ... implementation ...
        
        logger.info(f"Search completed with {len(results)} total matches")
        return results
"""