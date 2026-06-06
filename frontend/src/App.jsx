import React, { useState, useEffect, useMemo } from 'react';
import { 
  Box, 
  Grid, 
  useMediaQuery, 
  useTheme, 
  Fab, 
  Drawer 
} from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';

// Import Components
import Header from './components/Header';
import QuickFilters from './components/QuickFilters';
import FlightsGrid from './components/FlightsGrid';
import ChatbotPanel from './components/ChatbotPanel';

function App() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  
  // Flights and Scraper States
  const [flights, setFlights] = useState([]);
  const [scraperStatus, setScraperStatus] = useState(null);
  const [loadingFlights, setLoadingFlights] = useState(false);

  // Filter States (synchronized between Chat and Quick Filters)
  const [maxPrice, setMaxPrice] = useState(2000);
  const [selectedAirlines, setSelectedAirlines] = useState([]);
  const [destinationFilter, setDestinationFilter] = useState('');
  
  // Available list options for filters
  const [availableAirlines, setAvailableAirlines] = useState([]);
  const [availableDestinations, setAvailableDestinations] = useState([]);

  // Chatbot States
  const [chatMessages, setChatMessages] = useState([
    {
      sender: 'agent',
      text: "Hello! I am your SFO Anywhere flight assistant. Ask me anything, like 'Find me flights under $600 to London' or 'Show me JetBlue options', and I will automatically filter the results for you!"
    }
  ]);
  const [sendingChat, setSendingChat] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);

  // Fetch Flights
  const fetchFlights = async () => {
    setLoadingFlights(true);
    try {
      const response = await fetch('/api/flights');
      if (response.ok) {
        const data = await response.json();
        setFlights(data);
        
        // Extract unique airlines from active flights
        const airlines = [...new Set(data.map(f => f.airline))].sort();
        setAvailableAirlines(airlines);

        // Extract unique destinations from active flights
        const destinations = [...new Set(data.map(f => f.destination.toUpperCase()))].sort();
        setAvailableDestinations(destinations);
        
        // Set maximum price slider range dynamically based on flights if possible
        if (data.length > 0) {
          const prices = data.map(f => parseFloat(f.price));
          const maxVal = Math.max(...prices);
          setMaxPrice(Math.ceil(maxVal / 100) * 100);
        }
      }
    } catch (error) {
      console.error("Error fetching flights:", error);
    } finally {
      setLoadingFlights(false);
    }
  };

  // Fetch Scraper Status
  const fetchScraperStatus = async () => {
    try {
      const response = await fetch('/api/scraper/status');
      if (response.ok) {
        const data = await response.json();
        if (data && data.length > 0) {
          setScraperStatus(data[0]); // Get latest log
        }
      }
    } catch (error) {
      console.error("Error fetching scraper status:", error);
    }
  };

  useEffect(() => {
    fetchFlights();
    fetchScraperStatus();
  }, []);

  // Filter local flights
  const filteredFlights = useMemo(() => {
    return flights.filter(flight => {
      // 1. Max Price Filter
      if (parseFloat(flight.price) > maxPrice) return false;
      
      // 2. Airlines Filter
      if (selectedAirlines.length > 0 && !selectedAirlines.includes(flight.airline)) return false;
      
      // 3. Destination Filter
      if (destinationFilter && flight.destination.toUpperCase() !== destinationFilter.toUpperCase()) return false;
      
      return true;
    });
  }, [flights, maxPrice, selectedAirlines, destinationFilter]);

  // Handle Chat Submit
  const handleSendChat = async (userMsg) => {
    setChatMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
    setSendingChat(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: userMsg }),
      });

      if (response.ok) {
        const data = await response.json();
        
        setChatMessages(prev => [...prev, { 
          sender: 'agent', 
          text: data.response_text 
        }]);

        // Process synchronized filters returned by the agent
        if (data.filters) {
          const { max_price, airlines, destination } = data.filters;
          
          if (max_price !== undefined && max_price !== null) {
            setMaxPrice(parseFloat(max_price));
          }
          if (airlines && Array.isArray(airlines)) {
            // Find matched airlines from available list to prevent exact casing mismatch
            const matched = availableAirlines.filter(avail => 
              airlines.some(req => avail.toLowerCase().includes(req.toLowerCase()))
            );
            setSelectedAirlines(matched.length > 0 ? matched : airlines);
          }
          if (destination) {
            setDestinationFilter(destination.toUpperCase());
          }
        }
      } else {
        setChatMessages(prev => [...prev, { 
          sender: 'agent', 
          text: "I experienced an error connecting to my flight search assistant server. Please try again." 
        }]);
      }
    } catch (err) {
      console.error("Chat error:", err);
      setChatMessages(prev => [...prev, { 
        sender: 'agent', 
        text: "Could not establish server connection. Is the API server running?" 
      }]);
    } finally {
      setSendingChat(false);
    }
  };

  // Reset all filters
  const handleResetFilters = () => {
    setMaxPrice(2000);
    setSelectedAirlines([]);
    setDestinationFilter('');
  };

  const chatbotProps = {
    messages: chatMessages,
    onSendMessage: handleSendChat,
    sending: sendingChat,
    maxPrice,
    setMaxPrice,
    destinationFilter,
    setDestinationFilter,
    selectedAirlines,
    setSelectedAirlines
  };

  return (
    <div className="flex flex-col h-screen bg-bg-light overflow-hidden">
      
      <Header 
        scraperStatus={scraperStatus} 
        loadingFlights={loadingFlights} 
        onRefresh={() => { fetchFlights(); fetchScraperStatus(); }} 
      />

      <main className="flex-grow flex overflow-hidden">
        {/* Main Content Area: Scrollable Left, Fixed Sidebar Right */}
        <div className="flex-grow flex w-full">
          
          {/* LEFT PANEL: Flights Table & Filters */}
          <section className="flex-grow h-full overflow-y-auto p-6 md:pr-3 flex flex-col gap-6 w-full md:w-[70%]">
            
            <QuickFilters 
              maxPrice={maxPrice}
              setMaxPrice={setMaxPrice}
              destinationFilter={destinationFilter}
              setDestinationFilter={setDestinationFilter}
              selectedAirlines={selectedAirlines}
              setSelectedAirlines={setSelectedAirlines}
              availableDestinations={availableDestinations}
              availableAirlines={availableAirlines}
              onReset={handleResetFilters}
            />

            <FlightsGrid 
              flights={filteredFlights} 
              loading={loadingFlights} 
            />

          </section>

          {/* RIGHT PANEL: AI Chatbot Panel (Visible on Desktop) */}
          {!isMobile && (
            <aside className="h-full p-6 pl-3 flex flex-col w-[30%]">
              <ChatbotPanel {...chatbotProps} />
            </aside>
          )}
          
        </div>
      </main>

      {/* Floating Action Button for Mobile Chat */}
      {isMobile && (
        <Fab 
          color="primary" 
          aria-label="chat" 
          sx={{ position: 'fixed', bottom: 24, right: 24, zIndex: 2000 }}
          onClick={() => setIsChatOpen(true)}
        >
          <SmartToyIcon />
        </Fab>
      )}

      {/* Drawer for Mobile Chat */}
      <Drawer
        anchor="right"
        open={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        sx={{ zIndex: 2100 }}
      >
        <ChatbotPanel 
          {...chatbotProps} 
          isDrawer={true} 
          onClose={() => setIsChatOpen(false)} 
        />
      </Drawer>
    </div>
  );
}

export default App;
