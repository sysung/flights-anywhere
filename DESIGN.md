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
We use a clean, modern color scheme designed to feel familiar to Google Flights users while maintaining a premium, high-trust appearance, with distinct color separations for key sections.

| Color Token | Hex Code / Value | Role | Design Rationale |
| :--- | :--- | :--- | :--- |
| **Primary Blue** | `#1a73e8` | Brand, Main Actions, Headers | Direct nod to Google Flights' visual identity; establishes instant trust and navigation familiarity. |
| **Success Green** | `#137333` | Prices, Best Deals, Success badges | Soft, accessible dark green that signals a "good deal" and indicates positive pricing states. |
| **Bg Light** | `#f8fafc` | Global Page Background | Slate 50 tint that reduces harsh glare compared to pure `#ffffff` white, easing long search sessions. |
| **Surface White** | `#ffffff` | Card and Container surfaces | Pure white elements placed on the slate background to create high-contrast visual layers. |
| **Text Primary** | `#0f172a` | Headers, Titles, Active Labels | Slate 900; provides sharp contrast and maximum readability. |
| **Text Secondary** | `#475569` | Subtitles, Layovers, Durations | Slate 600; dims less critical information to establish typographic hierarchy. |
| **Border Slate** | `#e2e8f0` | Dividers, Grid Borders | Slate 200; thin separators that structure grid items without adding visual noise. |
| **Filters Background**| `#f1f5f9` (Cool Slate) | Filters container surface | Cool slate background to group and distinguish filter inputs from the table below. |
| **Chatbot Feed Bg** | `#f5f3ff` (Lavender Tint) | Chat feed messages area bg | Premium soft violet/lavender tint to set the chatbot assistant visually apart. |
| **Chatbot Header** | `linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)` | Chat Title block bg | Dynamic purple gradient giving a premium, AI-native touch to the flight assistant. |

---

## 🖥️ Layout & Component Hierarchy

We implement a responsive, fluid split-pane layout to balance conversational AI controls with structured database results.

```
┌───────────────────────────────────────────────────────────────────────┐
│                    App Bar (Title & Scraper Status)                   │
├───────────────────────────────────────┬───────────────────────────────┤
│                                       │                               │
│        Left Panel (70% Width)         │     Right Panel (30% Width)   │
│   ┌───────────────────────────────┐   │   ┌───────────────────────┐   │
│   │ Filters Row (Slate Background)│   │   │ AI Assistant          │   │
│   │ [Slider][Dest][Airlines] [X]  │   │   │ - Title Gradient      │   │
│   └───────────────────────────────┘   │   │ - Lavender Message    │   │
│   ┌───────────────────────────────┐   │   │   History feed        │   │
│   │ Flights Listings Table        │   │   │   (Scrollable)        │   │
│   │ (Crisp White Background)      │   │   │ - Chat input field    │   │
│   └───────────────────────────────┘   │   └───────────────────────┘   │
│                                       │                               │
└───────────────────────────────────────┴───────────────────────────────┘
```

### 1. The Flights Grid (Left Pane - 70% width)
Displays flight listings matching active search queries.
*   **MUI Component:** `Box` container spanning `70%` width of the screen.
*   **Inline Filters Bar (`Paper`):** 
    *   Styled with Cool Slate (`#f1f5f9`) background and slate accent line (`borderLeft: '4px solid #64748b'`).
    *   **Max Price Slider:** Shorter width slider for filtering flights by maximum price.
    *   **Destination Code Autocomplete:** Single-select search filter populated with active routes. Text-box with pre-select options, restricted to 3 uppercase letters.
    *   **Airlines Autocomplete:** Multi-select input displaying active selections as compact Chips inside the input area.
    *   **Clear Filters Button:** Outlined red button (`variant="outlined"` and `color="error"`) positioned on the far right of the row.
*   **Flights Listing Table (`Paper`):**
    *   Styled with Crisp White (`#ffffff`) background and primary blue accent line (`borderLeft: '4px solid #1a73e8'`).
    *   Displays routes and schedules using MUI `DataGrid`.

### 2. The AI Chatbot Panel (Right Pane - 30% width)
A docking side panel locked to the viewport height.
*   **MUI Component:** `Paper` card with a fixed height (`calc(100vh - 80px)`), an internally scrollable messages feed (`overflowY: 'auto'`), and a bottom input container (`TextField` with an `IconButton` submit).
*   **Message Bubble (`Box`):**
    *   *User Bubbles:* Indigo background (`#4f46e5`), white text, aligned to the right.
    *   *Agent Bubbles:* Crisp White background (`#ffffff`), dark slate text (`#0f172a`), thin purple border (`1px solid #e9d5ff`), aligned to the left.
*   **Dynamic Synchronization Script:**
    *   When the user submits a message, the chatbot sends the text to `/api/chat`.
    *   The API returns the agent text along with SQL filter states.
    *   The frontend updates the filter states (Slider, Destination, Airlines), filtering the listings table in real-time.

---

## 🧱 Key MUI Components List

1.  `CssBaseline`: Standardizes box-sizing, margins, and font rendering across different browsers.
2.  `DataGrid`: Out-of-the-box support for pagination, sorting by price/duration, and robust column rendering.
3.  `Autocomplete`: Used for Destination search (single-select with dropdown list) and Airlines selection (multi-select with compact dismissible Chips).
4.  `Button`: Used with `variant="outlined"` and `color="error"` for the red outline Clear Filters button.
5.  `Chip`: Used to display active AI-applied filters (e.g., `Max Price: $600`) and multiselect choices. Dismissing a chip automatically resets the filter and updates the grid.
