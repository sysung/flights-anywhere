import { render, screen, waitFor, within } from "@testing-library/react";
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
  fallback_options: [],
  clarifying_question: null
};

const fallbackResponse = {
  assistant_message: "I couldn't find an exact match for every filter. I already verified fallback options that do work: raise budget to $450, or remove climate filter.",
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
    budget_max: 200,
    nonstop: null,
    max_flight_duration_minutes: null,
    domestic_international: "any",
    climates: ["sunny"],
    vibes: [],
    sort: "best_match"
  },
  active_filters: [
    { key: "origin", label: "From", value: "SFO", source: "user" },
    { key: "budget_max", label: "Budget", value: "$200", source: "user" },
    { key: "climates", label: "Climate", value: "sunny", source: "ai" }
  ],
  recommendations: [],
  fallback_options: [
    {
      label: "Raise budget to $450",
      assistant_message: "I couldn't find a match with your current budget, but I did verify options if we raise it to $450.",
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
        budget_max: 450,
        nonstop: null,
        max_flight_duration_minutes: null,
        domestic_international: "any",
        climates: ["sunny"],
        vibes: [],
        sort: "best_match"
      },
      active_filters: [
        { key: "origin", label: "From", value: "SFO", source: "user" },
        { key: "budget_max", label: "Budget", value: "$450", source: "user" },
        { key: "climates", label: "Climate", value: "sunny", source: "user" }
      ],
      recommendations: [response.recommendations[0]]
    },
    {
      label: "Remove climate filter",
      assistant_message: "I couldn't find a destination that matches the current weather filter, but I did verify options once I removed it.",
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
        budget_max: 200,
        nonstop: null,
        max_flight_duration_minutes: null,
        domestic_international: "any",
        climates: [],
        vibes: [],
        sort: "best_match"
      },
      active_filters: [
        { key: "origin", label: "From", value: "SFO", source: "user" },
        { key: "budget_max", label: "Budget", value: "$200", source: "user" }
      ],
      recommendations: [
        {
          ...response.recommendations[0],
          destination: "SEA",
          destination_name: "Seattle",
          price: 180,
          weather: { summary: "Weather match is moderate." },
          tags: ["Under budget"],
          why: "This fits because $180; under budget."
        }
      ]
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

const discoveryResponse = {
  assistant_message: "I found 8 options. My top pick is Los Angeles around $56.",
  applied_filters: {
    origin: "SFO",
    destination: null,
    date_mode: "flexible",
    outbound_date: null,
    return_date: null,
    trip_length_days: 7,
    flexible_window: "next_3_months",
    flexible_window_start: "2026-06-15",
    flexible_window_end: "2026-09-15",
    budget_max: 1000,
    nonstop: null,
    max_flight_duration_minutes: null,
    domestic_international: "any",
    climates: [],
    vibes: [],
    sort: "cheapest"
  },
  active_filters: [
    { key: "origin", label: "From", value: "SFO", source: "user" },
    { key: "date_mode", label: "Dates", value: "Flexible", source: "ai" },
    { key: "trip_length_days", label: "Length", value: "7 days", source: "user" },
    { key: "budget_max", label: "Budget", value: "$1000", source: "user" },
    { key: "sort", label: "Sort", value: "cheapest", source: "user" }
  ],
  recommendations: [
    {
      destination: "LAX",
      destination_name: "Los Angeles",
      price: 56,
      currency: "USD",
      outbound_date: "2026-07-11",
      return_date: "2026-07-18",
      stops: 0,
      duration_minutes: 95,
      match_score: 0.7,
      tags: ["Under budget", "Cheapest flexible date"],
      why: "This fits because $56; under budget, cheapest flexible date.",
      weather: null,
      places: null
    },
    {
      destination: "SAN",
      destination_name: "San Diego",
      price: 69,
      currency: "USD",
      outbound_date: "2026-07-12",
      return_date: "2026-07-19",
      stops: 0,
      duration_minutes: 102,
      match_score: 0.68,
      tags: ["Under budget", "Cheapest flexible date"],
      why: "This fits because $69; under budget, cheapest flexible date.",
      weather: null,
      places: null
    },
    {
      destination: "LAS",
      destination_name: "Las Vegas",
      price: 80,
      currency: "USD",
      outbound_date: "2026-07-10",
      return_date: "2026-07-17",
      stops: 0,
      duration_minutes: 98,
      match_score: 0.66,
      tags: ["Under budget", "Cheapest flexible date"],
      why: "This fits because $80; under budget, cheapest flexible date.",
      weather: null,
      places: null
    }
  ],
  fallback_options: [],
  clarifying_question: null
};

