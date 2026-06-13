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
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import ChatBubbleOutlineIcon from "@mui/icons-material/ChatBubbleOutline";
import CloseIcon from "@mui/icons-material/Close";
import FlightTakeoffIcon from "@mui/icons-material/FlightTakeoff";
import SearchIcon from "@mui/icons-material/Search";
import TravelExploreIcon from "@mui/icons-material/TravelExplore";
import { recommendTravel, searchFlights } from "./api";
import { ActiveFilterChip, defaultFilters, FallbackOption, FlightSearchResponse, Recommendation, TravelFilters } from "./types";

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
  const chips = new Map<string, ActiveFilterChip>();

  for (const chip of activeFilters) {
    if (!chip.value) continue;
    if (chip.key === "destination" && chip.value === "Anywhere") continue;
    if (filters.date_mode === "flexible" && (chip.key === "outbound_date" || chip.key === "return_date")) continue;
    if (filters.date_mode === "exact" && (chip.key === "trip_length_days" || chip.key === "flexible_window")) continue;
    chips.set(chip.key, chip);
  }

  const push = (key: string, label: string, value: string, force = false) => {
    if (!value) return;
    if (!force && chips.has(key)) return;
    chips.set(key, { key, label, value, source: sourceFor(key, activeFilters) });
  };

  if (filters.origin && (filters.origin !== defaultFilters.origin || chips.has("origin"))) {
    push("origin", "From", filters.origin, true);
  }
  if (filters.destination) {
    push("destination", "To", filters.destination, true);
  }
  if (filters.date_mode === "flexible") {
    push("date_mode", "Dates", "Flexible", true);
    if (filters.trip_length_days) {
      push("trip_length_days", "Length", `${filters.trip_length_days} days`, true);
    }
    if (filters.flexible_window !== defaultFilters.flexible_window || chips.has("flexible_window")) {
      push("flexible_window", "Window", flexibleWindowLabel(filters.flexible_window), true);
    }
  } else {
    if (filters.outbound_date) push("outbound_date", "Depart", filters.outbound_date, true);
    if (filters.return_date) push("return_date", "Return", filters.return_date, true);
  }
  if (typeof filters.budget_max === "number" && (filters.budget_max !== defaultFilters.budget_max || chips.has("budget_max"))) {
    push("budget_max", "Budget", `$${filters.budget_max}`, true);
  }
  if (filters.nonstop === true) push("nonstop", "Stops", "Nonstop", true);
  if (filters.nonstop === false) push("nonstop", "Stops", "One stop ok", true);
  if (filters.max_flight_duration_minutes) push("max_flight_duration_minutes", "Max flight", `${filters.max_flight_duration_minutes} min`, true);
  if (filters.domestic_international !== "any") push("domestic_international", "Region", filters.domestic_international, true);
  if (filters.climates.length) push("climates", "Climate", filters.climates.join(", "), true);
  if (filters.vibes.length) push("vibes", "Interests", filters.vibes.join(", "), true);
  if (filters.sort !== "best_match") push("sort", "Sort", filters.sort.replace("_", " "), true);
  return Array.from(chips.values());
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

function deriveReturnDate(outboundDate?: string | null, returnDate?: string | null, tripLengthDays?: number | null): string | null {
  if (returnDate) return returnDate;
  if (!outboundDate || !tripLengthDays) return null;
  const base = new Date(`${outboundDate}T00:00:00`);
  if (Number.isNaN(base.getTime())) return null;
  base.setDate(base.getDate() + tripLengthDays);
  return base.toISOString().slice(0, 10);
}

function destinationDisplayLabel(recommendation: Recommendation): string {
  if (recommendation.destination_name && recommendation.destination) {
    return `${recommendation.destination_name} (${recommendation.destination})`;
  }
  return recommendation.destination_name || recommendation.destination || "this destination";
}

function sameRecommendation(a?: Recommendation | null, b?: Recommendation | null): boolean {
  return Boolean(a && b && (a.destination || a.destination_name) && (a.destination || a.destination_name) === (b.destination || b.destination_name));
}

