import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    primary: { main: "#176b63" },
    secondary: { main: "#d65a31" },
    background: {
      default: "#f7f7f2",
      paper: "#ffffff"
    },
    text: {
      primary: "#1d2b2a",
      secondary: "#5f6f6b"
    }
  },
  shape: {
    borderRadius: 8
  },
  typography: {
    fontFamily: "'Aptos', 'Segoe UI', sans-serif",
    h1: {
      fontSize: "2.25rem",
      fontWeight: 800,
      letterSpacing: 0
    },
    h2: {
      fontSize: "1.25rem",
      fontWeight: 800,
      letterSpacing: 0
    },
    button: {
      textTransform: "none",
      fontWeight: 700
    }
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 8 }
      }
    },
    MuiCard: {
      styleOverrides: {
        root: { borderRadius: 8 }
      }
    }
  }
});
