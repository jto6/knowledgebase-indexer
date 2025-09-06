# Test Data Documentation

This directory contains comprehensive test data files used by the Knowledgebase Indexer test suite.

## File Structure

### Sample Mind Map Files (.mm)
- `sample_complex.mm` - Complex Freeplane mind map with nested nodes, rich content, and attributes
  - Tests hierarchical XML parsing
  - Contains nodes with rich content (HTML)
  - Includes attribute-based tags
  - Multiple nesting levels for hierarchy testing

### Sample Markdown Files (.md)  
- `sample_documentation.md` - Comprehensive markdown document with complex structure
  - Multiple heading levels (H1-H4)
  - Nested lists (both ordered and unordered)
  - Code blocks with syntax highlighting
  - YAML frontmatter with tags
  - Hashtag-style tags in content
  - Mixed content types (text, code, lists)

### Keyword Files (.txt)
- `complex_keywords.txt` - Hierarchical keyword structure for search testing
  - Deep nesting (up to 5 levels)
  - Complex colon-separated search sequences
  - Organizational categories and leaf patterns
  - Comment lines and empty line handling
  - Various domain knowledge areas

## Usage in Tests

### Unit Tests
Test data files are used in unit tests to verify:
- File handler parsing capabilities
- Hierarchical node creation
- Search pattern matching
- Tag extraction functionality

### Integration Tests  
Integration tests use these files to verify:
- Complete workflow processing
- Multi-file indexing
- Cross-file search operations
- XML mind map generation

### Quick Commit Tests
Lightweight tests use simplified versions of this data for:
- Basic functionality verification
- Smoke testing
- Rapid feedback during development

## Data Characteristics

### Complexity Levels
- **Simple**: Basic structure for quick tests
- **Medium**: Realistic content for unit tests
- **Complex**: Comprehensive data for integration tests

### Content Domains
Test data covers multiple knowledge domains:
- Software development (programming languages, frameworks)
- System architecture (microservices, databases)
- DevOps practices (containerization, CI/CD)
- API development (REST, GraphQL)
- Testing strategies (unit, integration, E2E)
- Security practices (authentication, authorization)
- Performance optimization (frontend, backend)

### Search Pattern Coverage
Keyword files include patterns for testing:
- Single keyword searches
- Multi-term colon sequences (2-6 terms)
- Hierarchical context sensitivity
- Early termination scenarios
- Complex organizational structures

## Test Data Guidelines

### Adding New Test Data
When adding new test data files:
1. Follow the naming convention: `sample_[type]_[complexity].ext`
2. Include documentation comments explaining the structure
3. Add corresponding test cases that use the new data
4. Update this README with file descriptions

### Maintaining Test Data
- Keep files under 100KB to ensure fast test execution
- Include diverse content to test edge cases
- Maintain realistic structure that mirrors real-world usage
- Update data when adding new features that require testing

## File Size Guidelines
- **Quick tests**: < 10KB files for rapid execution
- **Unit tests**: < 50KB files for reasonable test times  
- **Integration tests**: < 100KB files for comprehensive testing
- **Performance tests**: Larger files may be used for load testing

This test data ensures comprehensive coverage of the Knowledgebase Indexer's functionality across different file types, content structures, and search scenarios.