import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1a73e8', // Primary Blue
      contrastText: '#ffffff',
    },
    success: {
      main: '#137333', // Success Green
      contrastText: '#ffffff',
    },
    background: {
      default: '#f8fafc', // Bg Light
      paper: '#ffffff', // Surface White
    },
    text: {
      primary: '#0f172a', // Text Primary
      secondary: '#475569', // Text Secondary
    },
    divider: '#e2e8f0', // Border Slate
  },
  typography: {
    fontFamily: [
      'Inter',
      'Roboto',
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Arial',
      'sans-serif',
    ].join(','),
    h1: {
      fontFamily: 'Inter',
      fontWeight: 700,
    },
    h2: {
      fontFamily: 'Inter',
      fontWeight: 700,
    },
    h3: {
      fontFamily: 'Inter',
      fontWeight: 600,
    },
    h4: {
      fontFamily: 'Inter',
      fontWeight: 600,
    },
    h5: {
      fontFamily: 'Inter',
      fontWeight: 600,
    },
    h6: {
      fontFamily: 'Inter',
      fontWeight: 600,
    },
    body1: {
      fontFamily: 'Inter',
      fontSize: '0.925rem',
    },
    body2: {
      fontFamily: 'Inter',
      fontSize: '0.85rem',
    },
    button: {
      fontFamily: 'Inter',
      fontWeight: 600,
      textTransform: 'none',
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
          padding: '6px 16px',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: '12px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.1)',
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
        },
      },
    },
  },
});

export default theme;
