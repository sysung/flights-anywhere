import { useState } from "react";
import {
  Alert,
  AppBar,
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Chip,
  CircularProgress,
  Container,
  Drawer,
  Fab,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  MenuItem,
  OutlinedInput,
  Select,
  Slider,
  Stack,
  TextField,
  Toolbar,
  Typography,
  useMediaQuery
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import ChatBubbleOutlineIcon from "@mui/icons-material/ChatBubbleOutline";
import CloseIcon from "@mui/icons-material/Close";
import FilterListIcon from "@mui/icons-material/FilterList";
import FlightTakeoffIcon from "@mui/icons-material/FlightTakeoff";
import FavoriteBorderIcon from "@mui/icons-material/FavoriteBorder";
import SearchIcon from "@mui/icons-material/Search";
import TravelExploreIcon from "@mui/icons-material/TravelExplore";
import { recommendTravel, searchFlights } from "./api";
import { ActiveFilterChip, defaultFilters, FlightSearchResponse, Recommendation, TravelFilters } from "./types";

const climates = ["sunny", "warm", "tropical", "mild", "snowy", "not_rainy"];
const vibes = ["beaches", "food", "nightlife", "nature", "culture", "family", "romantic", "adventure", "temples", "museums", "budget"];

interface ChatMessage {
  role: "assistant" | "user";
  text: string;
}

interface FlightSearchState {
  destination: string;
  loading: boolean;
  error: string | null;
  response: FlightSearchResponse | null;
}

function chipLabel(chip: ActiveFilterChip): string {
  return `${chip.label}: ${chip.value}`;
}

function flexibleWindowLabel(value?: string | null): string {
  if (value === "next_month") return "Next month";
  if (value === "next_6_months") return "Next 6 months";
  return "Next 3 months";
}

function sourceFor(key: string, activeFilters: ActiveFilterChip[]): ActiveFilterChip["source"] {
  return activeFilters.find((chip) => chip.key === key)?.source || "user";
}

function activeChipsFromFilters(filters: TravelFilters, activeFilters: ActiveFilterChip[]): ActiveFilterChip[] {
  const chips: ActiveFilterChip[] = [];
  const push = (key: string, label: string, value: string) => {
    if (value) chips.push({ key, label, value, source: sourceFor(key, activeFilters) });
  };

  push("origin", "From", filters.origin || "");
  push("destination", "To", filters.destination || "Anywhere");
  if (filters.date_mode === "flexible") {
    push("date_mode", "Dates", "Flexible");
    push("flexible_window", "Window", flexibleWindowLabel(filters.flexible_window));
  } else {
    push("outbound_date", "Depart", filters.outbound_date || "");
    push("return_date", "Return", filters.return_date || "");
  }
  if (filters.trip_length_days) push("trip_length_days", "Length", `${filters.trip_length_days} days`);
  if (filters.budget_max) push("budget_max", "Budget", `$${filters.budget_max}`);
  if (filters.nonstop === true) push("nonstop", "Stops", "Nonstop");
  if (filters.nonstop === false) push("nonstop", "Stops", "One stop ok");
  if (filters.max_flight_duration_minutes) push("max_flight_duration_minutes", "Max flight", `${filters.max_flight_duration_minutes} min`);
  if (filters.domestic_international !== "any") push("domestic_international", "Region", filters.domestic_international);
  if (filters.climates.length) push("climates", "Climate", filters.climates.join(", "));
  if (filters.vibes.length) push("vibes", "Interests", filters.vibes.join(", "));
  if (filters.sort !== "best_match") push("sort", "Sort", filters.sort.replace("_", " "));
  return chips;
}

function formatDuration(minutes?: number | null): string {
  if (!minutes) return "Duration unavailable";
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return mins ? `${hours}h ${mins}m` : `${hours}h`;
}

function stopsLabel(stops?: number | null): string {
  if (stops === 0) return "Nonstop";
  if (stops === 1) return "1 stop";
  if (typeof stops === "number") return `${stops} stops`;
  return "Stops unavailable";
}

export default function App() {
  const theme = useTheme();
  const desktopChat = useMediaQuery(theme.breakpoints.up("lg"));
  const [filters, setFilters] = useState<TravelFilters>(defaultFilters);
  const [activeFilters, setActiveFilters] = useState<ActiveFilterChip[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", text: "Where to next? Tell me a vibe, a budget, or ask me to surprise you." }
  ]);
  const [message, setMessage] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [flightSearch, setFlightSearch] = useState<FlightSearchState | null>(null);

  async function submitChat(text = message) {
    const trimmed = text.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    setMessages((items) => [...items, { role: "user", text: trimmed }]);
    setMessage("");
    try {
      const response = await recommendTravel(trimmed, filters);
      setFilters(response.applied_filters);
      setActiveFilters(response.active_filters);
      setRecommendations(response.recommendations);
      setFlightSearch(null);
      setMessages((items) => [...items, { role: "assistant", text: response.assistant_message }]);
    } catch (err) {
      const text = err instanceof Error ? err.message : "Something went wrong.";
      setError(text);
      setMessages((items) => [...items, { role: "assistant", text: "I could not complete that search yet. Try broader dates or fewer filters." }]);
    } finally {
      setLoading(false);
    }
  }

  function updateFilter<K extends keyof TravelFilters>(key: K, value: TravelFilters[K]) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function toggleListValue(key: "climates" | "vibes", value: string) {
    setFilters((current) => {
      const existing = current[key];
      return { ...current, [key]: existing.includes(value) ? existing.filter((item) => item !== value) : [...existing, value] };
    });
  }

  function removeChip(key: string) {
    setActiveFilters((current) => current.filter((chip) => chip.key !== key));
    setFilters((current) => {
      const next = { ...current };
      if (key === "origin") next.origin = null;
      else if (key === "destination") next.destination = null;
      else if (key === "date_mode") next.date_mode = "exact";
      else if (key === "outbound_date") next.outbound_date = "";
      else if (key === "return_date") next.return_date = "";
      else if (key === "trip_length_days") next.trip_length_days = null;
      else if (key === "flexible_window") next.flexible_window = "next_3_months";
      else if (key === "budget_max") next.budget_max = null;
      else if (key === "nonstop") next.nonstop = null;
      else if (key === "max_flight_duration_minutes") next.max_flight_duration_minutes = null;
      else if (key === "domestic_international") next.domestic_international = "any";
      else if (key === "climates") next.climates = [];
      else if (key === "vibes") next.vibes = [];
      else if (key === "sort") next.sort = "best_match";
      return next;
    });
  }

  async function showFlights(recommendation: Recommendation) {
    const destination = recommendation.destination;
    const destinationLabel = recommendation.destination_name || recommendation.destination || "this destination";
    const outboundDate = recommendation.outbound_date || filters.outbound_date;
    const returnDate = recommendation.return_date || filters.return_date;

    if (!destination) {
      setFlightSearch({ destination: destinationLabel, loading: false, error: "This recommendation does not include a flight-searchable destination code yet.", response: null });
      return;
    }
    if (!filters.origin || !outboundDate || !returnDate) {
      setFlightSearch({ destination: destinationLabel, loading: false, error: "Add an origin, departure date, and return date before showing flights.", response: null });
      return;
    }

    setFlightSearch({ destination: destinationLabel, loading: true, error: null, response: null });
    try {
      const response = await searchFlights({
        origin: filters.origin,
        destination,
        outbound_date: outboundDate,
        return_date: returnDate,
        nonstop: filters.nonstop,
        include_details: false
      });
      setFlightSearch({ destination: destinationLabel, loading: false, error: null, response });
    } catch (err) {
      const text = err instanceof Error ? err.message : "Could not load flights.";
      setFlightSearch({ destination: destinationLabel, loading: false, error: text, response: null });
    }
  }

  const featured = recommendations[0];
  const visibleChips = activeChipsFromFilters(filters, activeFilters);

  return (
    <Box sx={{ minHeight: "100vh", background: "linear-gradient(180deg, #f7f7f2 0%, #e8f0ec 58%, #f7f7f2 100%)" }}>
      <AppBar position="sticky" color="inherit" elevation={0} sx={{ borderBottom: "1px solid #d8e1dc" }}>
        <Toolbar sx={{ gap: 2, flexWrap: "wrap" }}>
          <TravelExploreIcon color="primary" />
          <Typography variant="h2" component="h1" sx={{ flexGrow: 1 }}>
            Flights Anywhere
          </Typography>
          {!desktopChat && (
            <IconButton aria-label="Open chat" onClick={() => setChatOpen(true)}>
              <ChatBubbleOutlineIcon />
            </IconButton>
          )}
        </Toolbar>
      </AppBar>

      <Container maxWidth={false} sx={{ py: 3, minHeight: "calc(100vh - 65px)", display: "flex" }}>
        <Grid container spacing={3} sx={{ flex: 1, alignItems: "stretch" }}>
          <Grid item xs={12} lg={desktopChat ? 8.4 : 12} sx={{ display: "flex" }}>
            <Stack spacing={2} sx={{ flex: 1, minHeight: "calc(100vh - 113px)" }}>
              <ToolbarPanel filters={filters} updateFilter={updateFilter} onOpenFilters={() => setDrawerOpen(true)} onRunSearch={() => submitChat("Find trips that match my filters")} loading={loading} />
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" aria-label="Active filters">
                {visibleChips.map((chip) => (
                  <Chip key={chip.key} label={chipLabel(chip)} color={chip.source === "ai" ? "primary" : "default"} onDelete={() => removeChip(chip.key)} />
                ))}
              </Stack>
              {error && <Alert severity="error">{error}</Alert>}
              {featured ? <FeaturedCard recommendation={featured} onSurprise={() => submitChat("Surprise me again")} onShowFlights={() => showFlights(featured)} flightsLoading={Boolean(flightSearch?.loading && flightSearch.destination === (featured.destination_name || featured.destination || "this destination"))} /> : <EmptyState loading={loading} />}
              {flightSearch && <FlightResultsPanel search={flightSearch} />}
              <Grid container spacing={2}>
                {recommendations.slice(1).map((item) => (
                  <Grid item xs={12} sm={6} lg={4} key={`${item.destination}-${item.price}`}>
                    <DestinationCard recommendation={item} onRefine={() => submitChat(`Find more like ${item.destination_name || item.destination}`)} />
                  </Grid>
                ))}
              </Grid>
            </Stack>
          </Grid>
          {desktopChat && (
            <Grid item lg={3.6} sx={{ alignSelf: "stretch" }}>
              <ChatPanel messages={messages} message={message} setMessage={setMessage} submitChat={() => submitChat()} loading={loading} fullHeight />
            </Grid>
          )}
        </Grid>
      </Container>

      <FilterDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} filters={filters} updateFilter={updateFilter} toggleListValue={toggleListValue} />
      {!desktopChat && (
        <FloatingChat
          open={chatOpen}
          onOpen={() => setChatOpen(true)}
          onClose={() => setChatOpen(false)}
          messages={messages}
          message={message}
          setMessage={setMessage}
          submitChat={() => submitChat()}
          loading={loading}
        />
      )}
    </Box>
  );
}

