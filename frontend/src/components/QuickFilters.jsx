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
import { useFlights } from '@/context/FlightsContext';

const QuickFilters = () => {
  const {
    maxPrice,
    setMaxPrice,
    maxPossiblePrice,
    destinationFilter,
    setDestinationFilter,
    selectedAirlines,
    setSelectedAirlines,
    selectedTripLengths,
    setSelectedTripLengths,
    availableDestinations,
    availableAirlines,
    availableTripLengths,
    handleResetFilters: onReset
  } = useFlights();

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
            max={maxPossiblePrice}
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
            renderInput={(params) => {
              const { inputProps, ...restParams } = params;
              return (
                <TextField
                  {...restParams}
                  placeholder="Anywhere"
                  inputProps={{
                    ...inputProps,
                    maxLength: 3,
                    className: "uppercase font-bold"
                  }}
                />
              );
            }}
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
              value.map((option, index) => {
                const { key, ...tagProps } = getTagProps({ index });
                return (
                  <Chip
                    key={key || option}
                    label={option}
                    size="small"
                    {...tagProps}
                  />
                );
              })
            }
          />
        </div>

        {/* Trip Length Multi-Select Autocomplete */}
        <div className="w-48 flex-shrink-0">
          <p className="text-sm font-medium text-text-secondary mb-1.5">
            Trip Length (Days)
          </p>
          <Autocomplete
            multiple
            size="small"
            options={availableTripLengths}
            getOptionLabel={(option) => `${option} days`}
            value={selectedTripLengths}
            onChange={(event, newValue) => {
              setSelectedTripLengths(newValue);
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                placeholder="Any Duration"
              />
            )}
            renderTags={(value, getTagProps) =>
              value.map((option, index) => {
                const { key, ...tagProps } = getTagProps({ index });
                return (
                  <Chip
                    key={key || option}
                    label={`${option}d`}
                    size="small"
                    {...tagProps}
                  />
                );
              })
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
            disabled={!(maxPrice < maxPossiblePrice || selectedAirlines.length > 0 || selectedTripLengths.length > 0 || destinationFilter)}
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
