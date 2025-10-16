# Coding Style Guide

This document outlines the coding conventions and style guidelines for the Knowledgebase Indexer project.

## File Organization

### Single Responsibility Principle
Each source file should contain only 1 logically coherent component of the system. This promotes:
- **Maintainability**: Each component has a single responsibility
- **Reusability**: Components can be used independently  
- **Readability**: Smaller, focused files are easier to understand
- **Testability**: Individual components can be tested in isolation

### File Size Guidelines
- **Ideal**: All source files should be less than 1000 lines
- **Maximum**: Files exceeding 1000 lines should be refactored into logically independent components
- **Exception**: Generated files or large data structures may exceed this limit

### File Structure Example
```
project/
├── handlers.py              # Base handler interface (~400 lines)
├── handlers/
│   ├── freeplane_handler.py # Freeplane-specific logic (~300 lines)
│   └── markdown_handler.py  # Markdown-specific logic (~350 lines)
├── search.py                # Search engine (~500 lines)
├── keywords.py              # Keyword processing (~400 lines)
└── config.py                # Configuration management (~200 lines)
```

## Debug Logging Requirements

### Multi-Level Logging Support
All components must implement debug logging with multiple detail levels:

```python
from logging_config import create_component_logger, LoggedOperation, AppLogger

logger = create_component_logger('component_name')

def complex_operation(data):
    with LoggedOperation('component_name', 'operation_name', {'size': len(data)}):
        logger.info(f"Starting operation with {len(data)} items")
        
        # Key algorithm steps
        AppLogger.log_algorithm_step('component_name', 'phase_1_initialization', {
            'input_size': len(data),
            'memory_usage': get_memory_usage()
        })
        
        # ... implementation ...
        
        logger.info("Operation completed successfully")
```

### Always-On File Logging
- **Default Mode**: Log to `/tmp/mmdir_debug_YYYYMMDD_HHMMSS_PID.log`
- **One file per invocation**: Each application run creates a separate log file
- **Terminal Clean**: File logging prevents terminal pollution
- **Issue Reproduction**: Past runs can be analyzed for debugging

### Log Levels and Content
- **DEBUG**: Algorithm steps, detailed flow, variable states
- **INFO**: Major operation start/completion, performance metrics
- **WARNING**: Non-fatal issues, fallback behaviors
- **ERROR**: Exceptions with full context

### Structured Logging Examples

```python
# Algorithm step logging
AppLogger.log_algorithm_step('search', 'hierarchical_search_start', {
    'files': len(files),
    'keywords': len(keyword_sequence),
    'first_keyword': keyword_sequence[0]
})

# Performance metric logging  
AppLogger.log_performance_metric('parser', 'file_parsing', duration_ms, {
    'file_size': file_stats.st_size,
    'lines_parsed': line_count
})

# Error context logging
AppLogger.log_error_context('handlers', exception, {
    'file_path': file_path,
    'file_size': os.path.getsize(file_path),
    'handler_type': type(self).__name__
}, 'file_processing')
```

## Code Formatting

### Whitespace Management
- **No trailing whitespace**: Remove all trailing spaces and tabs
- **Editor configuration**: Configure editor to show/remove trailing whitespace
- **Line endings**: Use Unix line endings (LF)
- **Indentation**: 4 spaces, no tabs in Python files

### Function and Method Guidelines

```python
def well_documented_function(param1: str, param2: List[int]) -> Dict[str, Any]:
    """
    Brief description of what the function does.
    
    Args:
        param1: Description of parameter
        param2: Description of parameter with type info
    
    Returns:
        Description of return value
    
    Raises:
        SpecificException: When this specific condition occurs
    """
    logger = create_component_logger('module_name')
    
    with LoggedOperation('module_name', 'function_operation'):
        logger.debug(f"Processing {param1} with {len(param2)} items")
        
        # Implementation with clear logging
        result = perform_work(param1, param2)
        
        logger.info(f"Function completed successfully")
        return result
```

### Class Organization

