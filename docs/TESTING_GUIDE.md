# Testing Guide for Knowledgebase Indexer

This guide provides comprehensive information about the testing infrastructure and methodologies implemented for the Knowledgebase Indexer project.

## Overview

The testing framework is designed around three primary categories:
- **Quick Commit Tests**: Fast feedback for development (~30 seconds)
- **Unit Tests**: Component-level testing (~2 minutes)  
- **Integration Tests**: Full workflow testing (~5 minutes)

## Test Structure

### Directory Organization
```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── test_quick_commit.py        # Quick tests for rapid feedback
├── unit/                       # Unit tests by component
│   ├── test_config.py         # Configuration loading tests
│   ├── test_handlers.py       # File handler tests
│   ├── test_keywords.py       # Keyword parsing tests
│   └── test_search.py         # Search engine tests
├── integration/                # Full workflow tests  
│   └── test_full_workflow.py  # End-to-end integration tests
└── data/                       # Test data files
    ├── sample_complex.mm      # Complex Freeplane mind map
    ├── sample_documentation.md # Comprehensive Markdown doc
    └── complex_keywords.txt   # Hierarchical keyword structure
```

## Running Tests

### Using the Test Runner
```bash
# Quick commit tests (< 30 seconds)
python run_tests.py quick

# Unit tests (< 2 minutes)  
python run_tests.py unit

# Integration tests (< 5 minutes)
python run_tests.py integration

# All tests with reporting (< 10 minutes)
python run_tests.py all

# Tests with coverage reporting
python run_tests.py coverage
```

### Using Make Commands
```bash
# Quick development feedback
make test-quick

# Comprehensive testing
make test-all

# With coverage reporting
make test-coverage

# All quality checks + tests
make ci-test
```

### Direct Pytest Usage
```bash
# Quick tests only
pytest tests/test_quick_commit.py -m quick -v

# Unit tests with detailed output
pytest tests/unit/ -v --tb=long

# Integration tests
pytest tests/integration/ -m slow -v

# All tests with coverage
pytest --cov=. --cov-report=html tests/
```

## Test Categories and Markers

### Test Markers
- `@pytest.mark.quick` - Fast tests for development feedback
- `@pytest.mark.slow` - Longer-running tests
- `@pytest.mark.integration` - Full workflow tests
- `@pytest.mark.unit` - Component-level tests

### When to Use Each Category

#### Quick Commit Tests
**Purpose**: Rapid feedback during development
**Duration**: < 30 seconds
**Use Cases**:
- Pre-commit hooks
- Continuous development feedback
- Basic functionality verification
- Smoke testing

**Example**:
```python
@pytest.mark.quick
def test_config_loading_basic():
    """Test that configuration loads without errors."""
    loader = ConfigLoader()
    config = loader._get_default_config()
    assert 'directories' in config
```

#### Unit Tests  
**Purpose**: Component-level testing in isolation
**Duration**: < 2 minutes total
**Use Cases**:
- Individual class/function testing
- Error condition testing
- Edge case verification
- Mock-based testing

**Example**:
```python
@pytest.mark.quick
class TestHierarchicalNode:
    def test_node_creation(self):
        """Test basic node creation and properties."""
        node = HierarchicalNode(id="test", content="content")
        assert node.id == "test"
        assert node.content == "content"
```

#### Integration Tests
**Purpose**: Full workflow and system integration testing
**Duration**: < 5 minutes total
**Use Cases**:
- End-to-end workflow testing
- Multi-component interaction testing
- File system integration
- Configuration discovery testing

**Example**:
```python
@pytest.mark.slow
@pytest.mark.integration
def test_full_workflow_with_keywords(temp_dir):
    """Test complete workflow including keyword searching."""
    # Set up test environment with files
    # Run complete index generation
    # Verify all outputs and side effects
```

## Test Fixtures and Utilities

### Common Fixtures
```python
# Temporary directory for test files
def test_with_temp_files(temp_dir):
    test_file = temp_dir / "test.md"
    test_file.write_text("# Test\nContent")
    # Test implementation

# Sample configuration  
def test_with_config(sample_config):
    generator = IndexGenerator(sample_config)
    # Test implementation

# Test data files
def test_with_test_data(test_files):
    md_file = test_files['markdown']
    mm_file = test_files['freeplane'] 
    # Test implementation
```

### Test Data Generation
The `TestDataGenerator` class provides methods for creating complex test data:

