import React from 'react';
import {
  Box,
  Typography,
  IconButton,
  Tooltip
} from '@mui/material';
import FlightTakeoffIcon from '@mui/icons-material/FlightTakeoff';
import RefreshIcon from '@mui/icons-material/Refresh';

const Header = ({ scraperStatus, loadingFlights, onRefresh }) => {
  const getStatusColor = (status) => {
    if (!status) return 'bg-slate-400';
    switch (status.toUpperCase()) {
      case 'SUCCESS': return 'bg-success-green';
      case 'RUNNING': return 'bg-primary-blue';
      case 'FAILED': return 'bg-red-600';
      default: return 'bg-slate-400';
    }
  };

  return (
    <header className="sticky top-0 z-[1100] px-6 py-4 border-b border-border-slate bg-white/85 backdrop-blur-md shadow-sm">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 sm:gap-0">
        <div className="flex items-center gap-4">
          <FlightTakeoffIcon className="text-primary-blue text-4xl" sx={{ fontSize: 32 }} />
          <div>
            <h1 className="text-2xl font-bold text-text-primary tracking-tight leading-tight">
              SFO Anywhere Flights
            </h1>
            <p className="text-xs text-text-secondary">
              Real-time Flight Scraping & Intelligent AI Search Discovery
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-6 self-end sm:self-auto">
          {/* Scraper Status Badge */}
          {scraperStatus && (
            <Tooltip title={`Records Inserted: ${scraperStatus.records_inserted} | Updated: ${scraperStatus.records_updated}`}>
              <div className="px-4 py-1.5 flex items-center gap-3 border border-border-slate bg-bg-light rounded-full shadow-sm">
                <div className={`w-2 h-2 rounded-full ${getStatusColor(scraperStatus.status)}`} />
                <div>
                  <span className="text-[10px] font-bold block uppercase tracking-wider text-text-primary leading-none">
                    Scraper: {scraperStatus.status}
                  </span>
                  <span className="text-[9px] text-text-secondary">
                    Last run: {new Date(scraperStatus.started_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                  </span>
                </div>
              </div>
            </Tooltip>
          )}
          
          <IconButton 
            onClick={onRefresh} 
            color="primary" 
            size="small" 
            disabled={loadingFlights}
            className="hover:bg-blue-50 transition-colors"
          >
            <RefreshIcon />
          </IconButton>
        </div>
      </div>
    </header>
  );
};

export default Header;
