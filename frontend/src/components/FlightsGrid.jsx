import React from 'react';
import {
  Box,
  Typography,
  Button,
  Chip
} from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';

const FlightsGrid = ({ flights, loading }) => {
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
          className="font-bold"
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
        <span className="text-success-green font-bold font-mono text-base">
          ${parseFloat(params.value).toFixed(2)}
        </span>
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
        <span className="text-sm">
          {params.value === 0 ? 'Nonstop' : `${params.value} stop${params.value > 1 ? 's' : ''}`}
        </span>
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
          endIcon={<OpenInNewIcon className="text-xs" />}
          className="text-[10px] py-1 px-3 rounded-md shadow-sm"
        >
          Book Flight
        </Button>
      )
    }
  ];

  return (
    <div className="flex-grow p-4 min-h-[450px] flex flex-col border-l-4 border-primary-blue shadow-md rounded-xl bg-white overflow-hidden">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold text-text-primary">
          Available Flight Listings
        </h2>
        <div className="bg-primary-blue/10 text-primary-blue text-xs font-bold px-3 py-1 rounded-full border border-primary-blue/20">
          {flights.length} match{flights.length !== 1 ? 'es' : ''}
        </div>
      </div>

      <div className="flex-grow w-full min-h-[400px]">
        <DataGrid
          rows={flights}
          columns={columns}
          loading={loading}
          pageSizeOptions={[5, 10, 20]}
          initialState={{
            pagination: {
              paginationModel: { pageSize: 10, page: 0 }
            }
          }}
          className="border-none"
          sx={{
            '& .MuiDataGrid-columnHeaders': {
              backgroundColor: '#f8fafc',
              borderBottom: '1px solid #e2e8f0',
            },
            '& .MuiDataGrid-cell': {
              borderBottom: '1px solid #f1f5f9',
            },
            '& .MuiDataGrid-row:hover': {
              backgroundColor: 'rgba(26, 115, 232, 0.04)',
            },
            '& .MuiDataGrid-footerContainer': {
              borderTop: '1px solid #e2e8f0',
            }
          }}
        />
      </div>
    </div>
  );
};

export default FlightsGrid;
