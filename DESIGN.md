# Spec: SFO Flight Anywhere Search MUI Frontend Design

This document details the frontend visual design, styling tokens, component hierarchy, and the user experience rationale for the SFO Flight Anywhere Search mini-app.

---

## 🎨 Design System & Visual Identity

### 1. Typography
*   **Primary Font:** `Inter` (Sans-serif)
    *   *Reasoning:* Inter is a modern, highly legible typeface engineered specifically for user interfaces. Its neutral tone and open letterforms prevent visual fatigue in dense data displays (like our flights grid).
*   **Secondary Font:** `Roboto`
    *   *Reasoning:* Leveraged for numbers, dates, and currency values. Roboto's semi-monospaced number characters ensure columns align perfectly in pricing tables without text jittering.

### 2. Color System
We use a clean, modern color scheme designed to feel familiar to Google Flights users while maintaining a premium, high-trust appearance.

| Color Token | Hex Code | Role | Design Rationale |
| :--- | :--- | :--- | :--- |
| **Primary Blue** | `#1a73e8` | Brand, Main Actions, Headers | Direct nod to Google Flights' visual identity; establishes instant trust and navigation familiarity. |
| **Success Green** | `#137333` | Prices, Best Deals, Success badges | Soft, accessible dark green that signals a "good deal" and indicates positive pricing states. |
| **Bg Light** | `#f8fafc` | Global Page Background | Slate 50 tint that reduces harsh glare compared to pure `#ffffff` white, easing long search sessions. |
| **Surface White** | `#ffffff` | Card and Container surfaces | Pure white elements placed on the slate background to create high-contrast visual layers. |
| **Text Primary** | `#0f172a` | Headers, Titles, Active Labels | Slate 900; provides sharp contrast and maximum readability. |
| **Text Secondary** | `#475569` | Subtitles, Layovers, Durations | Slate 600; dims less critical information to establish typographic hierarchy. |
| **Border Slate** | `#e2e8f0` | Dividers, Grid Borders | Slate 200; thin separators that structure grid items without adding visual noise. |

---

## 🖥️ Layout & Component Hierarchy

We implement a responsive split-pane layout to balance conversational AI controls with structured database results.

```
┌───────────────────────────────────────┬───────────────────────┐
│              App Bar (Title & Scraper Status)                 │
├───────────────────────────────────────┼───────────────────────┤
│                                       │                       │
│                                       │                       │
│        Flights Grid (70% Width)       │  AI Agent (30% Width) │
│   - Quick Filters Bar                 │  - Conversational Box │
│   - Data Table (MUI DataGrid)         │  - Filter Tags        │
│   - Flight Cards                      │  - Dynamic Sync Feed  │
│                                       │                       │
│                                       │                       │
└───────────────────────────────────────┴───────────────────────┘
```

### 1. The Flights Grid (Left Pane - 70% width)
Displays flight listings matching active search queries.
*   **MUI Component:** `Box` container housing a `DataGrid` or `List` of cards.
*   **Quick Filters Bar (`Paper`):** A horizontal filter bar containing sliders for `Price`, checkboxes for `Airlines`, and a multi-select dropdown for `Country/Airport`.
*   **Table / List Cards (`Card`):**
    *   Renders the Airline Logo (IATA icon), flight duration, layovers/stops, price in green, and a prominent blue button: `Book on Google Flights`.
    *   *Link Rationale:* Direct external deep-link with parameters (`q=Flights from SFO to...`) ensuring users can book immediately.

### 2. The AI Chatbot Panel (Right Pane - 30% width)
A docking side drawer or persistent chat window.
*   **MUI Component:** `Paper` card with a fixed height, scrollable messages list, and a bottom input container (`TextField` with an `IconButton` submit).
*   **Message Bubble (`Box`):**
    *   *User Bubbles:* Soft blue background (`#e8f0fe`), white text, aligned to the right.
    *   *Agent Bubbles:* Slate gray background (`#f1f5f9`), dark text, aligned to the left.
*   **Dynamic Synchronization Script:**
    *   When the user submits a message, the chatbot sends the text to `/api/chat`.
    *   The API returns the agent text along with a list of matching flight records or SQL filter states.
    *   The frontend intercepts this payload, updates the main Flights Grid state, highlights matching rows, and displays custom tags (e.g., `"Japan"`, `"< $800"`) under the chat input.

---

## 🧱 Key MUI Components List

1.  `CssBaseline`: Standardizes box-sizing, margins, and font rendering across different browsers.
2.  `DataGrid`: Out-of-the-box support for pagination, sorting by price/duration, and robust column rendering.
3.  `Card` & `CardContent`: Holds each flight's information with clean shadows (`box-shadow: 0 1px 3px rgba(0,0,0,0.12)`).
4.  `TextField`: Rounded variant (`borderRadius: '24px'`) for the chatbot message input, mimicking the Google Search box style for familiarity.
5.  `Chip`: Used to display active AI-applied filters (e.g., `Max Price: $600`). Dismissing a chip automatically resets the filter and updates the grid.