function FloatingChat({
  open,
  onOpen,
  onClose,
  messages,
  message,
  setMessage,
  submitChat,
  loading
}: {
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
  messages: ChatMessage[];
  message: string;
  setMessage: (value: string) => void;
  submitChat: () => void;
  loading: boolean;
}) {
  return (
    <>
      {!open && (
        <Fab
          color="primary"
          variant="extended"
          aria-label="Open chat"
          onClick={onOpen}
          sx={{ position: "fixed", right: { xs: 16, sm: 24 }, bottom: { xs: 16, sm: 24 }, zIndex: (theme) => theme.zIndex.drawer + 1, gap: 1 }}
        >
          <ChatBubbleOutlineIcon />
          Chat
        </Fab>
      )}
      {open && (
        <Box
          role="dialog"
          aria-label="Travel chat"
          data-testid="floating-chat"
          sx={{
            position: "fixed",
            right: { xs: 12, sm: 24 },
            bottom: { xs: 12, sm: 24 },
            width: { xs: "calc(100vw - 24px)", sm: 420 },
            maxWidth: "calc(100vw - 24px)",
            zIndex: (theme) => theme.zIndex.modal,
            boxShadow: "0 24px 70px rgba(18, 42, 37, 0.24)",
            borderRadius: 3,
            overflow: "hidden"
          }}
        >
          <Box sx={{ position: "absolute", right: 10, top: 10, zIndex: 1 }}>
            <IconButton aria-label="Close chat" onClick={onClose} size="small">
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
          <ChatPanel messages={messages} message={message} setMessage={setMessage} submitChat={submitChat} loading={loading} popup />
        </Box>
      )}
    </>
  );
}

