import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Container,
  Grid,
  Typography,
  Paper,
  Slider,
  FormGroup,
  FormControlLabel,
  Checkbox,
  TextField,
  IconButton,
  Button,
  Chip,
  Avatar,
  Divider,
  CircularProgress,
  Tooltip,
  Badge,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  OutlinedInput,
  ListItemText,
  Autocomplete
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import SendIcon from '@mui/icons-material/Send';
import FlightTakeoffIcon from '@mui/icons-material/FlightTakeoff';
import FlightLandIcon from '@mui/icons-material/FlightLand';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import RefreshIcon from '@mui/icons-material/Refresh';
import FilterAltOffIcon from '@mui/icons-material/FilterAltOff';

function App() {
  // Flights and Scraper States
  const [flights, setFlights] = useState([]);
  const [scraperStatus, setScraperStatus] = useState(null);
  const [loadingFlights, setLoadingFlights] = useState(false);
  const [loadingScraper, setLoadingScraper] = useState(false);

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
  const [chatInput, setChatInput] = useState('');
  const [sendingChat, setSendingChat] = useState(false);
  
  const chatEndRef = useRef(null);

  // Scroll to bottom of chat
  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

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
    setLoadingScraper(true);
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
    } finally {
      setLoadingScraper(false);
    }
  };

  useEffect(() => {
    fetchFlights();
    fetchScraperStatus();
  }, []);

  // Filter local flights
  const filteredFlights = flights.filter(flight => {
    // 1. Max Price Filter
    if (parseFloat(flight.price) > maxPrice) return false;
    
    // 2. Airlines Filter
    if (selectedAirlines.length > 0 && !selectedAirlines.includes(flight.airline)) return false;
    
    // 3. Destination Filter
    if (destinationFilter && flight.destination.toUpperCase() !== destinationFilter.toUpperCase()) return false;
    
    return true;
  });

  // Handle Chat Submit
  const handleSendChat = async (e) => {
    if (e) e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = chatInput.trim();
    setChatInput('');
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

  // Status indicator colors
  const getStatusColor = (status) => {
    if (!status) return '#94a3b8';
    switch (status.toUpperCase()) {
      case 'SUCCESS': return '#137333'; // success green
      case 'RUNNING': return '#1a73e8'; // blue
      case 'FAILED': return '#dc2626'; // red
      default: return '#94a3b8';
    }
  };

  // DataGrid Columns Definition
  const columns = [
    { 
      field: 'destination', 
      headerName: 'To', 
      width: 100,
      renderCell: (params) => (
        <Chip 
          label={params.value} 
          color="primary" 
          variant="outlined" 
          size="small" 
          sx={{ fontWeight: 'bold' }} 
        />
      )
    },
    { 
      field: 'airline', 
      headerName: 'Airline', 
      width: 160 
    },
    { 
      field: 'price', 
      headerName: 'Price', 
      width: 120,
      renderCell: (params) => (
        <Typography sx={{ color: '#137333', fontWeight: 'bold', fontFamily: 'Roboto' }}>
          ${parseFloat(params.value).toFixed(2)}
        </Typography>
      )
    },
    { 
      field: 'departure_date', 
      headerName: 'Departure', 
      width: 130
    },
    { 
      field: 'return_date', 
      headerName: 'Return', 
      width: 130,
      renderCell: (params) => params.value || 'One way'
    },
    { 
      field: 'stops', 
      headerName: 'Stops', 
      width: 100,
      renderCell: (params) => (
        <Typography variant="body2">
          {params.value === 0 ? 'Nonstop' : `${params.value} stop${params.value > 1 ? 's' : ''}`}
        </Typography>
      )
    },
    { 
      field: 'duration_minutes', 
      headerName: 'Duration', 
      width: 120,
      renderCell: (params) => {
        if (!params.value) return 'Unknown';
        const hours = Math.floor(params.value / 60);
        const mins = params.value % 60;
        return `${hours}h ${mins}m`;
      }
    },
    {
      field: 'booking_url',
      headerName: 'Booking',
      width: 150,
      sortable: false,
      renderCell: (params) => (
        <Button
          variant="contained"
          size="small"
          color="primary"
          href={params.value}
          target="_blank"
          endIcon={<OpenInNewIcon sx={{ fontSize: 12 }} />}
          sx={{ fontSize: '0.75rem', py: 0.5 }}
        >
          Book Flight
        </Button>
      )
    }
  ];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', bgcolor: 'background.default' }}>
      
      {/* App Header Bar */}
      <Paper 
        square 
        elevation={2} 
        sx={{ 
          px: 3, 
          py: 2, 
          borderBottom: 1, 
          borderColor: 'divider', 
          background: 'rgba(255, 255, 255, 0.85)',
          backdropFilter: 'blur(10px)',
          position: 'sticky',
          top: 0,
          zIndex: 1100
        }}
      >
        <Grid container alignItems="center" justifyContent="space-between">
          <Grid item xs={12} sm={6} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <FlightTakeoffIcon sx={{ color: 'primary.main', fontSize: 32 }} />
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 'bold', color: 'text.primary', letterSpacing: -0.5 }}>
                SFO Anywhere Flights
              </Typography>
              <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                Real-time Flight Scraping & Intelligent AI Search Discovery
              </Typography>
            </Box>
          </Grid>
          
          <Grid item xs={12} sm={6} sx={{ display: 'flex', justifyContent: { xs: 'flex-start', sm: 'flex-end' }, mt: { xs: 1.5, sm: 0 }, alignItems: 'center', gap: 2 }}>
            {/* Scraper Status Badge */}
            {scraperStatus && (
              <Tooltip title={`Records Inserted: ${scraperStatus.records_inserted} | Updated: ${scraperStatus.records_updated}`}>
                <Paper 
                  variant="outlined" 
                  sx={{ 
                    px: 2, 
                    py: 0.5, 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: 1.5, 
                    borderColor: 'divider',
                    bgcolor: 'background.default',
                    borderRadius: '20px'
                  }}
                >
                  <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: getStatusColor(scraperStatus.status) }} />
                  <Box>
                    <Typography variant="caption" sx={{ fontWeight: 'bold', display: 'block', lineHeight: 1 }}>
                      Scraper: {scraperStatus.status}
                    </Typography>
                    <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>
                      Last run: {new Date(scraperStatus.started_at).toLocaleDateString()}
                    </Typography>
                  </Box>
                </Paper>
              </Tooltip>
            )}
            
            <IconButton onClick={() => { fetchFlights(); fetchScraperStatus(); }} color="primary" size="small" disabled={loadingFlights}>
              <RefreshIcon />
            </IconButton>
          </Grid>
        </Grid>
      </Paper>

      {/* Main Split-Pane Workspace */}
      <Box sx={{ flexGrow: 1, px: 3, py: 2, display: 'flex', flexDirection: 'column', width: '100%' }}>
        <Grid container spacing={3} sx={{ flexGrow: 1 }}>
          
          {/* LEFT PANEL: Flights Table & Filters (70% width) */}
          <Grid item xs={12} md={8.4} sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            
            {/* Quick Filters Card */}
            <Paper 
              sx={{ 
                p: 2.5,
                borderTop: '4px solid #64748b', // Slate grey top border
                boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05)'
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 1 }}>
                  Quick Filters
                </Typography>
              </Box>
              
              <Box sx={{ display: 'flex', alignItems: 'flex-end', gap: 3, flexWrap: 'wrap' }}>
                {/* Max Price Slider */}
                <Box sx={{ width: 160, flexShrink: 0, mb: 0.5 }}>
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
                    sx={{ py: 1 }}
                  />
                </Box>
                
                {/* Destination Code Autocomplete */}
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

                {/* Airlines Multi-Select Autocomplete */}
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

                {/* Outlined Red Reset Button */}
                <Box sx={{ flexShrink: 0 }}>
                  <Button
                    variant="outlined"
                    color="error"
                    startIcon={<FilterAltOffIcon />}
                    onClick={handleResetFilters}
                    disabled={!(maxPrice < 2000 || selectedAirlines.length > 0 || destinationFilter)}
                    sx={{ height: 40 }}
                  >
                    Clear Filters
                  </Button>
                </Box>
              </Box>
            </Paper>

            {/* Flights Grid Results Container */}
            <Paper 
              sx={{ 
                flexGrow: 1, 
                p: 2, 
                minHeight: '450px', 
                display: 'flex', 
                flexDirection: 'column',
                borderTop: '4px solid #1a73e8', // Primary Blue top border
                boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05)'
              }}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                  Available Flight Listings
                </Typography>
                <Chip 
                  label={`${filteredFlights.length} match${filteredFlights.length !== 1 ? 'es' : ''}`} 
                  color="primary" 
                  size="small" 
                  sx={{ fontWeight: 'bold' }}
                />
              </Box>

              <Box sx={{ flexGrow: 1, width: '100%' }}>
                <DataGrid
                  rows={filteredFlights}
                  columns={columns}
                  loading={loadingFlights}
                  pageSizeOptions={[5, 10, 20]}
                  initialState={{
                    pagination: {
                      paginationModel: { pageSize: 10, page: 0 }
                    }
                  }}
                  autoHeight
                  sx={{
                    borderColor: 'divider',
                    '& .MuiDataGrid-columnHeaders': {
                      backgroundColor: 'background.default',
                      borderBottom: 1,
                      borderColor: 'divider',
                    },
                    '& .MuiDataGrid-row:hover': {
                      backgroundColor: 'rgba(26, 115, 232, 0.04)',
                    },
                    '& .MuiDataGrid-cell': {
                      borderColor: 'divider',
                    }
                  }}
                />
              </Box>
            </Paper>
          </Grid>

          {/* RIGHT PANEL: AI Chatbot Panel (30% width) */}
          <Grid item xs={12} md={3.6} sx={{ display: 'flex', flexDirection: 'column' }}>
            <Paper 
              sx={{ 
                display: 'flex', 
                flexDirection: 'column', 
                position: 'sticky',
                top: '90px',
                height: 'calc(100vh - 120px)', 
                overflow: 'hidden',
                border: '1px solid #ddd6fe', // Purple borders
                boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.05), 0 4px 6px -4px rgb(0 0 0 / 0.05)'
              }}
            >
              
              {/* Chat Title Header */}
              <Box 
                sx={{ 
                  p: 2.2, 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: 1.5, 
                  background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)', // Violet-to-Purple premium gradient
                  color: '#ffffff' 
                }}
              >
                <SmartToyIcon />
                <Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 'bold', lineHeight: 1.2 }}>
                    AI Flight Assistant
                  </Typography>
                  <Typography variant="caption" sx={{ opacity: 0.85 }}>
                    Gemini-powered natural language queries
                  </Typography>
                </Box>
              </Box>
              
              {/* Chat Messages Feed */}
              <Box sx={{ flexGrow: 1, p: 2, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2, bgcolor: '#f5f3ff' }}> {/* Lavender tint background */}
                {chatMessages.map((msg, index) => {
                  const isAgent = msg.sender === 'agent';
                  return (
                    <Box 
                      key={index} 
                      sx={{ 
                        display: 'flex', 
                        justifyContent: isAgent ? 'flex-start' : 'flex-end',
                        width: '100%' 
                      }}
                    >
                      <Box sx={{ display: 'flex', gap: 1, maxWidth: '85%', flexDirection: isAgent ? 'row' : 'row-reverse' }}>
                        <Avatar sx={{ width: 28, height: 28, bgcolor: isAgent ? '#7c3aed' : '#475569' }}>
                          {isAgent ? <SmartToyIcon sx={{ fontSize: 16 }} /> : <PersonIcon sx={{ fontSize: 16 }} />}
                        </Avatar>
                        <Paper 
                          sx={{ 
                            p: 1.5, 
                            bgcolor: isAgent ? '#ffffff' : '#4f46e5',
                            color: isAgent ? '#0f172a' : '#ffffff',
                            borderRadius: isAgent ? '4px 16px 16px 16px' : '16px 4px 16px 16px',
                            border: isAgent ? '1px solid #e9d5ff' : 'none',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.03)'
                          }}
                        >
                          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.4 }}>
                            {msg.text}
                          </Typography>
                        </Paper>
                      </Box>
                    </Box>
                  );
                })}
                {sendingChat && (
                  <Box sx={{ display: 'flex', gap: 1, maxWidth: '85%' }}>
                    <Avatar sx={{ width: 28, height: 28, bgcolor: '#7c3aed' }}>
                      <SmartToyIcon sx={{ fontSize: 16 }} />
                    </Avatar>
                    <Paper sx={{ p: 1.5, borderRadius: '4px 16px 16px 16px', display: 'flex', alignItems: 'center', gap: 1, border: '1px solid #e9d5ff' }}>
                      <CircularProgress size={16} color="secondary" />
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>Thinking...</Typography>
                    </Paper>
                  </Box>
                )}
                <div ref={chatEndRef} />
              </Box>

              <Divider />

              {/* Dynamic Synchronized Chips Bar */}
              {(maxPrice < 2000 || selectedAirlines.length > 0 || destinationFilter) && (
                <Box sx={{ px: 2, py: 1.2, display: 'flex', flexWrap: 'wrap', gap: 1, bgcolor: 'background.paper' }}>
                  <Typography variant="caption" sx={{ width: '100%', color: 'text.secondary', fontWeight: 'bold' }}>
                    Active AI Search Filters:
                  </Typography>
                  {maxPrice < 2000 && (
                    <Chip 
                      label={`Price < $${maxPrice}`} 
                      onDelete={() => setMaxPrice(2000)}
                      size="small" 
                      color="primary"
                      variant="outlined"
                    />
                  )}
                  {destinationFilter && (
                    <Chip 
                      label={`To: ${destinationFilter}`} 
                      onDelete={() => setDestinationFilter('')}
                      size="small" 
                      color="primary"
                      variant="outlined"
                    />
                  )}
                  {selectedAirlines.map(airline => (
                    <Chip 
                      key={airline}
                      label={airline} 
                      onDelete={() => setSelectedAirlines(prev => prev.filter(a => a !== airline))}
                      size="small" 
                      color="primary"
                      variant="outlined"
                    />
                  ))}
                </Box>
              )}

              {/* Chat Input Area */}
              <Box 
                component="form" 
                onSubmit={handleSendChat}
                sx={{ 
                  p: 2, 
                  display: 'flex', 
                  gap: 1, 
                  bgcolor: 'background.paper',
                  borderTop: 1,
                  borderColor: 'divider'
                }}
              >
                <TextField
                  placeholder="Ask agent, e.g. 'flights under $700'..."
                  variant="outlined"
                  size="small"
                  fullWidth
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  disabled={sendingChat}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      borderRadius: '24px',
                    }
                  }}
                />
                <IconButton 
                  color="primary" 
                  type="submit" 
                  disabled={!chatInput.trim() || sendingChat}
                  sx={{ bgcolor: 'primary.main', color: '#ffffff', '&:hover': { bgcolor: 'primary.dark' }, p: 1 }}
                >
                  <SendIcon sx={{ fontSize: 18 }} />
                </IconButton>
              </Box>

            </Paper>
          </Grid>
          
        </Grid>
      </Box>
    </Box>
  );
}

export default App;