const secondaryFlightsResponse = {
  ...flightsResponse,
  query: { origin: "SFO", destination: "SAN" },
  results: [
    {
      ...flightsResponse.results[0],
      dest: "SAN",
      airline_code: "AS",
      airline: "Alaska",
      flight_num: "AS2211",
      flight_nums: ["AS2211"]
    }
  ]
};

describe("App", () => {
  beforeEach(() => {
    mockViewportWidth(1440);
  });

  it("updates inline filters and renders active pills", async () => {
    renderApp();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Destination airport"), "hnl");

    expect(screen.getByText("To: HNL")).toBeInTheDocument();
  });

  it("runs a recommendation from manual filters", async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => response });
    vi.stubGlobal("fetch", fetch);
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Find trips" }));

    await waitFor(() => expect(screen.getByText("Honolulu")).toBeInTheDocument());
    expect(fetch).toHaveBeenCalledWith("/api/travel/recommend", expect.any(Object));
    const request = JSON.parse(fetch.mock.calls[0][1].body as string);
    expect(request.message).toBe("");
    expect(request.filters.origin).toBe("SFO");
  });

  it("switches the inline toolbar into flexible date mode", async () => {
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

  it("clears stale exact dates when switching the toolbar to flexible mode", async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => response });
    vi.stubGlobal("fetch", fetch);
    renderApp();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("Depart"), "2026-06-15");
    await user.type(screen.getByLabelText("Return"), "2026-06-19");
    expect(screen.getByText("Depart: 2026-06-15")).toBeInTheDocument();
    expect(screen.getByText("Return: 2026-06-19")).toBeInTheDocument();

    await user.click(screen.getByLabelText("Dates"));
    await user.click(screen.getByRole("option", { name: "Flexible" }));

    expect(screen.queryByText("Depart: 2026-06-15")).not.toBeInTheDocument();
    expect(screen.queryByText("Return: 2026-06-19")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Find trips" }));

    await waitFor(() => expect(fetch).toHaveBeenCalled());
    const request = JSON.parse(fetch.mock.calls[0][1].body as string);
    expect(request.filters.outbound_date).toBe("");
    expect(request.filters.return_date).toBe("");
    expect(request.filters.date_mode).toBe("flexible");
  });

  it("shows a loading indicator while recommendations are searching", async () => {
    let resolveFetch: (value: unknown) => void;
    const pending = new Promise((resolve) => {
      resolveFetch = resolve;
    });
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(pending));
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getAllByRole("button", { name: "Open chat" })[0]);
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
    expect(screen.getAllByRole("button", { name: "Open chat" }).length).toBeGreaterThan(0);
  });

  it("renders the desktop chat rail as a full-height panel", () => {
    mockViewportWidth(1920);
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

    await user.click(screen.getAllByRole("button", { name: "Open chat" })[0]);
    await user.type(screen.getAllByPlaceholderText("Try: sunny next week under $1000")[0], "sunny next week under $1000");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(screen.getByText("Honolulu")).toBeInTheDocument());
    expect(screen.getByText("Climate: sunny")).toBeInTheDocument();
    expect(screen.getAllByText("Weather match").length).toBeGreaterThan(0);
  });

  it("rotates the surprise prompt instead of reusing one canned query", async () => {
    const random = vi.spyOn(Math, "random").mockReturnValue(0);
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getAllByRole("button", { name: "Open chat" })[0]);
    await user.click(screen.getByRole("button", { name: "Surprise me" }));
    expect(screen.getByPlaceholderText("Try: sunny next week under $1000")).toHaveValue(
      "Surprise me with a sunny beach trip next month under $900"
    );

    await user.click(screen.getByRole("button", { name: "Surprise me" }));
    expect(screen.getByPlaceholderText("Try: sunny next week under $1000")).toHaveValue(
      "Find me an unexpected long weekend getaway with nonstop flights under $500"
    );

    expect(screen.getByPlaceholderText("Try: sunny next week under $1000")).not.toHaveValue(
      "Surprise me somewhere sunny next week under $1000"
    );

    random.mockRestore();
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

    await waitFor(() => expect(screen.getByText("Flights to Honolulu (HNL)")).toBeInTheDocument());
    expect(screen.getByText("Hawaiian")).toBeInTheDocument();
    expect(screen.getByText(/HA11/)).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(
      "/api/flights/search",
      expect.objectContaining({
        body: expect.stringContaining('"destination":"HNL"')
      })
    );
  });

  it("keeps more-like refinement local and highlights the selected airport card", async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => discoveryResponse });
    vi.stubGlobal("fetch", fetch);
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Find trips" }));

    await waitFor(() => expect(screen.getByText("Los Angeles")).toBeInTheDocument());
    expect(screen.getByText("LAX")).toBeInTheDocument();
    expect(screen.queryByText(/This fits because/i)).not.toBeInTheDocument();

    const sanCard = screen.getByTestId("destination-card-SAN");
    expect(within(sanCard).getByText("San Diego")).toBeInTheDocument();
    expect(within(sanCard).getByText("SAN")).toBeInTheDocument();

    await user.click(within(sanCard).getByRole("button", { name: "More like SAN" }));

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("To: SAN")).not.toBeInTheDocument();
    expect(screen.getByText("Showing broader matches similar to San Diego (SAN), ranked by shared traits and filters matched.")).toBeInTheDocument();
    expect(sanCard).toHaveStyle({ borderColor: "#2e7d32" });
  });

  it("shows flights from a secondary destination card", async () => {
    const fetch = vi.fn().mockImplementation((url: string) => {
      if (url === "/api/travel/recommend") return Promise.resolve({ ok: true, json: async () => discoveryResponse });
      if (url === "/api/flights/search") return Promise.resolve({ ok: true, json: async () => secondaryFlightsResponse });
      return Promise.reject(new Error(`Unexpected URL ${url}`));
    });
    vi.stubGlobal("fetch", fetch);
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Find trips" }));
    await waitFor(() => expect(screen.getByText("Los Angeles")).toBeInTheDocument());

    const sanCard = screen.getByTestId("destination-card-SAN");
    await user.click(within(sanCard).getByRole("button", { name: "Show flights" }));

    await waitFor(() => expect(screen.getByText("Flights to San Diego (SAN)")).toBeInTheDocument());
    expect(screen.getByText("Alaska")).toBeInTheDocument();
    expect(screen.getByText(/AS2211/)).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith(
      "/api/flights/search",
      expect.objectContaining({
        body: expect.stringContaining('"destination":"SAN"')
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

    await user.click(screen.getAllByRole("button", { name: "Open chat" })[0]);
    await user.type(screen.getAllByPlaceholderText("Try: sunny next week under $1000")[0], "sunny next week under $1000");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(screen.getByText("Timed out waiting for a Google Flights session request.")).toBeInTheDocument());
  });

  it("renders verified fallbacks and applies one without another search", async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => fallbackResponse });
    vi.stubGlobal("fetch", fetch);
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getAllByRole("button", { name: "Open chat" })[0]);
    await user.type(screen.getAllByPlaceholderText("Try: sunny next week under $1000")[0], "sunny next week under $200");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(screen.getByText("Verified fallback options")).toBeInTheDocument());
    expect(screen.getAllByText(/already verified fallback options/).length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: "Raise budget to $450" }));

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Honolulu")).toBeInTheDocument();
    expect(screen.queryByText("Verified fallback options")).not.toBeInTheDocument();
  });
});