function ToolbarPanel({
  filters,
  updateFilter,
  onOpenFilters,
  onRunSearch,
  loading
}: {
  filters: TravelFilters;
  updateFilter: <K extends keyof TravelFilters>(key: K, value: TravelFilters[K]) => void;
  onOpenFilters: () => void;
  onRunSearch: () => void;
  loading: boolean;
}) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ xs: "stretch", sm: "center" }} useFlexGap flexWrap="wrap">
          <TextField label="From" value={filters.origin || ""} onChange={(event) => updateFilter("origin", event.target.value.toUpperCase())} inputProps={{ "aria-label": "Origin airport" }} sx={{ width: { xs: "100%", sm: 120 }, flexShrink: 0 }} />
          <FormControl sx={{ width: { xs: "100%", sm: 135 }, flexShrink: 0 }}>
            <InputLabel>Dates</InputLabel>
            <Select label="Dates" value={filters.date_mode} inputProps={{ "aria-label": "Dates" }} onChange={(event) => updateFilter("date_mode", event.target.value as TravelFilters["date_mode"])}>
              <MenuItem value="exact">Exact</MenuItem>
              <MenuItem value="flexible">Flexible</MenuItem>
            </Select>
          </FormControl>
          {filters.date_mode === "flexible" ? (
            <>
              <FormControl sx={{ width: { xs: "100%", sm: 145 }, flexShrink: 0 }}>
                <InputLabel>Length</InputLabel>
                <Select label="Length" value={filters.trip_length_days || 7} inputProps={{ "aria-label": "Length" }} onChange={(event) => updateFilter("trip_length_days", Number(event.target.value))}>
                  <MenuItem value={3}>3 days</MenuItem>
                  <MenuItem value={5}>5 days</MenuItem>
                  <MenuItem value={7}>7 days</MenuItem>
                  <MenuItem value={10}>10 days</MenuItem>
                  <MenuItem value={14}>14 days</MenuItem>
                </Select>
              </FormControl>
              <FormControl sx={{ width: { xs: "100%", sm: 170 }, flexShrink: 0 }}>
                <InputLabel>Window</InputLabel>
                <Select label="Window" value={filters.flexible_window} inputProps={{ "aria-label": "Window" }} onChange={(event) => updateFilter("flexible_window", event.target.value as TravelFilters["flexible_window"])}>
                  <MenuItem value="next_month">Next month</MenuItem>
                  <MenuItem value="next_3_months">Next 3 months</MenuItem>
                  <MenuItem value="next_6_months">Next 6 months</MenuItem>
                </Select>
              </FormControl>
            </>
          ) : (
            <>
              <TextField label="Depart" type="date" value={filters.outbound_date || ""} onChange={(event) => updateFilter("outbound_date", event.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: { xs: "100%", sm: 170 }, flexShrink: 0 }} />
              <TextField label="Return" type="date" value={filters.return_date || ""} onChange={(event) => updateFilter("return_date", event.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: { xs: "100%", sm: 170 }, flexShrink: 0 }} />
            </>
          )}
          <Box sx={{ minWidth: { xs: "100%", sm: 150 }, flex: "1 1 180px" }}>
            <Typography variant="caption" color="text.secondary">
              Budget ${filters.budget_max || 0}
            </Typography>
            <Slider min={100} max={3000} step={50} value={filters.budget_max || 1000} onChange={(_, value) => updateFilter("budget_max", value as number)} aria-label="Budget" />
          </Box>
          <IconButton aria-label="Open filters" onClick={onOpenFilters} color="primary" sx={{ flexShrink: 0 }}>
            <FilterListIcon />
          </IconButton>
          <Button variant="contained" startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <SearchIcon />} onClick={onRunSearch} disabled={loading} sx={{ minWidth: 136, flexShrink: 0, whiteSpace: "nowrap" }}>
            {loading ? "Searching" : "Find trips"}
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}