```python
class WellStructuredClass:
    """
    Class-level documentation explaining purpose and usage.
    
    This class handles X functionality by doing Y.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with configuration."""
        self.config = config
        self.logger = create_component_logger(self.__class__.__name__.lower())
        self._internal_state = {}
        
        self.logger.debug("Component initialized")
    
    def public_method(self, param: str) -> bool:
        """Public interface method."""
        return self._internal_implementation(param)
    
    def _internal_implementation(self, param: str) -> bool:
        """Private implementation detail."""
        self.logger.debug(f"Internal processing: {param}")
        # Implementation...
        return True
```

## Error Handling Patterns

### Comprehensive Error Context

```python
def robust_file_operation(file_path: str):
    logger = create_component_logger('file_ops')
    
    try:
        with LoggedOperation('file_ops', 'file_processing', {'file': file_path}):
            # File operation
            result = process_file(file_path)
            return result
            
    except FileNotFoundError as e:
        AppLogger.log_error_context('file_ops', e, {
            'file_path': file_path,
            'working_directory': os.getcwd(),
            'file_exists': os.path.exists(file_path)
        }, 'file_access')
        raise
        
    except Exception as e:
        AppLogger.log_error_context('file_ops', e, {
            'file_path': file_path,
            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 'N/A',
            'operation': 'file_processing'
        }, 'general_file_operation')
        raise
```

### Graceful Degradation

```python
def fault_tolerant_processing(items: List[str]) -> List[ProcessedItem]:
    logger = create_component_logger('processing')
    results = []
    errors = []
    
    for item in items:
        try:
            result = process_single_item(item)
            results.append(result)
            
        except Exception as e:
            AppLogger.log_error_context('processing', e, {
                'item': item,
                'processed_count': len(results),
                'error_count': len(errors)
            }, 'item_processing')
            
            errors.append((item, str(e)))
            logger.warning(f"Failed to process item {item}: {e}")
            # Continue processing other items
    
    logger.info(f"Processing complete: {len(results)} succeeded, {len(errors)} failed")
    return results
```

## Testing Requirements

### Test File Organization
- **Unit tests**: `tests/unit/test_[component].py`
- **Integration tests**: `tests/integration/test_[workflow].py`  
- **Quick tests**: `tests/test_quick_commit.py`

### Test Naming Conventions

```python
@pytest.mark.quick
class TestComponentName:
    """Test cases for ComponentName class."""
    
    def test_basic_functionality(self):
        """Test basic operation works correctly."""
        pass
    
    def test_error_condition_handling(self):
        """Test component handles error conditions gracefully."""
        pass
    
    def test_edge_case_empty_input(self):
        """Test component handles edge case of empty input."""
        pass

@pytest.mark.slow
@pytest.mark.integration
class TestFullWorkflow:
    """Integration tests for complete workflows."""
    pass
```

## Documentation Standards

### Module-Level Documentation

```python
#!/usr/bin/env python3
"""
Module description explaining the component's purpose.

This module implements X functionality for the Index Generator project.
It provides Y capabilities and is used by Z components.

Key classes:
    ClassName: Brief description
    
Key functions:
    function_name: Brief description
    
Example usage:
    component = ClassName(config)
    result = component.process(data)
"""
```

### API Documentation
- All public methods must have docstrings
- Include parameter types and return types
- Document exceptions that may be raised
- Provide usage examples for complex APIs

### README Updates
When adding new components:
1. Update main README.md with component description
2. Add component to architecture documentation
3. Update usage examples if needed
4. Document any new configuration options

## Performance Guidelines

### Logging Performance Impact
- Use appropriate log levels to minimize overhead
- Structure log messages for easy parsing
- Include performance metrics in algorithm logging

```python
def performance_conscious_operation(large_dataset):
    with LoggedOperation('component', 'bulk_operation', {'size': len(large_dataset)}) as op:
        start_memory = get_memory_usage()
        
        # Bulk processing
        results = []
        for batch in chunk_data(large_dataset, 1000):
            batch_results = process_batch(batch)
            results.extend(batch_results)
            
            # Log progress periodically
            if len(results) % 5000 == 0:
                AppLogger.log_algorithm_step('component', 'batch_progress', {
                    'processed': len(results),
                    'remaining': len(large_dataset) - len(results),
                    'memory_delta': get_memory_usage() - start_memory
                })
        
        return results
```

This coding style ensures maintainable, debuggable, and testable code that follows the project's architectural principles.