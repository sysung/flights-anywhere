# Code Review and Refactoring Plan

**Goal:** Perform a comprehensive code review of all non-markdown source files and refactor to address issues, warnings, and code hygiene.

## Proposed Changes

### 1. Backend (FastAPI, Python)
* **Modify:** `app/db/models.py`
  * Replace deprecated `datetime.utcnow` with `lambda: datetime.now(timezone.utc).replace(tzinfo=None)` for database defaults to eliminate `DeprecationWarning` under Python 3.10+.
* **Modify:** `app/scraper/extractor.py`
  * Replace `datetime.utcnow()` calls with `datetime.now(timezone.utc).replace(tzinfo=None)`.
  * Fix the database seeding logic for `Airport` so that new/missing airports detected during scraping are dynamically seeded rather than skipped, keeping the database in sync with the scraper.

### 2. Frontend (Vite, React)
* **Modify:** `frontend/src/components/QuickFilters.jsx`
  * Fix the MUI Autocomplete warning by avoiding passing raw `inputProps` and custom props directly to the DOM elements.
* **Modify:** `frontend/src/components/ChatbotPanel.jsx`
  * Ensure consistent MUI prop configuration to eliminate console warnings.

---

## Verification Plan

### Automated Tests
* Run backend tests: `DATABASE_URL=sqlite:/// PYTHONPATH=. .venv/bin/python -m pytest`
* Run frontend tests: `npm run test --prefix frontend -- --run`