const compactPrimaryChipSx = {
  alignSelf: "flex-start",
  borderRadius: "999px",
  fontWeight: 700
};

function matchesWeatherFilters(recommendation: Recommendation, filters: TravelFilters): boolean {
  if (!filters.climates.length) return true;
  return recommendation.tags.includes("Weather match") || recommendation.weather?.summary?.toLowerCase().includes("match") === true;
}

function matchesVibeFilters(recommendation: Recommendation, filters: TravelFilters): boolean {
  if (!filters.vibes.length) return true;
  return Boolean(recommendation.places?.matched_interests?.length);
}

function matchedFilterCount(recommendation: Recommendation, filters: TravelFilters): number {
  let matches = 0;
  if (typeof filters.budget_max === "number" && recommendation.price !== null && recommendation.price !== undefined && recommendation.price <= filters.budget_max) {
    matches += 1;
  }
  if (filters.nonstop === true && recommendation.stops === 0) {
    matches += 1;
  } else if (filters.nonstop === false && recommendation.stops !== null && recommendation.stops !== undefined && recommendation.stops >= 1) {
    matches += 1;
  }
  if (
    typeof filters.max_flight_duration_minutes === "number" &&
    recommendation.duration_minutes !== null &&
    recommendation.duration_minutes !== undefined &&
    recommendation.duration_minutes <= filters.max_flight_duration_minutes
  ) {
    matches += 1;
  }
  if (filters.climates.length && matchesWeatherFilters(recommendation, filters)) {
    matches += 1;
  }
  if (filters.vibes.length && matchesVibeFilters(recommendation, filters)) {
    matches += 1;
  }
  return matches;
}

function similarityScore(candidate: Recommendation, seed: Recommendation, filters: TravelFilters): number {
  let score = matchedFilterCount(candidate, filters) * 10;
  const sharedTags = candidate.tags.filter((tag) => seed.tags.includes(tag)).length;
  score += sharedTags * 4;

  if (candidate.stops !== null && candidate.stops !== undefined && candidate.stops === seed.stops) {
    score += 3;
  }
  if (candidate.weather && seed.weather) {
    score += 2;
  }

  const sharedInterests = candidate.places?.matched_interests?.filter((item) => seed.places?.matched_interests?.includes(item)).length || 0;
  score += sharedInterests * 3;

  if (candidate.price !== null && candidate.price !== undefined && seed.price !== null && seed.price !== undefined) {
    score += Math.max(0, 6 - Math.abs(candidate.price - seed.price) / 30);
  }
  if (
    candidate.duration_minutes !== null &&
    candidate.duration_minutes !== undefined &&
    seed.duration_minutes !== null &&
    seed.duration_minutes !== undefined
  ) {
    score += Math.max(0, 5 - Math.abs(candidate.duration_minutes - seed.duration_minutes) / 60);
  }
  if (sameRecommendation(candidate, seed)) {
    score += 100;
  }
  return score;
}

const surprisePrompts = [
  "Surprise me with a sunny beach trip next month under $900",
  "Find me an unexpected long weekend getaway with nonstop flights under $500",
  "Show me a surprise international city with great food this fall under $1200",
  "Pick a warm surprise trip for one week sometime in the next 3 months",
  "Suggest a culture-focused surprise trip with mild weather and a reasonable budget",
  "Find an adventurous surprise destination with the cheapest dates you can spot"
];

function nextSurprisePrompt(previous: string | null): string {
  const options = surprisePrompts.filter((prompt) => prompt !== previous);
  const pool = options.length ? options : surprisePrompts;
  return pool[Math.floor(Math.random() * pool.length)];
}

function DestinationTitle({ name, code, featured = false }: { name?: string | null; code?: string | null; featured?: boolean }) {
  const title = name || code || "Destination";
  const showCode = Boolean(name && code && name !== code);

  return (
    <Stack direction="row" spacing={1} alignItems="baseline" justifyContent="flex-start" useFlexGap flexWrap="wrap">
      <Typography variant={featured ? "h1" : "h2"}>{title}</Typography>
      {showCode && (
        <Typography
          color="text.secondary"
          sx={{
            fontSize: featured ? "0.92rem" : "0.8rem",
            fontWeight: 700,
            letterSpacing: "0.08em",
            transform: "translateY(0.3em)"
          }}
        >
          {code}
        </Typography>
      )}
    </Stack>
  );
}

