import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import QuickFilters from '../QuickFilters';
import { useFlights } from '@/context/FlightsContext';

// Mock the context hook
const mockReset = vi.fn();
vi.mock('@/context/FlightsContext', () => ({
  useFlights: () => ({
    maxPrice: 500,
    setMaxPrice: vi.fn(),
    maxPossiblePrice: 2000,
    destinationFilter: 'LAX',
    setDestinationFilter: vi.fn(),
    selectedAirlines: [],
    setSelectedAirlines: vi.fn(),
    availableDestinations: ['LAX', 'SFO', 'JFK'],
    availableAirlines: ['United', 'Delta'],
    handleResetFilters: mockReset
  })
}));

test('renders Quick Filters and triggers reset callback from context', () => {
  render(<QuickFilters />);

  // Check that the title and values render
  expect(screen.getByText(/Quick Filters/i)).toBeInTheDocument();
  expect(screen.getByText(/\$500/i)).toBeInTheDocument();

  // Test the reset button
  const clearButton = screen.getByRole('button', { name: /Clear Filters/i });
  expect(clearButton).not.toBeDisabled();
  fireEvent.click(clearButton);
  expect(mockReset).toHaveBeenCalled();
});
