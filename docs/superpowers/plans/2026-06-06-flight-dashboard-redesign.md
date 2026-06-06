# Flight Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign SFO Anywhere Flights dashboard to implement a fluid 70/30 split layout, a sticky scrollable chatbot on the right, compact filters on a single row (using Autocomplete fields), a red outlined reset button, and distinct theme colors.

**Architecture:** Update `frontend/src/App.jsx` layout container to be full-width (fluid), lock chatbot height to viewport and set internal scrollable area, replace dropdown filters with MUI Autocomplete components, wrap the filter row in a single horizontal flex layout, and style the components with specific slate, white, and lavender colors.

**Tech Stack:** React, Material UI (MUI), DataGrid

---

### Task 1: Fluid Layout Structure and Sidebar Docking

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Modify root containers to be fluid and full-width**
  
  In `frontend/src/App.jsx`, update the root structure and the container around the main workspace to allow full-screen width.
  
  ```jsx
  // Modify container from:
  <Container maxWidth="xl" sx={{ flexGrow: 1, py: 3, display: 'flex', flexDirection: 'column' }}>
  // To:
  <Box sx={{ flexGrow: 1, px: 3, py: 2, display: 'flex', flexDirection: 'column', width: '100%' }}>
  ```

- [ ] **Step 2: Implement sticky, scrollable chatbot container**
  
  Set the Chatbot panel's outer Paper container to have a fixed height matching the viewport height, and make the chat message list container internally scrollable with a lavender background.
  
  Modify `frontend/src/App.jsx` chatbot Paper settings (around line 554):
  ```jsx
  <Paper 
    sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: 'calc(100vh - 120px)', 
      overflow: 'hidden',
      border: '1px solid #ddd6fe',
      boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.05), 0 4px 6px -4px rgb(0 0 0 / 0.05)'
    }}
  >
  ```
  And set the message history container:
  ```jsx
  <Box sx={{ flexGrow: 1, p: 2, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2, bgcolor: '#f5f3ff' }}>
  ```

- [ ] **Step 3: Commit layout changes**
  
  ```bash
  git add frontend/src/App.jsx
  git commit -m "feat: implement fluid 70/30 split layout and sticky chatbot sidebar"
  ```

---

### Task 2: Redesign Quick Filters Row (Short Slider, Autocompletes & Red Reset Button)

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Replace filter containers with a single inline horizontal row**
  
  Replace the nested `Grid` in the Quick Filters panel with a single flexbox container that keeps all controls aligned horizontally.
  
  Change the content inside Quick Filters `Paper` (around line 409):
  ```jsx
  <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 2.5, flexWrap: 'wrap' }}>
    {/* Short Max Price Slider */}
    <Box sx={{ width: 160, flexShrink: 0 }}>
      <Typography variant="body2" sx={{ mb: 1, color: 'text.secondary', fontWeight: 500 }}>
        Max Price: <strong>${maxPrice}</strong>
      </Typography>
      <Slider
        value={maxPrice}
        onChange={(e, val) => setMaxPrice(val)}
        min={100}
        max={2000}
        step={50}
        valueLabelDisplay="auto"
      />
    </Box>
  ```

- [ ] **Step 2: Implement single-select Destination Autocomplete**
  
  Replace the old Autocomplete implementation with a cleaner, compact styled Autocomplete input.
  
  ```jsx
  {/* Destination Autocomplete */}
  <Box sx={{ width: 140, flexShrink: 0 }}>
    <Typography variant="body2" sx={{ mb: 0.5, color: 'text.secondary', fontWeight: 500 }}>
      Destination
    </Typography>
    <Autocomplete
      size="small"
      options={availableDestinations}
      value={destinationFilter}
      onChange={(event, newValue) => {
        setDestinationFilter(newValue || '');
      }}
      inputValue={destinationFilter}
      onInputChange={(event, newInputValue) => {
        setDestinationFilter(newInputValue.toUpperCase());
      }}
      renderInput={(params) => (
        <TextField
          {...params}
          placeholder="Anywhere"
          inputProps={{
            ...params.inputProps,
            maxLength: 3,
            style: { textTransform: 'uppercase', fontWeight: 'bold' }
          }}
        />
      )}
    />
  </Box>
  ```

