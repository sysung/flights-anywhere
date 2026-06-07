import React, { useState } from 'react';
import { 
  useMediaQuery, 
  useTheme, 
  Fab, 
  Drawer,
  Snackbar,
  Alert
} from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';

// Import Context
import { FlightsProvider, useFlights } from '@/context/FlightsContext';

// Import Components
import Header from './components/Header';
import QuickFilters from './components/QuickFilters';
import FlightsGrid from './components/FlightsGrid';
import ChatbotPanel from './components/ChatbotPanel';

function MainLayout() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [isChatOpen, setIsChatOpen] = useState(false);

  const {
    filteredFlights,
    loadingFlights,
    scraperStatus,
    notification,
    handleRunScraper,
    handleCloseNotification
  } = useFlights();

  return (
    <div className="flex flex-col h-screen bg-bg-light overflow-hidden">
      
      <Header 
        scraperStatus={scraperStatus} 
        onRefresh={handleRunScraper}
      />

      <main className="flex-grow flex overflow-hidden">
        {/* Main Content Area: Scrollable Left, Fixed Sidebar Right */}
        <div className="flex-grow flex w-full">
          
          {/* LEFT PANEL: Flights Table & Filters */}
          <section className="flex-grow h-full overflow-y-auto p-6 md:pr-3 flex flex-col gap-6 w-full md:w-[70%]">
            <QuickFilters />
            <FlightsGrid flights={filteredFlights} loading={loadingFlights} />
          </section>

          {/* RIGHT PANEL: AI Chatbot Panel (Visible on Desktop) */}
          {!isMobile && (
            <aside className="h-full p-6 pl-3 flex flex-col w-[30%]">
              <ChatbotPanel />
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
          isDrawer={true} 
          onClose={() => setIsChatOpen(false)} 
        />
      </Drawer>

      {/* Subtle Bottom-Right Notification */}
      <Snackbar 
        open={notification.open} 
        autoHideDuration={4000} 
        onClose={handleCloseNotification}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={handleCloseNotification} severity={notification.severity} variant="filled" sx={{ width: '100%', borderRadius: '12px' }}>
          {notification.message}
        </Alert>
      </Snackbar>
    </div>
  );
}

function App() {
  return (
    <FlightsProvider>
      <MainLayout />
    </FlightsProvider>
  );
}

export default App;
