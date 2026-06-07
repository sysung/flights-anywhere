import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import QuickFilters from '../QuickFilters';

test('renders Quick Filters and triggers reset callback', () => {
  const handleReset = vi.fn();
  const handleSetMaxPrice = vi.fn();

  render(
    <QuickFilters
      maxPrice={500}
      setMaxPrice={handleSetMaxPrice}
      maxPossiblePrice={2000}
      destinationFilter="LAX"
      setDestinationFilter={vi.fn()}
      selectedAirlines={[]}
      setSelectedAirlines={vi.fn()}
      availableDestinations={['LAX', 'SFO', 'JFK']}
      availableAirlines={['United', 'Delta']}
      onReset={handleReset}
    />
  );

  // Check that the title and values render
  expect(screen.getByText(/Quick Filters/i)).toBeInTheDocument();
  expect(screen.getByText(/\$500/i)).toBeInTheDocument();

  // Test the reset button (it should be enabled since maxPrice < maxPossiblePrice)
  const clearButton = screen.getByRole('button', { name: /Clear Filters/i });
  expect(clearButton).not.toBeDisabled();
  fireEvent.click(clearButton);
  expect(handleReset).toHaveBeenCalled();
});
