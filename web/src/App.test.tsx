import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeProvider } from "@mui/material/styles";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { theme } from "./theme";

function mockViewportWidth(width: number) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => {
      const min = /min-width:\s*(\d+(?:\.\d+)?)px/.exec(query);
      const max = /max-width:\s*(\d+(?:\.\d+)?)px/.exec(query);
      const matchesMin = min ? width >= Number(min[1]) : true;
      const matchesMax = max ? width <= Number(max[1]) : true;
      return {
        matches: matchesMin && matchesMax,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn()
      };
    })
  });
}

function renderApp() {
  return render(
    <ThemeProvider theme={theme}>
      <App />
    </ThemeProvider>
  );
}

const response = {
  assistant_message: "I found 2 options. My top pick is Honolulu around $450.",
  applied_filters: {
    origin: "SFO",
    destination: null,
    date_mode: "exact",
    outbound_date: "2026-06-15",
    return_date: "2026-06-19",
    trip_length_days: null,
    flexible_window: "next_3_months",
    flexible_window_start: null,
    flexible_window_end: null,
    budget_max: 1000,
    nonstop: null,
    max_flight_duration_minutes: null,
    domestic_international: "any",
    climates: ["sunny"],
    vibes: [],
    sort: "best_match"
  },
  active_filters: [
    { key: "origin", label: "From", value: "SFO", source: "user" },
    { key: "budget_max", label: "Budget", value: "$1000", source: "user" },
    { key: "climates", label: "Climate", value: "sunny", source: "ai" }
  ],
  recommendations: [
    {
      destination: "HNL",
      destination_name: "Honolulu",
      price: 450,
      currency: "USD",
      outbound_date: "2026-06-15",
      return_date: "2026-06-19",
      stops: 0,
      duration_minutes: 330,
      match_score: 0.92,
      tags: ["Under budget", "Weather match"],
      why: "This fits because $450; under budget, weather match.",
      weather: { summary: "Sunny next week" },
      places: null
    }
  ],
  clarifying_question: null
};

const flightsResponse = {
  mode: "shopping",
  selection_stage: "outbound",
  query: { origin: "SFO", destination: "HNL" },
  results: [
    {
      id: null,
      source: "shopping",
      selection_stage: "outbound",
      origin: "SFO",
      dest: "HNL",
      outbound_date: "2026-06-15",
      return_date: "2026-06-19",
      date: "2026-06-15",
      price: 450,
      price_delta: null,
      currency: "USD",
      airline_code: "HA",
      airline: "Hawaiian",
      stops: 0,
      duration_minutes: 330,
      flight_num: "HA11",
      flight_nums: ["HA11"],
      route_token: null,
      option_token: "option-1",
      outbound_options: [],
      return_options: [],
      booking_options: [],
      workflow_state: {},
      raw: null
    }
  ],
  workflow_state: { mode: "shopping" }
};