- [ ] **Step 3: Implement multi-select Airlines Autocomplete**
  
  Replace the old Select dropdown with a multi-select Autocomplete field where selections render as Chips inside the text input box.
  
  ```jsx
  {/* Airlines Autocomplete */}
  <Box sx={{ flexGrow: 1, minWidth: 200 }}>
    <Typography variant="body2" sx={{ mb: 0.5, color: 'text.secondary', fontWeight: 500 }}>
      Airlines
    </Typography>
    <Autocomplete
      multiple
      size="small"
      options={availableAirlines}
      value={selectedAirlines}
      onChange={(event, newValue) => {
        setSelectedAirlines(newValue);
      }}
      renderInput={(params) => (
        <TextField
          {...params}
          placeholder="All Airlines"
        />
      )}
      renderTags={(value, getTagProps) =>
        value.map((option, index) => (
          <Chip
            label={option}
            size="small"
            {...getTagProps({ index })}
          />
        ))
      }
    />
  </Box>
  ```

- [ ] **Step 4: Implement Red Outlined Reset Button**
  
  Add the Reset Button to the far right of the filter row, using MUI's outlined error button style.
  
  ```jsx
  {/* Clear/Reset Button */}
  <Box sx={{ flexShrink: 0 }}>
    <Button 
      variant="outlined" 
      color="error" 
      startIcon={<FilterAltOffIcon />} 
      onClick={handleResetFilters}
      disabled={maxPrice === 2000 && selectedAirlines.length === 0 && !destinationFilter}
      sx={{ height: 40 }}
    >
      Clear Filters
    </Button>
  </Box>
  ```

- [ ] **Step 5: Commit filters row changes**
  
  ```bash
  git add frontend/src/App.jsx
  git commit -m "feat: redesign filters row using compact Autocompletes and red outlined reset button"
  ```

---

### Task 3: Color Contrast and Design Polish

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Set component background colors and headers**
  
  Apply the distinct coloring to each component:
  
  - Quick Filters Card background: Cool Slate `#f1f5f9` with left accent line:
    ```jsx
    // Modify Quick Filters Card Paper styles:
    <Paper 
      sx={{ 
        p: 2.5,
        bgcolor: '#f1f5f9',
        borderLeft: '4px solid #64748b',
        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05)'
      }}
    >
    ```
  
  - Flight listings Card background: Crisp White `#ffffff` with blue left accent line:
    ```jsx
    // Modify Flight listings Card Paper styles:
    <Paper 
      sx={{ 
        flexGrow: 1, 
        p: 2, 
        minHeight: '450px', 
        display: 'flex', 
        flexDirection: 'column',
        bgcolor: '#ffffff',
        borderLeft: '4px solid #1a73e8',
        boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05)'
      }}
    >
    ```
  
  - AI Assistant Message Bubbles styling:
    - User message: `#4f46e5` (Indigo background, white text)
    - Agent message: `#ffffff` (White background, `#0f172a` text, purple border `#e9d5ff`)
    
    ```jsx
    // Update msg rendering:
    bgcolor: isAgent ? '#ffffff' : '#4f46e5',
    color: isAgent ? '#0f172a' : '#ffffff',
    borderRadius: isAgent ? '4px 16px 16px 16px' : '16px 4px 16px 16px',
    border: isAgent ? '1px solid #e9d5ff' : 'none',
    ```

- [ ] **Step 2: Verify look and feel**
  
  Verify manually that the page elements match the color guidelines and there is strong contrast distinction.

- [ ] **Step 3: Commit style updates**
  
  ```bash
  git add frontend/src/App.jsx
  git commit -m "style: apply premium color scheme and strong contrast boundaries to dashboard components"
  ```
