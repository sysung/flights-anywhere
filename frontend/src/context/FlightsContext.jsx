import React, { createContext, useContext, useState, useEffect, useMemo, useRef } from 'react';

const FlightsContext = createContext();

export const useFlights = () => useContext(FlightsContext);

export const FlightsProvider = ({ children }) => {
  const [flights, setFlights] = useState([]);
  const [scraperStatus, setScraperStatus] = useState(null);
  const [loadingFlights, setLoadingFlights] = useState(false);
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'info' });
  const [maxPrice, setMaxPrice] = useState(2000);
  const [maxPossiblePrice, setMaxPossiblePrice] = useState(2000);
  const [selectedAirlines, setSelectedAirlines] = useState([]);
  const [destinationFilter, setDestinationFilter] = useState('');
  const [availableAirlines, setAvailableAirlines] = useState([]);
  const [availableDestinations, setAvailableDestinations] = useState([]);
  const isInitialLoad = useRef(true);

  const [chatMessages, setChatMessages] = useState([
    {
      sender: 'agent',
      text: "Hello! I am your SFO Anywhere flight assistant. Ask me anything, like 'Find me flights under $600 to London' or 'Show me JetBlue options', and I will automatically filter the results for you!"
    }
  ]);
  const [sendingChat, setSendingChat] = useState(false);

  const fetchFlights = async () => {
    setLoadingFlights(true);
    try {
      const response = await fetch('/api/flights');
      if (response.ok) {
        const data = await response.json();
        setFlights(data);
        const airlines = [...new Set(data.map(f => f.airline))].sort();
        setAvailableAirlines(airlines);
        const destinations = [...new Set(data.map(f => f.destination.toUpperCase()))].sort();
        setAvailableDestinations(destinations);
        
        if (data.length > 0) {
          const prices = data.map(f => parseFloat(f.price));
          const actualMax = Math.max(...prices);
          const roundedMax = Math.ceil(actualMax / 100) * 100;
          setMaxPossiblePrice(roundedMax);
          if (isInitialLoad.current) {
            setMaxPrice(roundedMax);
            isInitialLoad.current = false;
          }
        }
      }
    } catch (error) {
      console.error("Error fetching flights:", error);
    } finally {
      setLoadingFlights(false);
    }
  };

  const fetchScraperStatus = async () => {
    try {
      const response = await fetch('/api/scraper/status');
      if (response.ok) {
        const data = await response.json();
        if (data && data.length > 0) {
          setScraperStatus(data[0]);
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

  useEffect(() => {
    let interval;
    if (scraperStatus?.status === 'RUNNING') {
      interval = setInterval(() => {
        fetchScraperStatus();
        fetchFlights();
      }, 5000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [scraperStatus?.status]);

  const filteredFlights = useMemo(() => {
    return flights.filter(flight => {
      if (parseFloat(flight.price) > maxPrice) return false;
      if (selectedAirlines.length > 0 && !selectedAirlines.includes(flight.airline)) return false;
      if (destinationFilter && flight.destination.toUpperCase() !== destinationFilter.toUpperCase()) return false;
      return true;
    });
  }, [flights, maxPrice, selectedAirlines, destinationFilter]);

  const handleSendChat = async (userMsg) => {
    setChatMessages(prev => [...prev, { sender: 'user', text: userMsg }]);
    setSendingChat(true);
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg }),
      });
      if (response.ok) {
        const data = await response.json();
        setChatMessages(prev => [...prev, { sender: 'agent', text: data.response_text }]);
        if (data.filters) {
          const { max_price, airlines, destination } = data.filters;
          if (max_price !== undefined && max_price !== null) {
            setMaxPrice(parseFloat(max_price));
          }
          if (airlines && Array.isArray(airlines)) {
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
        setChatMessages(prev => [...prev, { sender: 'agent', text: "I experienced an error connecting to my flight assistant server. Please try again." }]);
      }
    } catch (err) {
      console.error("Chat error:", err);
      setChatMessages(prev => [...prev, { sender: 'agent', text: "Could not establish server connection. Is the API server running?" }]);
    } finally {
      setSendingChat(false);
    }
  };

  const handleResetFilters = () => {
    setMaxPrice(maxPossiblePrice);
    setSelectedAirlines([]);
    setDestinationFilter('');
  };

  const handleRunScraper = async () => {
    setScraperStatus(prev => ({ ...prev, status: 'RUNNING' }));
    setNotification({ open: true, message: 'Scraper job started in the background!', severity: 'success' });
    try {
      const response = await fetch('/api/scraper/run', { method: 'POST' });
      if (!response.ok) {
        setNotification({ open: true, message: 'Failed to trigger scraper.', severity: 'error' });
        fetchScraperStatus();
      }
    } catch (error) {
      console.error("Error triggering scraper:", error);
      setNotification({ open: true, message: 'Connection error while triggering scraper.', severity: 'error' });
      fetchScraperStatus();
    }
  };

  const handleCloseNotification = () => {
    setNotification(prev => ({ ...prev, open: false }));
  };

  return (
    <FlightsContext.Provider value={{
      flights,
      loadingFlights,
      filteredFlights,
      scraperStatus,
      notification,
      maxPrice,
      setMaxPrice,
      maxPossiblePrice,
      selectedAirlines,
      setSelectedAirlines,
      destinationFilter,
      setDestinationFilter,
      availableAirlines,
      availableDestinations,
      chatMessages,
      sendingChat,
      handleSendChat,
      handleResetFilters,
      handleRunScraper,
      handleCloseNotification
    }}>
      {children}
    </FlightsContext.Provider>
  );
};
