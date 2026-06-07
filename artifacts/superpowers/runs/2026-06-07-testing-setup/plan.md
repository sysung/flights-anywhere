# FastAPI and Vite/React Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize and clean up both backend (FastAPI) and frontend (Vite/React) codebases by implementing the agreed-upon optimizations.

**Architecture:** 
- **Backend:** Update `app/main.py` to use `lifespan` context manager, delegate scrapes to `BackgroundTasks`, and shift booking URL generation to Pydantic computed fields in `app/db/schemas.py`.
- **Frontend:** Add Vite path aliases (`@/*`), extract state management from `App.jsx` into a custom `FlightsContext`, and fix MUI Autocomplete prop warning messages.

**Tech Stack:** FastAPI, Pydantic, React Context, Vite.

---

## Proposed Changes

### Backend Refactoring

#### [MODIFY] [main.py](file:///home/sysung/lumalabs-eng-take-home-f95f32dccc670e06ea55b05b2d10e28e78151a04/app/main.py)
#### [MODIFY] [schemas.py](file:///home/sysung/lumalabs-eng-take-home-f95f32dccc670e06ea55b05b2d10e28e78151a04/app/db/schemas.py)

### Frontend Refactoring

#### [MODIFY] [vite.config.js](file:///home/sysung/lumalabs-eng-take-home-f95f32dccc670e06ea55b05b2d10e28e78151a04/frontend/vite.config.js)
#### [NEW] [FlightsContext.jsx](file:///home/sysung/lumalabs-eng-take-home-f95f32dccc670e06ea55b05b2d10e28e78151a04/frontend/src/context/FlightsContext.jsx)
#### [MODIFY] [App.jsx](file:///home/sysung/lumalabs-eng-take-home-f95f32dccc670e06ea55b05b2d10e28e78151a04/frontend/src/App.jsx)
#### [MODIFY] [QuickFilters.jsx](file:///home/sysung/lumalabs-eng-take-home-f95f32dccc670e06ea55b05b2d10e28e78151a04/frontend/src/components/QuickFilters.jsx)
#### [MODIFY] [ChatbotPanel.jsx](file:///home/sysung/lumalabs-eng-take-home-f95f32dccc670e06ea55b05b2d10e28e78151a04/frontend/src/components/ChatbotPanel.jsx)
#### [MODIFY] [FlightsGrid.jsx](file:///home/sysung/lumalabs-eng-take-home-f95f32dccc670e06ea55b05b2d10e28e78151a04/frontend/src/components/FlightsGrid.jsx)

---

### Task 1: Refactor FastAPI Backend

**Files:**
- Modify: `app/main.py`
- Modify: `app/db/schemas.py`

- [x] **Step 1: Shift dynamic booking_url to Pydantic schema**
- [x] **Step 2: Implement FastAPI lifespan handler and BackgroundTasks**

---

### Task 2: Configure Vite Path Aliases

**Files:**
- Modify: `frontend/vite.config.js`

- [x] **Step 1: Add path resolving config to Vite**

---

### Task 3: Extract Global State to React Context

**Files:**
- Create: `frontend/src/context/FlightsContext.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/QuickFilters.jsx`
- Modify: `frontend/src/components/ChatbotPanel.jsx`
- Modify: `frontend/src/components/FlightsGrid.jsx`

- [x] **Step 1: Create FlightsContext provider**
- [x] **Step 2: Clean up App.jsx and sub-components**

---

## Verification Plan

### Automated Tests
- Run Vitest: `npm run test --prefix frontend`
- Run pytest: `DATABASE_URL=sqlite:/// PYTHONPATH=. pytest`
