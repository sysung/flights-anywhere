import React from 'react';
import {
  Box,
  Typography,
  Slider,
  TextField,
  Button,
  Chip,
  Autocomplete
} from '@mui/material';
import FilterAltOffIcon from '@mui/icons-material/FilterAltOff';

const QuickFilters = ({
  maxPrice,
  setMaxPrice,
  destinationFilter,
  setDestinationFilter,
  selectedAirlines,
  setSelectedAirlines,
  availableDestinations,
  availableAirlines,
  onReset
}) => {
  return (
    <div className="bg-bg-slate p-6 border-l-4 border-slate-500 shadow-md rounded-xl flex flex-col gap-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-bold text-text-primary flex items-center gap-2">
          Quick Filters
        </h2>
      </div>
      
      <div className="flex items-end gap-6 flex-wrap">
        {/* Max Price Slider */}
        <div className="w-40 flex-shrink-0 mb-1">
          <p className="text-sm font-medium text-text-secondary mb-2">
            Max Price: <strong className="text-text-primary">${maxPrice}</strong>
          </p>
          <Slider
            value={maxPrice}
            onChange={(e, val) => setMaxPrice(val)}
            min={100}
            max={2000}
            step={50}
            valueLabelDisplay="auto"
            size="small"
          />
        </div>
        
        {/* Destination Code Autocomplete */}
        <div className="w-36 flex-shrink-0">
          <p className="text-sm font-medium text-text-secondary mb-1.5">
            Destination
          </p>
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
                  className: "uppercase font-bold"
                }}
              />
            )}
          />
        </div>

        {/* Airlines Multi-Select Autocomplete */}
        <div className="flex-grow min-w-[200px]">
          <p className="text-sm font-medium text-text-secondary mb-1.5">
            Airlines
          </p>
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
        </div>

        {/* Outlined Red Reset Button */}
        <div className="flex-shrink-0">
          <Button
            variant="outlined"
            color="error"
            startIcon={<FilterAltOffIcon />}
            onClick={onReset}
            disabled={!(maxPrice < 2000 || selectedAirlines.length > 0 || destinationFilter)}
            className="h-10 px-6 rounded-lg"
          >
            Clear Filters
          </Button>
        </div>
      </div>
    </div>
  );
};

export default QuickFilters;
