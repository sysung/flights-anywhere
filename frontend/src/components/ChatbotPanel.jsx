import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  IconButton,
  Avatar,
  CircularProgress,
  Chip
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import CloseIcon from '@mui/icons-material/Close';

const ChatbotPanel = ({
  messages,
  onSendMessage,
  sending,
  maxPrice,
  setMaxPrice,
  destinationFilter,
  setDestinationFilter,
  selectedAirlines,
  setSelectedAirlines,
  isDrawer = false,
  onClose
}) => {
  const [input, setInput] = useState('');
  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!input.trim() || sending) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const containerClassName = isDrawer 
    ? "flex flex-col h-full w-full sm:w-[400px] overflow-hidden bg-white shadow-2xl"
    : "flex flex-col h-full overflow-hidden border border-blue-100 shadow-xl rounded-2xl bg-white";

  return (
    <div className={containerClassName}>
      
      {/* Chat Title Header */}
      <div className="p-5 flex items-center justify-between bg-gradient-to-br from-primary-blue to-blue-800 text-white shadow-md">
        <div className="flex items-center gap-3">
          <SmartToyIcon className="text-blue-100" />
          <div>
            <h3 className="text-sm font-bold leading-tight tracking-wide">
              AI Flight Assistant
            </h3>
            <p className="text-[10px] text-blue-100/80 font-medium">
              Gemini-powered natural language queries
            </p>
          </div>
        </div>
        {isDrawer && (
          <IconButton onClick={onClose} size="small" className="text-white hover:bg-white/20 transition-colors">
            <CloseIcon fontSize="small" />
          </IconButton>
        )}
      </div>
      
      {/* Chat Messages Feed */}
      <div className="flex-grow p-5 overflow-y-auto flex flex-col gap-4 bg-blue-50/30">
        {messages.map((msg, index) => {
          const isAgent = msg.sender === 'agent';
          return (
            <div 
              key={index} 
              className={`flex w-full ${isAgent ? 'justify-start' : 'justify-end'}`}
            >
              <div className={`flex gap-3 max-w-[85%] ${isAgent ? 'flex-row' : 'flex-row-reverse'}`}>
                <Avatar 
                  className={`w-7 h-7 shadow-sm ${isAgent ? 'bg-primary-blue' : 'bg-slate-600'}`}
                  sx={{ width: 28, height: 28 }}
                >
                  {isAgent ? <SmartToyIcon sx={{ fontSize: 16 }} /> : <PersonIcon sx={{ fontSize: 16 }} />}
                </Avatar>
                <div 
                  className={`p-3.5 text-sm leading-relaxed shadow-sm ring-1 ring-black/5 ${
                    isAgent 
                      ? 'bg-white text-slate-800 rounded-2xl rounded-tl-none' 
                      : 'bg-primary-blue text-white rounded-2xl rounded-tr-none'
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            </div>
          );
        })}
        {sending && (
          <div className="flex gap-3 max-w-[85%] animate-pulse">
            <Avatar className="w-7 h-7 bg-primary-blue shadow-sm" sx={{ width: 28, height: 28 }}>
              <SmartToyIcon sx={{ fontSize: 16 }} />
            </Avatar>
            <div className="p-3.5 bg-white rounded-2xl rounded-tl-none flex items-center gap-3 ring-1 ring-black/5 shadow-sm">
              <CircularProgress size={14} className="text-primary-blue" thickness={6} />
              <span className="text-xs font-semibold text-slate-400 italic">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Dynamic Synchronized Chips Bar */}
      {(maxPrice < 2000 || selectedAirlines.length > 0 || destinationFilter) && (
        <div className="px-4 py-3 flex flex-wrap gap-2 bg-white border-t border-slate-100">
          <p className="w-full text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">
            Active Search Filters:
          </p>
          {maxPrice < 2000 && (
            <Chip 
              label={`< $${maxPrice}`} 
              onDelete={() => setMaxPrice(2000)}
              size="small" 
              color="primary"
              variant="outlined"
              className="bg-blue-50/50"
            />
          )}
          {destinationFilter && (
            <Chip 
              label={`To: ${destinationFilter}`} 
              onDelete={() => setDestinationFilter('')}
              size="small" 
              color="primary"
              variant="outlined"
              className="bg-blue-50/50"
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
              className="bg-blue-50/50"
            />
          ))}
        </div>
      )}

      {/* Chat Input Area */}
      <form 
        onSubmit={handleSubmit}
        className="p-4 bg-white border-t border-slate-100 flex gap-2 items-center"
      >
        <TextField
          placeholder="Ask anything..."
          variant="outlined"
          size="small"
          fullWidth
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={sending}
          slotProps={{
            input: {
              className: "bg-slate-50/50 rounded-full text-sm py-1"
            }
          }}
          sx={{ '& .MuiOutlinedInput-root': { borderRadius: '9999px' } }}
        />
        <IconButton 
          color="primary" 
          type="submit" 
          disabled={!input.trim() || sending}
          className="bg-primary-blue text-white hover:bg-blue-700 disabled:bg-slate-100 disabled:text-slate-400 shadow-md p-2 transition-all"
        >
          <SendIcon fontSize="small" />
        </IconButton>
      </form>

    </div>
  );
};

export default ChatbotPanel;