function FilterDrawer({ open, onClose, filters, updateFilter, toggleListValue }: { open: boolean; onClose: () => void; filters: TravelFilters; updateFilter: <K extends keyof TravelFilters>(key: K, value: TravelFilters[K]) => void; toggleListValue: (key: "climates" | "vibes", value: string) => void }) {
  return (
    <Drawer anchor="right" open={open} onClose={onClose}>
      <Box sx={{ width: { xs: 320, sm: 420 }, p: 3 }} role="presentation">
        <Stack spacing={3}>
          <Typography variant="h2">Filters</Typography>
          <TextField label="Destination" placeholder="Anywhere" value={filters.destination || ""} onChange={(event) => updateFilter("destination", event.target.value ? event.target.value.toUpperCase() : null)} />
          <FormControl fullWidth>
            <InputLabel>Stops</InputLabel>
            <Select label="Stops" value={filters.nonstop === true ? "nonstop" : filters.nonstop === false ? "one_stop" : "any"} onChange={(event) => updateFilter("nonstop", event.target.value === "nonstop" ? true : event.target.value === "one_stop" ? false : null)}>
              <MenuItem value="any">Any stops</MenuItem>
              <MenuItem value="nonstop">Nonstop</MenuItem>
              <MenuItem value="one_stop">One stop ok</MenuItem>
            </Select>
          </FormControl>
          <TextField label="Max flight minutes" type="number" value={filters.max_flight_duration_minutes || ""} onChange={(event) => updateFilter("max_flight_duration_minutes", event.target.value ? Number(event.target.value) : null)} />
          <FormControl fullWidth>
            <InputLabel>Region</InputLabel>
            <Select label="Region" value={filters.domestic_international} onChange={(event) => updateFilter("domestic_international", event.target.value as TravelFilters["domestic_international"])}>
              <MenuItem value="any">Any</MenuItem>
              <MenuItem value="domestic">Domestic</MenuItem>
              <MenuItem value="international">International</MenuItem>
            </Select>
          </FormControl>
          <ChipGroup title="Climate" values={climates} selected={filters.climates} onToggle={(value) => toggleListValue("climates", value)} />
          <ChipGroup title="Interests" values={vibes} selected={filters.vibes} onToggle={(value) => toggleListValue("vibes", value)} />
          <FormControl fullWidth>
            <InputLabel>Sort</InputLabel>
            <Select label="Sort" value={filters.sort} onChange={(event) => updateFilter("sort", event.target.value as TravelFilters["sort"])}>
              <MenuItem value="best_match">Best match</MenuItem>
              <MenuItem value="cheapest">Cheapest</MenuItem>
              <MenuItem value="shortest_flight">Shortest flight</MenuItem>
              <MenuItem value="sunniest">Sunniest</MenuItem>
              <MenuItem value="most_surprising">Most surprising</MenuItem>
            </Select>
          </FormControl>
          <Button variant="contained" onClick={onClose}>
            Apply filters
          </Button>
        </Stack>
      </Box>
    </Drawer>
  );
}

