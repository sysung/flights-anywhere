import React from 'react';
import { render, screen } from '@testing-library/react';
import FlightsGrid from '../FlightsGrid';

// Mock MUI DataGrid to avoid jsdom layout/rendering compatibility warnings
vi.mock('@mui/x-data-grid', () => ({
  DataGrid: ({ rows }) => (
    <div data-testid="mock-data-grid">
      {rows.map((row) => (
        <div key={row.id} data-testid="grid-row">
          {row.airline} to {row.destination} - ${row.price}
        </div>
      ))}
    </div>
  ),
}));

test('renders flights table and matched flights count', () => {
  const flights = [
    { id: 1, origin: 'SFO', destination: 'LAX', price: 150.00, airline: 'United', stops: 0 },
    { id: 2, origin: 'SFO', destination: 'JFK', price: 350.00, airline: 'Delta', stops: 1 }
  ];

  render(<FlightsGrid flights={flights} loading={false} />);

  // Check matching badge count
  expect(screen.getByText('2 matches')).toBeInTheDocument();

  // Check rows rendered via mock
  expect(screen.getByText('United to LAX - $150')).toBeInTheDocument();
  expect(screen.getByText('Delta to JFK - $350')).toBeInTheDocument();
});