describe("App", () => {
  beforeEach(() => {
    mockViewportWidth(1440);
  });

  it("opens the filter drawer and updates chip selections", async () => {
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getByLabelText("Open filters"));
    await user.click(screen.getByText("temples"));

    expect(screen.getByText("Filters")).toBeInTheDocument();
    expect(screen.getAllByText("temples").length).toBeGreaterThan(0);
    expect(screen.getByText("Interests: temples")).toBeInTheDocument();
  });

  it("runs a recommendation from manual filters", async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => response });
    vi.stubGlobal("fetch", fetch);
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Find trips" }));

    await waitFor(() => expect(screen.getByText("Honolulu")).toBeInTheDocument());
    expect(fetch).toHaveBeenCalledWith(
      "/api/travel/recommend",
      expect.objectContaining({
        body: expect.stringContaining("Find trips that match my filters")
      })
    );
  });

  it("switches the toolbar into flexible date mode", async () => {
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getByLabelText("Dates"));
    await user.click(screen.getByRole("option", { name: "Flexible" }));
    await user.click(screen.getByLabelText("Length"));
    await user.click(screen.getByRole("option", { name: "10 days" }));
    await user.click(screen.getByLabelText("Window"));
    await user.click(screen.getByRole("option", { name: "Next 6 months" }));

    expect(screen.getByText("Dates: Flexible")).toBeInTheDocument();
    expect(screen.getByText("Length: 10 days")).toBeInTheDocument();
    expect(screen.getByText("Window: Next 6 months")).toBeInTheDocument();
  });

  it("shows a loading indicator while recommendations are searching", async () => {
    let resolveFetch: (value: unknown) => void;
    const pending = new Promise((resolve) => {
      resolveFetch = resolve;
    });
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(pending));
    renderApp();
    const user = userEvent.setup();

    await user.type(screen.getAllByPlaceholderText("Try: sunny next week under $1000")[0], "sunny next week under $1000");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("Searching destinations...")).toBeInTheDocument();
    expect(screen.getByTestId("fullscreen-loading")).toHaveStyle({ flex: "1", minHeight: "calc(100vh - 300px)", width: "100%" });
    expect(screen.getByText("Finding places...")).toBeInTheDocument();
    expect(screen.getAllByRole("progressbar").length).toBeGreaterThan(0);

    resolveFetch!({ ok: true, json: async () => response });
    await waitFor(() => expect(screen.getByText("Honolulu")).toBeInTheDocument());
  });

  it("keeps the empty state uncluttered while preserving the chat surprise action", () => {
    renderApp();

    expect(screen.getByText("Start with a destination mood")).toBeInTheDocument();
    expect(screen.getByTestId("start-pane")).toHaveStyle({ flex: "1", minHeight: "calc(100vh - 300px)", width: "100%" });
    expect(screen.getAllByRole("button", { name: "Surprise me" })).toHaveLength(1);
  });

  it("renders the desktop chat rail as a full-height panel", () => {
    renderApp();

    expect(screen.getByTestId("chat-panel")).toHaveStyle({ height: "calc(100vh - 114px)" });
    expect(screen.queryByTestId("floating-chat")).not.toBeInTheDocument();
  });

  it("collapses chat into a bottom-right popup below the wide desktop breakpoint", async () => {
    mockViewportWidth(1080);
    renderApp();
    const user = userEvent.setup();

    expect(screen.queryByTestId("chat-panel")).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Open chat" }).length).toBeGreaterThan(0);

    await user.click(screen.getAllByRole("button", { name: "Open chat" })[0]);

    expect(screen.getByTestId("floating-chat")).toBeInTheDocument();
    expect(screen.getByTestId("chat-panel")).toBeInTheDocument();
    expect(screen.getByText("Where to next?")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Close chat" }));
    expect(screen.queryByTestId("floating-chat")).not.toBeInTheDocument();
  });

  it("submits chat and renders recommendation cards with active filters", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => response }));
    renderApp();
    const user = userEvent.setup();

    await user.type(screen.getAllByPlaceholderText("Try: sunny next week under $1000")[0], "sunny next week under $1000");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(screen.getByText("Honolulu")).toBeInTheDocument());
    expect(screen.getByText("Climate: sunny")).toBeInTheDocument();
    expect(screen.getByText(/Sunny next week/)).toBeInTheDocument();
  });

  it("searches flights from the featured recommendation", async () => {
    const fetch = vi.fn().mockImplementation((url: string) => {
      if (url === "/api/travel/recommend") return Promise.resolve({ ok: true, json: async () => response });
      if (url === "/api/flights/search") return Promise.resolve({ ok: true, json: async () => flightsResponse });
      return Promise.reject(new Error(`Unexpected URL ${url}`));
    });
    vi.stubGlobal("fetch", fetch);
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Find trips" }));
    await waitFor(() => expect(screen.getByText("Honolulu")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Show flights" }));

    await waitFor(() => expect(screen.getByText("Flights to Honolulu")).toBeInTheDocument());
    expect(screen.getByText("Hawaiian")).toBeInTheDocument();
    expect(screen.getByText(/HA11/)).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(
      "/api/flights/search",
      expect.objectContaining({
        body: expect.stringContaining('"destination":"HNL"')
      })
    );
  });

  it("shows a recovery error when the recommendation request times out", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        text: async () => JSON.stringify({ detail: "Timed out waiting for a Google Flights session request." })
      })
    );
    renderApp();
    const user = userEvent.setup();

    await user.type(screen.getAllByPlaceholderText("Try: sunny next week under $1000")[0], "sunny next week under $1000");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(screen.getByText("Timed out waiting for a Google Flights session request.")).toBeInTheDocument());
  });
});
