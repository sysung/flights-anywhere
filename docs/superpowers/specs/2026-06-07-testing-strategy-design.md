# Frontend and Scraper Testing Strategy Design

**Date:** 2026-06-07  
**Topic:** Frontend & Scraper Testing Setup  

## 1. Goal
Ensure the reliability of both the React frontend (filters, table, chatbot panel) and the python scraper by establishing distinct unit, integration, and E2E test suites with deterministic mocking.

## 2. Architecture & Tech Stack
- **Frontend Unit & Integration Tests:**
  - **Vitest:** The test runner.
  - **React Testing Library (RTL) & jsdom:** For rendering and interacting with React components in a node-based test environment.
- **Backend & Scraper Tests:**
  - **pytest:** The python test runner.
  - **Playwright (Python):** For E2E/integration testing of the scraper flow.

---

## 3. Detailed Component Testing Design

### Frontend Component Tests (Vitest + RTL)
1. **`QuickFilters` (Unit):**
   - Verify that predefined quick filter buttons render.
   - Verify that clicking a quick filter button triggers the corresponding callback with the correct filter criteria.
2. **`FlightsGrid` (Unit):**
   - Verify that the MUI DataGrid renders with the supplied flight data rows.
   - Verify that empty state is shown when no flight data is provided.
3. **`ChatbotPanel` (Integration):**
   - Mock the global `fetch` API.
   - Verify that typing a message and clicking send appends the message to the chat history.
   - Verify that a mock success response from the server updates the chatbot conversation.

### Scraper & Backend Tests (pytest)
1. **`test_stream_parser.py` (Unit):**
   - Validate that `WizStreamParser` parses chunked stream strings, strips XSSI prefixes, and decodes nested base64 protobuf payloads correctly.
2. **`test_scraper.py` (Integration/E2E):**
   - Use Playwright in headless mode.
   - Intercept network requests targeting `google.com` and respond with a pre-recorded mock response.
   - Verify that the scraper correctly parses the mock data and returns flights without hitting the live external endpoint.

---

## 4. Mocking Strategy
- **Frontend Network Mocking:** Simple `global.fetch = vi.fn(...)` mocks will be used to simulate backend responses for the chatbot assistant and flight search endpoints.
- **Scraper Network Mocking:** Playwright's `page.route` will intercept network calls to mock the Google Flights `GetShoppingResults` endpoint.