function ChipGroup({ title, values, selected, onToggle }: { title: string; values: string[]; selected: string[]; onToggle: (value: string) => void }) {
  return (
    <Stack spacing={1}>
      <Typography variant="subtitle2">{title}</Typography>
      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
        {values.map((value) => (
          <Chip key={value} label={value.replace("_", " ")} color={selected.includes(value) ? "primary" : "default"} onClick={() => onToggle(value)} />
        ))}
      </Stack>
    </Stack>
  );
}

function ChatPanel({
  messages,
  message,
  setMessage,
  submitChat,
  loading,
  fullHeight = false,
  popup = false
}: {
  messages: ChatMessage[];
  message: string;
  setMessage: (value: string) => void;
  submitChat: () => void;
  loading: boolean;
  fullHeight?: boolean;
  popup?: boolean;
}) {
  return (
    <Card
      variant="outlined"
      data-testid="chat-panel"
      sx={{
        position: fullHeight ? "sticky" : "static",
        top: fullHeight ? 90 : "auto",
        height: fullHeight ? "calc(100vh - 114px)" : popup ? "min(78vh, 680px)" : "min(78vh, 680px)",
        display: "flex",
        flexDirection: "column",
        borderRadius: popup ? 0 : undefined
      }}
    >
      <CardContent sx={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
        <Stack spacing={2} sx={{ flex: 1, minHeight: 0 }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <ChatBubbleOutlineIcon color="primary" />
            <Typography variant="h2">Where to next?</Typography>
          </Stack>
          <Stack spacing={1} sx={{ flex: 1, minHeight: 0, overflow: "auto" }}>
            {messages.map((item, index) => (
              <Box key={`${item.role}-${index}`} sx={{ alignSelf: item.role === "user" ? "flex-end" : "flex-start", bgcolor: item.role === "user" ? "primary.main" : "background.default", color: item.role === "user" ? "white" : "text.primary", px: 1.5, py: 1, borderRadius: 2, maxWidth: "90%" }}>
                <Typography variant="body2">{item.text}</Typography>
              </Box>
            ))}
            {loading && (
              <Box sx={{ alignSelf: "flex-start", bgcolor: "background.default", color: "text.primary", px: 1.5, py: 1, borderRadius: 2, maxWidth: "90%" }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <CircularProgress size={18} />
                  <Typography variant="body2">Searching destinations...</Typography>
                </Stack>
              </Box>
            )}
          </Stack>
          <OutlinedInput value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => event.key === "Enter" && !loading && submitChat()} placeholder="Try: sunny next week under $1000" multiline minRows={2} disabled={loading} />
          <Stack direction="row" spacing={1}>
            <Button variant="contained" startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <AutoAwesomeIcon />} onClick={submitChat} disabled={loading}>
              {loading ? "Asking" : "Ask"}
            </Button>
            <Button variant="outlined" onClick={() => setMessage("Surprise me somewhere sunny next week under $1000")}>
              Surprise me
            </Button>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}

function FeaturedCard({
  recommendation,
  onSurprise,
  onShowFlights,
  flightsLoading
}: {
  recommendation: Recommendation;
  onSurprise: () => void;
  onShowFlights: () => void;
  flightsLoading: boolean;
}) {
  return (
    <Card sx={{ bgcolor: "#fffdf7", border: "1px solid #d8e1dc" }}>
      <CardContent>
        <Stack spacing={2}>
          <Typography variant="overline" color="secondary">
            Best match
          </Typography>
          <Typography variant="h1">{recommendation.destination_name || recommendation.destination}</Typography>
          <Typography variant="h2">{recommendation.price ? `$${recommendation.price}` : "Price available"} · {Math.round(recommendation.match_score * 100)}% match</Typography>
          <Typography color="text.secondary">{recommendation.why}</Typography>
          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
            {recommendation.tags.map((tag) => (
              <Chip key={tag} label={tag} color="primary" />
            ))}
            {recommendation.weather && <Chip label={recommendation.weather.summary} />}
            {recommendation.places && <Chip label={recommendation.places.summary} />}
          </Stack>
        </Stack>
      </CardContent>
      <CardActions>
        <Button startIcon={flightsLoading ? <CircularProgress size={16} color="inherit" /> : <FlightTakeoffIcon />} variant="contained" onClick={onShowFlights} disabled={flightsLoading}>
          {flightsLoading ? "Loading flights" : "Show flights"}
        </Button>
        <Button startIcon={<FavoriteBorderIcon />}>Save</Button>
        <Button onClick={onSurprise}>Surprise me again</Button>
      </CardActions>
    </Card>
  );
}

function FlightResultsPanel({ search }: { search: FlightSearchState }) {
  const results = search.response?.results || [];
  return (
    <Card variant="outlined" sx={{ bgcolor: "rgba(255, 255, 255, 0.86)" }}>
      <CardContent>
        <Stack spacing={2}>
          <Stack direction="row" spacing={1} alignItems="center">
            <FlightTakeoffIcon color="primary" />
            <Typography variant="h2">Flights to {search.destination}</Typography>
          </Stack>
          {search.loading && (
            <Stack direction="row" spacing={1} alignItems="center" role="status">
              <CircularProgress size={20} />
              <Typography color="text.secondary">Checking live flight options...</Typography>
            </Stack>
          )}
          {search.error && <Alert severity="error">{search.error}</Alert>}
          {!search.loading && !search.error && search.response && results.length === 0 && (
            <Alert severity="info">The route search completed, but Google Flights did not return bookable options for these dates yet. Try broader dates or another destination.</Alert>
          )}
          {results.length > 0 && (
            <Stack spacing={1.5}>
              {results.slice(0, 5).map((flight, index) => (
                <Card key={flight.option_token || flight.route_token || `${flight.dest}-${index}`} variant="outlined">
                  <CardContent>
                    <Stack direction={{ xs: "column", sm: "row" }} spacing={1} justifyContent="space-between" alignItems={{ xs: "flex-start", sm: "center" }}>
                      <Box>
                        <Typography fontWeight={800}>{flight.airline || flight.airline_code || "Flight option"}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          {flight.flight_nums?.length ? flight.flight_nums.join(", ") : flight.flight_num || "Flight number unavailable"} · {formatDuration(flight.duration_minutes)} · {stopsLabel(flight.stops)}
                        </Typography>
                      </Box>
                      <Typography fontWeight={900}>{flight.price ? `$${flight.price}` : "Price unavailable"}</Typography>
                    </Stack>
                  </CardContent>
                </Card>
              ))}
            </Stack>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

function DestinationCard({ recommendation, onRefine }: { recommendation: Recommendation; onRefine: () => void }) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Stack spacing={1.25}>
          <Typography variant="h2">{recommendation.destination_name || recommendation.destination}</Typography>
          <Typography fontWeight={800}>{recommendation.price ? `$${recommendation.price}` : "Price available"}</Typography>
          <Typography variant="body2" color="text.secondary">{recommendation.why}</Typography>
          {recommendation.weather && <Chip size="small" label={recommendation.weather.summary} />}
          {recommendation.places && <Chip size="small" label={recommendation.places.summary} />}
        </Stack>
      </CardContent>
      <CardActions>
        <Button size="small" onClick={onRefine}>Refine</Button>
        <IconButton aria-label="Save destination">
          <FavoriteBorderIcon />
        </IconButton>
      </CardActions>
    </Card>
  );
}

function EmptyState({ loading }: { loading: boolean }) {
  const paneSx = {
    flex: 1,
    minHeight: "calc(100vh - 300px)",
    width: "100%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    bgcolor: "rgba(255, 255, 255, 0.72)",
    backdropFilter: "blur(8px)"
  };

  if (loading) {
    return (
      <Card
        variant="outlined"
        data-testid="fullscreen-loading"
        sx={paneSx}
      >
        <CardContent>
          <Stack spacing={2.5} alignItems="center" textAlign="center">
            <CircularProgress size={52} thickness={3.5} aria-label="Searching destinations" />
            <Typography variant="h1">Finding places...</Typography>
            <Typography color="text.secondary" sx={{ maxWidth: 620 }}>
              Searching live flight options and matching them to your travel mood.
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card variant="outlined" data-testid="start-pane" sx={paneSx}>
      <CardContent>
        <Stack spacing={2.5} alignItems="center" textAlign="center">
          <Typography variant="h1">Start with a destination mood</Typography>
          <Typography color="text.secondary" sx={{ maxWidth: 620 }}>Ask for something like sunny next week, Japanese temples, beach under $1000, or a surprise trip.</Typography>
        </Stack>
      </CardContent>
    </Card>
  );
}
