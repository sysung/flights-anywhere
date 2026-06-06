# Design Specification: Flight Dashboard Redesign

Redesign SFO Anywhere Flights dashboard to improve layout responsiveness, streamline the search filters bar, and establish a distinct, premium visual identity for all main components.

---

## 1. Objectives & Requirements

- **Fluid Split-Pane Layout**: The UI must use 100% viewport width, splitting the page into a 70% width Left Panel (table & filters) and a 30% width Right Panel (AI Chatbot).
- **Sticky Chatbot**: The chatbot needs to remain anchored to the viewport height with an internally scrollable chat message feed, rather than scrolling off-screen.
- **Streamlined Filters Row**:
  - The filters should reside on a single compact horizontal line.
  - The **Max Price Slider** should be shortened.
  - The **Destination Code** filter must be a compact single-select Autocomplete field (handling typing + dropdown preselect options).
  - The **Airlines** filter must be a multi-select Autocomplete field showing selected items as Chip tags inside the input.
  - A red **Clear Filters** button (MUI error color, outlined style) must be positioned on the far right of the filter line.
- **Visual Color Separation**:
  - Filters Panel: Cool Slate tint (`#f1f5f9`).
  - Flight listings: Crisp White (`#ffffff`).
  - AI Assistant: Soft Lavender/Indigo border (`#ddd6fe`) and lavender feed background (`#f5f3ff`).

---

## 2. Proposed Implementation Details

### Component Layout Map
```
+-----------------------------------------------------------------------------------+
| ✈️ SFO Anywhere Flights Header                                                      |
+------------------------------------+----------------------------------------------+
| LEFT PANEL (70% Width)             | RIGHT PANEL (30% Width)                      |
|                                    |                                              |
| +--------------------------------+ | +------------------------------------------+ |
| | Filters Row:                   | | | AI Flight Assistant (Sticky Height)       | |
| | [Slider] [Dest] [Airlines] [X] | | | Header (Indigo Gradient)                 | |
| +--------------------------------+ | |                                          | |
|                                    | | +--------------------------------------+ | |
| +--------------------------------+ | | | Message history (Lavender Bg,        | | |
| | Flights Table (Crisp White)    | | | | internally scrollable)               | | |
| |                                | | | +--------------------------------------+ | |
| |                                | | |                                          | |
| |                                | | | [Chat input field]                       | |
| +--------------------------------+ | +------------------------------------------+ |
+------------------------------------+----------------------------------------------+
```

### Files to Modify
- **[`frontend/src/App.jsx`](file:///home/sysung/lumalabs-eng-take-home-f95f32dccc670e06ea55b05b2d10e28e78151a04/frontend/src/App.jsx)**:
  - Update `Container` wrapper to a fluid CSS Box spanning full width.
  - Re-structure grid columns and heights to enforce `70% / 30%` ratio.
  - Implement fixed height and `overflowY` for chatbot list and columns.
  - Swap current dropdown filters with MUI `<Autocomplete>` components.
  - Restructure filters row to place elements side-by-side.
  - Replace the text-based filter clear button with `<Button variant="outlined" color="error">` on the far right.
  - Add inline style overrides/classes to support slate backgrounds for filters and lavender for chat.

---

## 3. Verification Plan

### Manual Verification
- Resize browser window to check layout fluid responsiveness at different widths.
- Ensure the Chat feed scrolls independently without causing the whole page to scroll.
- Test typing custom destination codes (like LHR, JFK) and selecting from the dropdown.
- Test selecting multiple airlines, verifying they appear as chips, and can be deleted individually.
- Hover over the red outline Clear Filters button and verify it fills with solid red.
- Confirm all active filters (slider, destination, airlines) clear correctly when clicking the button.
