```markdown
# EIDP Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill introduces the core development patterns, coding conventions, and operational workflows used in the EIDP Python codebase. It is designed to help contributors quickly understand how to write, structure, and maintain code, as well as how to perform common project tasks such as updating release documentation and expanding integration test coverage.

## Coding Conventions

### File Naming
- Use **snake_case** for all Python files.
  - **Example:** `pdf_discovery.py`, `test_fault_injection_pdf_discovery.py`

### Import Style
- Prefer **relative imports** within the package.
  - **Example:**
    ```python
    from .utils import parse_pdf
    from ..scraper.pdf_discovery import discover_pdfs
    ```

### Export Style
- Use **named exports** (explicitly define what is exported).
  - **Example:**
    ```python
    __all__ = ["discover_pdfs", "parse_pdf"]
    ```

### Commit Messages
- Follow **Conventional Commits** with prefixes like `docs:`, `test:`, `feat:`.
  - **Example:**  
    ```
    feat: add batch isolation checks to pdf discovery
    docs: update release exception record for v5.3.0
    test: expand fault injection scenarios
    ```

## Workflows

### Update Release Documentation
**Trigger:** When preparing for or documenting a new release or status update.  
**Command:** `/update-release-docs`

1. Update or create a release exception record in `docs/reports/`.
2. Update the current objective evidence checklist in `docs/reports/eidp-current-objective-evidence-checklist.md`.
3. Update or refresh the admin checklist in `docs/runbooks/eidp-v1-release-admin-checklist.md` (if needed).

**Example:**
```bash
# Step 1: Edit or create the release exception record
vim docs/reports/2026-05-19-publication-lag-release-exception-record.md

# Step 2: Update the objective evidence checklist
vim docs/reports/eidp-current-objective-evidence-checklist.md

# Step 3: Update admin checklist if required
vim docs/runbooks/eidp-v1-release-admin-checklist.md
```

### Add or Update Integration Tests for PDF Discovery
**Trigger:** When new fault scenarios are identified or when improving test coverage for `pdf_discovery` batch behavior.  
**Command:** `/add-pdf-discovery-integration-test`

1. Modify or add integration test files in `tests/integration/` (especially `test_fault_injection_pdf_discovery.py`).
2. If needed, update `src/eidp/scraper/pdf_discovery.py` to support new testable behaviors.
3. Document or assert new batch isolation/fault contracts in tests.

**Example:**
```python
# In tests/integration/test_fault_injection_pdf_discovery.py

def test_batch_isolation_on_fault():
    # Arrange: set up batch with a known fault
    # Act: run pdf_discovery
    # Assert: verify isolation and error handling
    pass
```
```python
# In src/eidp/scraper/pdf_discovery.py

def discover_pdfs(batch):
    """
    Discover PDFs in a batch, isolating faults.
    """
    # Implementation here
    pass
```

## Testing Patterns

- **Framework:** Not explicitly detected; likely uses standard Python testing tools (e.g., `pytest` or `unittest`).
- **Test Files:** Integration tests are placed in `tests/integration/` and follow the naming pattern `test_*.py`.
- **Test Focus:** Emphasis on batch isolation and fault injection for robust PDF discovery.

**Example Test File:**
```python
# tests/integration/test_fault_injection_pdf_discovery.py

def test_fault_injection():
    # Simulate a fault in PDF discovery and assert correct handling
    pass
```

## Commands

| Command                        | Purpose                                                        |
|--------------------------------|----------------------------------------------------------------|
| /update-release-docs           | Refresh and record release status and checklists for a new release cycle |
| /add-pdf-discovery-integration-test | Add or update integration tests for PDF discovery batch/fault scenarios |
```