export default function App() {
  const desktopChat = useMediaQuery("(min-width:1800px)");
  const [filters, setFilters] = useState<TravelFilters>(defaultFilters);
  const [activeFilters, setActiveFilters] = useState<ActiveFilterChip[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [fallbackOptions, setFallbackOptions] = useState<FallbackOption[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", text: "Where to next? Tell me a vibe, a budget, or ask me to surprise you." }
  ]);
  const [message, setMessage] = useState("");
  const [chatOpen, setChatOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [assistantNotice, setAssistantNotice] = useState<string | null>(null);
  const [flightSearch, setFlightSearch] = useState<FlightSearchState | null>(null);
  const [lastSurprisePrompt, setLastSurprisePrompt] = useState<string | null>(null);
  const [similarSeed, setSimilarSeed] = useState<Recommendation | null>(null);

  async function runRecommendation(
    text: string,
    { logUserMessage, logAssistantMessage }: { logUserMessage: boolean; logAssistantMessage: boolean }
  ) {
    const trimmed = text.trim();
    if (logUserMessage && !trimmed) return;
    setLoading(true);
    setError(null);
    if (logUserMessage) {
      setMessages((items) => [...items, { role: "user", text: trimmed }]);
      setMessage("");
    }
    try {
      const response = await recommendTravel(trimmed, filters);
      setFilters(response.applied_filters);
      setActiveFilters(response.active_filters);
      setRecommendations(response.recommendations);
      setFallbackOptions(response.fallback_options || []);
      setAssistantNotice(response.assistant_message);
      setSimilarSeed(null);
      setFlightSearch(null);
      if (logAssistantMessage) {
        setMessages((items) => [...items, { role: "assistant", text: response.assistant_message }]);
      }
    } catch (err) {
      const text = err instanceof Error ? err.message : "Something went wrong.";
      setError(text);
      setSimilarSeed(null);
      setFallbackOptions([]);
      setAssistantNotice(null);
      if (logAssistantMessage) {
        setMessages((items) => [...items, { role: "assistant", text: "I could not complete that search yet. Try broader dates or fewer filters." }]);
      }
    } finally {
      setLoading(false);
    }
  }

  async function submitChat(text = message) {
    return runRecommendation(text, { logUserMessage: true, logAssistantMessage: true });
  }

  function queueSurprisePrompt(): string {
    const prompt = nextSurprisePrompt(lastSurprisePrompt);
    setLastSurprisePrompt(prompt);
    setMessage(prompt);
    return prompt;
  }

  async function runFilterSearch() {
    return runRecommendation("", { logUserMessage: false, logAssistantMessage: false });
  }

  function applyFallback(option: FallbackOption) {
    setFilters(option.applied_filters);
    setActiveFilters(option.active_filters);
    setRecommendations(option.recommendations);
    setFallbackOptions([]);
    setAssistantNotice(option.assistant_message);
    setSimilarSeed(null);
    setFlightSearch(null);
    setError(null);
    setMessages((items) => [...items, { role: "assistant", text: option.assistant_message }]);
  }

  function updateFilter<K extends keyof TravelFilters>(key: K, value: TravelFilters[K]) {
    setFilters((current) => {
      if (key === "date_mode") {
        if (value === "flexible") {
          return {
            ...current,
            date_mode: "flexible",
            outbound_date: "",
            return_date: "",
            flexible_window_start: null,
            flexible_window_end: null
          };
        }
        return {
          ...current,
          date_mode: "exact",
          flexible_window_start: null,
          flexible_window_end: null
        };
      }

      if (key === "flexible_window") {
        return {
          ...current,
          flexible_window: value as TravelFilters["flexible_window"],
          flexible_window_start: null,
          flexible_window_end: null
        };
      }

      return { ...current, [key]: value };
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
    const destinationLabel = destinationDisplayLabel(recommendation);
    const outboundDate = recommendation.outbound_date || filters.outbound_date;
    const returnDate = deriveReturnDate(recommendation.outbound_date || filters.outbound_date, recommendation.return_date || filters.return_date, filters.trip_length_days);

    if (!destination) {
      setFlightSearch({ destination: destinationLabel, loading: false, error: "This recommendation does not include a flight-searchable destination code yet.", response: null });
      return;
    }
    if (!filters.origin || !outboundDate || !returnDate) {
      setFlightSearch({
        destination: destinationLabel,
        loading: false,
        error: "Show flights currently searches round-trip itineraries, so add an origin plus departure and return dates first.",
        response: null
      });
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

  function showMoreLike(recommendation: Recommendation) {
    setSimilarSeed(recommendation);
    setAssistantNotice(`Showing broader matches similar to ${destinationDisplayLabel(recommendation)}, ranked by shared traits and filters matched.`);
    setFallbackOptions([]);
    setFlightSearch(null);
    setError(null);
  }

  const featured = recommendations[0];
  const secondaryRecommendations = similarSeed
    ? [...recommendations.slice(1)].sort((left, right) => similarityScore(right, similarSeed, filters) - similarityScore(left, similarSeed, filters))
    : recommendations.slice(1);
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
          <Grid item xs={12} lg={desktopChat ? 8.8 : 12} sx={{ display: "flex" }}>
            <Stack spacing={2} sx={{ flex: 1, minHeight: "calc(100vh - 113px)" }}>
              <ToolbarPanel filters={filters} updateFilter={updateFilter} onRunSearch={runFilterSearch} loading={loading} />
              {visibleChips.length > 0 && (
                <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" aria-label="Active filters">
                  {visibleChips.map((chip) => (
                    <Chip key={chip.key} label={chipLabel(chip)} color="primary" onDelete={() => removeChip(chip.key)} sx={compactPrimaryChipSx} />
                  ))}
                </Stack>
              )}
              {error && <Alert severity="error">{error}</Alert>}
              {assistantNotice && (fallbackOptions.length > 0 || Boolean(similarSeed)) && <Alert severity="info">{assistantNotice}</Alert>}
              {fallbackOptions.length > 0 && recommendations.length === 0 && <FallbackOptionsPanel options={fallbackOptions} onApply={applyFallback} />}
              {featured ? <FeaturedCard recommendation={featured} onSurprise={() => submitChat(queueSurprisePrompt())} onShowFlights={() => showFlights(featured)} flightsLoading={Boolean(flightSearch?.loading && flightSearch.destination === destinationDisplayLabel(featured))} /> : <EmptyState loading={loading} />}
              {flightSearch && <FlightResultsPanel search={flightSearch} />}
              <Grid container spacing={2}>
                {secondaryRecommendations.map((item) => (
                  <Grid item xs={12} sm={6} lg={4} key={`${item.destination}-${item.price}`}>
                    <DestinationCard
                      recommendation={item}
                      highlighted={sameRecommendation(item, similarSeed)}
                      flightsLoading={Boolean(flightSearch?.loading && flightSearch.destination === destinationDisplayLabel(item))}
                      onRefine={() => showMoreLike(item)}
                      onShowFlights={() => showFlights(item)}
                    />
                  </Grid>
                ))}
              </Grid>
            </Stack>
          </Grid>
          {desktopChat && (
            <Grid item lg={3.2} sx={{ alignSelf: "stretch" }}>
              <ChatPanel messages={messages} message={message} setMessage={setMessage} submitChat={() => submitChat()} loading={loading} onSurprise={queueSurprisePrompt} fullHeight />
            </Grid>
          )}
        </Grid>
      </Container>
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
          onSurprise={queueSurprisePrompt}
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
  loading,
  onSurprise
}: {
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
  messages: ChatMessage[];
  message: string;
  setMessage: (value: string) => void;
  submitChat: () => void;
  loading: boolean;
  onSurprise: () => void;
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
          <ChatPanel messages={messages} message={message} setMessage={setMessage} submitChat={submitChat} loading={loading} onSurprise={onSurprise} popup />
        </Box>
      )}
    </>
  );
}

function ToolbarPanel({
  filters,
  updateFilter,
  onRunSearch,
  loading
}: {
  filters: TravelFilters;
  updateFilter: <K extends keyof TravelFilters>(key: K, value: TravelFilters[K]) => void;
  onRunSearch: () => void;
  loading: boolean;
}) {
  const gridTemplateColumns =
    filters.date_mode === "flexible"
      ? {
          xs: "1fr",
          lg: "110px 126px 118px 120px 136px minmax(260px, 1fr) 136px"
        }
      : {
          xs: "1fr",
          lg: "110px 126px 118px 146px 146px minmax(260px, 1fr) 136px"
        };

  return (
    <Card variant="outlined" sx={{ bgcolor: "rgba(255, 255, 255, 0.86)" }}>
      <CardContent sx={{ p: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns,
            gap: 1,
            alignItems: "center",
            width: "100%"
          }}
        >
          <TextField label="From" value={filters.origin || ""} onChange={(event) => updateFilter("origin", event.target.value ? event.target.value.toUpperCase() : null)} inputProps={{ "aria-label": "Origin airport" }} sx={{ width: { xs: "100%", sm: 110 }, flexShrink: 0 }} />
          <TextField label="To" placeholder="Anywhere" value={filters.destination || ""} onChange={(event) => updateFilter("destination", event.target.value ? event.target.value.toUpperCase() : null)} inputProps={{ "aria-label": "Destination airport" }} sx={{ width: { xs: "100%", sm: 126 }, flexShrink: 0 }} />
          <FormControl sx={{ width: { xs: "100%", sm: 118 }, flexShrink: 0 }}>
              <InputLabel>Dates</InputLabel>
              <Select label="Dates" value={filters.date_mode} inputProps={{ "aria-label": "Dates" }} onChange={(event) => updateFilter("date_mode", event.target.value as TravelFilters["date_mode"])}>
                <MenuItem value="exact">Exact</MenuItem>
                <MenuItem value="flexible">Flexible</MenuItem>
              </Select>
          </FormControl>
          {filters.date_mode === "flexible" ? (
            <>
              <FormControl sx={{ width: { xs: "100%", sm: 120 }, flexShrink: 0 }}>
                <InputLabel>Length</InputLabel>
                <Select label="Length" value={filters.trip_length_days || 7} inputProps={{ "aria-label": "Length" }} onChange={(event) => updateFilter("trip_length_days", Number(event.target.value))}>
                  <MenuItem value={3}>3 days</MenuItem>
                  <MenuItem value={5}>5 days</MenuItem>
                  <MenuItem value={7}>7 days</MenuItem>
                  <MenuItem value={10}>10 days</MenuItem>
                  <MenuItem value={14}>14 days</MenuItem>
                </Select>
              </FormControl>
              <FormControl sx={{ width: { xs: "100%", sm: 136 }, flexShrink: 0 }}>
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
              <TextField label="Depart" type="date" value={filters.outbound_date || ""} onChange={(event) => updateFilter("outbound_date", event.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: { xs: "100%", sm: 146 }, flexShrink: 0 }} />
              <TextField label="Return" type="date" value={filters.return_date || ""} onChange={(event) => updateFilter("return_date", event.target.value)} InputLabelProps={{ shrink: true }} sx={{ width: { xs: "100%", sm: 146 }, flexShrink: 0 }} />
            </>
          )}
          <Box sx={{ minWidth: { xs: "100%", lg: 260 }, width: "100%" }}>
            <Typography variant="caption" color="text.secondary">
              Budget ${filters.budget_max || 0}
            </Typography>
            <Slider min={25} max={3000} step={5} value={filters.budget_max || 1000} onChange={(_, value) => updateFilter("budget_max", value as number)} aria-label="Budget" />
          </Box>
          <Button variant="contained" startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <SearchIcon />} onClick={onRunSearch} disabled={loading} sx={{ minWidth: 122, width: "100%", height: 40, flexShrink: 0, whiteSpace: "nowrap" }}>
            {loading ? "Searching" : "Find trips"}
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
}

function ChatPanel({
  messages,
  message,
  setMessage,
  submitChat,
  loading,
  onSurprise,
  fullHeight = false,
  popup = false
}: {
  messages: ChatMessage[];
  message: string;
  setMessage: (value: string) => void;
  submitChat: () => void;
  loading: boolean;
  onSurprise: () => void;
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
            <Button variant="outlined" onClick={onSurprise}>
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
          <DestinationTitle name={recommendation.destination_name} code={recommendation.destination} featured />
          <Typography variant="h2">{recommendation.price ? `$${recommendation.price}` : "Price available"} · {Math.round(recommendation.match_score * 100)}% match</Typography>
          <RecommendationPills recommendation={recommendation} />
        </Stack>
      </CardContent>
      <CardActions>
        <Button startIcon={flightsLoading ? <CircularProgress size={16} color="inherit" /> : <FlightTakeoffIcon />} variant="contained" onClick={onShowFlights} disabled={flightsLoading}>
          {flightsLoading ? "Loading flights" : "Show flights"}
        </Button>
        <Button onClick={onSurprise}>Surprise me again</Button>
      </CardActions>
    </Card>
  );
}

function RecommendationPills({ recommendation }: { recommendation: Recommendation }) {
  const hasSignals = recommendation.tags.length > 0 || recommendation.weather || recommendation.places;

  return (
    <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
      {recommendation.tags.map((tag) => (
        <Chip key={tag} label={tag} color="primary" sx={compactPrimaryChipSx} />
      ))}
      {recommendation.places && <Chip label={recommendation.places.summary} color="primary" sx={compactPrimaryChipSx} />}
      {!hasSignals && <Chip label={`${Math.round(recommendation.match_score * 100)}% match`} variant="outlined" />}
    </Stack>
  );
}

function FallbackOptionsPanel({
  options,
  onApply
}: {
  options: FallbackOption[];
  onApply: (option: FallbackOption) => void;
}) {
  return (
    <Card variant="outlined" sx={{ bgcolor: "rgba(255, 255, 255, 0.9)" }}>
      <CardContent>
        <Stack spacing={2}>
          <Typography variant="h2">Verified fallback options</Typography>
          <Typography color="text.secondary">
            These alternatives already produced results, so applying one will move you forward without another dead end.
          </Typography>
          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
            {options.map((option) => (
              <Button key={option.label} variant="outlined" onClick={() => onApply(option)}>
                {option.label}
              </Button>
            ))}
          </Stack>
        </Stack>
      </CardContent>
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

function DestinationCard({
  recommendation,
  onRefine,
  onShowFlights,
  flightsLoading,
  highlighted
}: {
  recommendation: Recommendation;
  onRefine: () => void;
  onShowFlights: () => void;
  flightsLoading: boolean;
  highlighted: boolean;
}) {
  return (
    <Card
      variant="outlined"
      data-testid={`destination-card-${recommendation.destination || recommendation.destination_name || "unknown"}`}
      sx={{
        height: "100%",
        borderColor: highlighted ? "#2e7d32" : undefined,
        boxShadow: highlighted ? "0 0 0 2px rgba(46, 125, 50, 0.14)" : undefined,
        background: highlighted ? "linear-gradient(180deg, rgba(236, 249, 239, 0.92) 0%, rgba(255, 255, 255, 0.98) 100%)" : undefined
      }}
    >
      <CardContent>
        <Stack spacing={1.5}>
          <DestinationTitle name={recommendation.destination_name} code={recommendation.destination} />
          <Typography fontWeight={800}>{recommendation.price ? `$${recommendation.price}` : "Price available"}</Typography>
          <RecommendationPills recommendation={recommendation} />
        </Stack>
      </CardContent>
      <CardActions>
        <Button size="small" startIcon={flightsLoading ? <CircularProgress size={14} color="inherit" /> : <FlightTakeoffIcon fontSize="small" />} onClick={onShowFlights} disabled={flightsLoading}>
          {flightsLoading ? "Loading flights" : "Show flights"}
        </Button>
        <Button size="small" onClick={onRefine}>{`More like ${recommendation.destination || recommendation.destination_name || "this"}`}</Button>
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