```python
def test_complex_scenario(temp_dir, test_data_generator):
    # Create complex Freeplane file
    mm_file = test_data_generator.create_complex_freeplane(
        temp_dir / "complex.mm", 
        depth=4, 
        nodes_per_level=3
    )
    
    # Create complex Markdown file
    md_file = test_data_generator.create_complex_markdown(
        temp_dir / "complex.md"
    )
```

## Debugging Tests

### Debug Logging in Tests
Tests automatically set up debug logging to capture detailed information:

```python
def test_with_debugging():
    # Logging is automatically configured by conftest.py
    logger = create_component_logger('test')
    logger.debug("Debug information during test")
```

### Running Tests with Debug Output
```bash
# Verbose output with debug logging
pytest tests/ -v -s --log-cli-level=DEBUG

# Capture and display all logging
pytest tests/ -v --capture=no --log-cli-level=DEBUG

# Run specific test with maximum detail
pytest tests/unit/test_search.py::TestSearchEngine::test_complex_search -v -s --tb=long
```

### Test Log Files
Each test run creates a log file in `/tmp/` with detailed debugging information:
- File: `/tmp/mmdir_debug_YYYYMMDD_HHMMSS_PID.log`
- Contains: Full debug traces, algorithm steps, performance metrics
- Usage: For post-test analysis and debugging

## Coverage Reporting

### Generating Coverage Reports
```bash
# HTML coverage report
python run_tests.py coverage
# Creates: htmlcov/index.html

# Terminal coverage report  
pytest --cov=. --cov-report=term-missing tests/

# XML coverage report (for CI)
pytest --cov=. --cov-report=xml tests/
```

### Coverage Targets
- **Minimum**: 80% line coverage
- **Goal**: 90% line coverage  
- **Focus Areas**: Core algorithms, error handling, edge cases

## Performance Testing

### Performance Monitoring
Tests include automatic performance monitoring:

```python
def test_performance_critical_function():
    with LoggedOperation('test', 'performance_test') as op:
        # Test implementation
        result = expensive_operation(large_dataset)
    
    # Performance metrics automatically logged
    assert result is not None
```

### Benchmark Testing
```bash
# Show test durations
pytest --durations=10 tests/

# Performance benchmarks  
make benchmark
```

## Continuous Integration

### CI Test Pipeline
```bash
# Complete CI test suite
make ci-test

# Equivalent to:
make install-dev
make check          # Code quality
make test-all       # All tests
```

### Pre-commit Testing
```bash
# Before committing changes
make pre-commit

# Runs: format, lint, type-check, test-quick
```

## Test Data Management

### Test Data Files
- **Location**: `tests/data/`
- **Types**: `.mm`, `.md`, `.txt` files
- **Size Limits**: < 100KB per file
- **Content**: Realistic, diverse test scenarios

### Creating New Test Data
1. Add file to `tests/data/`
2. Document structure in `tests/data/README.md`  
3. Create corresponding test cases
4. Ensure file size < 100KB

## Troubleshooting Tests

### Common Issues

#### Test Discovery Problems
```bash
# Verify test discovery
pytest --collect-only tests/

# Check for syntax errors
python -m py_compile tests/unit/test_*.py
```

#### Import Errors
```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Run tests from project root
cd /path/to/project
python -m pytest tests/
```

#### Fixture Issues
```bash
# List available fixtures
pytest --fixtures tests/

# Run specific fixture tests
pytest tests/conftest.py -v
```

### Test Environment Issues

#### Temporary Directory Problems
```bash
# Check temp directory permissions
ls -la /tmp/

# Clean old test files
make clean
```

#### Dependency Issues  
```bash
# Reinstall test dependencies
make install-dev

# Check package versions
pip list | grep -E "(pytest|pyyaml|jsonschema)"
```

## Best Practices

### Writing Effective Tests
1. **Test Naming**: Use descriptive names explaining what is tested
2. **Test Structure**: Follow Arrange-Act-Assert pattern
3. **Test Isolation**: Each test should be independent
4. **Error Testing**: Include negative test cases
5. **Edge Cases**: Test boundary conditions

### Test Maintenance
1. **Regular Cleanup**: Remove obsolete tests
2. **Data Updates**: Keep test data current and realistic
3. **Performance Monitoring**: Watch for slow tests
4. **Coverage Analysis**: Identify untested code paths

### Development Workflow
1. **Red-Green-Refactor**: Write failing test, implement, refactor
2. **Commit Testing**: Run quick tests before commits
3. **Integration Testing**: Run full tests before merges
4. **Continuous Feedback**: Monitor test results in CI/CD

This comprehensive testing framework ensures high code quality, rapid development feedback, and robust system verification across all components of the Knowledgebase Indexer.