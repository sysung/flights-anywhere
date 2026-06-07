import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ChatbotPanel from '../ChatbotPanel';
import { useFlights } from '@/context/FlightsContext';

const mockSendMessage = vi.fn();
vi.mock('@/context/FlightsContext', () => ({
  useFlights: () => ({
    chatMessages: [{ sender: 'agent', text: 'Hello! How can I help you today?' }],
    handleSendChat: mockSendMessage,
    sendingChat: false,
    maxPrice: 2000,
    setMaxPrice: vi.fn(),
    destinationFilter: '',
    setDestinationFilter: vi.fn(),
    selectedAirlines: [],
    setSelectedAirlines: vi.fn()
  })
}));

test('submitting a prompt triggers handleSendChat callback from context', () => {
  render(<ChatbotPanel />);

  // Check assistant message is in the document
  expect(screen.getByText('Hello! How can I help you today?')).toBeInTheDocument();

  // Find input, enter query, and submit
  const input = screen.getByPlaceholderText(/Ask anything.../i);
  fireEvent.change(input, { target: { value: 'Flights to London under $800' } });
  
  const form = screen.getByPlaceholderText(/Ask anything.../i).closest('form');
  fireEvent.submit(form);

  // Check callback was triggered with the input query
  expect(mockSendMessage).toHaveBeenCalledWith('Flights to London under $800');
});
