import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ChatbotPanel from '../ChatbotPanel';

test('submitting a prompt triggers onSendMessage callback', () => {
  const handleSendMessage = vi.fn();
  const messages = [
    { sender: 'agent', text: 'Hello! How can I help you today?' }
  ];

  render(
    <ChatbotPanel
      messages={messages}
      onSendMessage={handleSendMessage}
      sending={false}
      maxPrice={2000}
      setMaxPrice={vi.fn()}
      destinationFilter=""
      setDestinationFilter={vi.fn()}
      selectedAirlines={[]}
      setSelectedAirlines={vi.fn()}
    />
  );

  // Check assistant message is in the document
  expect(screen.getByText('Hello! How can I help you today?')).toBeInTheDocument();

  // Find input, enter query, and submit
  const input = screen.getByPlaceholderText(/Ask anything.../i);
  fireEvent.change(input, { target: { value: 'Flights to London under $800' } });
  
  const form = screen.getByPlaceholderText(/Ask anything.../i).closest('form');
  fireEvent.submit(form);

  // Check callback was triggered with the input query
  expect(handleSendMessage).toHaveBeenCalledWith('Flights to London under $800');
});
