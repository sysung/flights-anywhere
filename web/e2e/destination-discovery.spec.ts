import { expect, test } from "@playwright/test";

const recommendationResponse = {
  assistant_message: "Honolulu is the best sunny match under $1000.",
  applied_filters: {
    origin: "SFO",
    destination: null,
    date_mode: "exact",
    outbound_date: "2026-06-18",
    return_date: "2026-06-25",
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
      outbound_date: "2026-06-18",
      return_date: "2026-06-25",
      stops: 0,
      duration_minutes: 330,
      match_score: 0.92,
      tags: ["Under budget", "Weather match"],
      why: "Sunny weather and a fare well under budget.",
      weather: { summary: "Sunny next week" },
      places: { summary: "Beaches and food", matched_interests: ["beaches", "food"] }
    }
  ],
  clarifying_question: null
};

const flexibleRecommendationResponse = {
  assistant_message: "I found flexible-date deals. Cancun is cheapest around $220.",
  applied_filters: {
    origin: "SFO",
    destination: null,
    date_mode: "flexible",
    outbound_date: null,
    return_date: null,
    trip_length_days: 7,
    flexible_window: "next_6_months",
    flexible_window_start: "2026-06-19",
    flexible_window_end: "2026-12-09",
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
    { key: "flexible_window", label: "Window", value: "Next 6 months", source: "ai" },
    { key: "budget_max", label: "Budget", value: "$1000", source: "user" },
    { key: "sort", label: "Sort", value: "cheapest", source: "user" }
  ],
  recommendations: [
    {
      destination: "CUN",
      destination_name: "Cancun",
      price: 220,
      currency: "USD",
      outbound_date: "2026-08-07",
      return_date: "2026-08-14",
      stops: 1,
      duration_minutes: 405,
      match_score: 0.88,
      tags: ["Under budget", "Cheapest flexible date"],
      why: "This is the cheapest flexible-date match in the selected window.",
      weather: null,
      places: null
    }
  ],
  clarifying_question: null
};

test("sunny under $1000 discovery shows loading and recommendations", async ({ page }) => {
  await page.route("**/api/travel/recommend", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 350));
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(recommendationResponse)
    });
  });

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Flights Anywhere" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Surprise me" })).toHaveCount(1);

  const chatPanel = page.getByTestId("chat-panel");
  const box = await chatPanel.boundingBox();
  expect(box?.height).toBeGreaterThan(720);

  await page.getByPlaceholder("Try: sunny next week under $1000").fill("sunny next week under $1000");
  await page.getByRole("button", { name: "Ask" }).click();

  await expect(page.getByText("Searching destinations...")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Honolulu" })).toBeVisible();
  await expect(page.getByText("Climate: sunny")).toBeVisible();
  await expect(page.locator(".MuiChip-label").filter({ hasText: "Sunny next week" }).first()).toBeVisible();
});

test("timeout response appears as a recoverable search error", async ({ page }) => {
  await page.route("**/api/travel/recommend", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Timed out waiting for a Google Flights session request." })
    });
  });

  await page.goto("/");
  await page.getByPlaceholder("Try: sunny next week under $1000").fill("sunny next week under $1000");
  await page.getByRole("button", { name: "Ask" }).click();

  await expect(page.getByText("Timed out waiting for a Google Flights session request.")).toBeVisible();
  await expect(page.getByText("I could not complete that search yet. Try broader dates or fewer filters.")).toBeVisible();
});

test("cheapest any-date discovery applies flexible date chips", async ({ page }) => {
  await page.route("**/api/travel/recommend", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(flexibleRecommendationResponse)
    });
  });

  await page.goto("/");
  await page.getByPlaceholder("Try: sunny next week under $1000").fill("find the cheapest 1 week trip any date in the next 6 months under $1000");
  await page.getByRole("button", { name: "Ask" }).click();

  await expect(page.getByRole("heading", { name: "Cancun" })).toBeVisible();
  await expect(page.getByText("Dates: Flexible")).toBeVisible();
  await expect(page.getByText("Length: 7 days")).toBeVisible();
  await expect(page.getByText("Window: Next 6 months")).toBeVisible();
  await expect(page.locator(".MuiChip-label").filter({ hasText: "Cheapest flexible date" }).first()).toBeVisible();
});

test("narrow desktop uses a bottom-right chat popup instead of covering filters", async ({ page }) => {
  await page.setViewportSize({ width: 1080, height: 1000 });
  await page.goto("/");

  const findTrips = page.getByRole("button", { name: "Find trips" });
  await expect(findTrips).toBeVisible();
  const buttonText = await findTrips.innerText();
  expect(buttonText.replace(/\s+/g, " ").trim()).toBe("Find trips");
  await expect(page.getByTestId("chat-panel")).toHaveCount(0);

  await page.getByRole("button", { name: "Open chat" }).last().click();

  await expect(page.getByTestId("floating-chat")).toBeVisible();
  await expect(page.getByTestId("chat-panel")).toBeVisible();
  await expect(page.getByRole("button", { name: "Find trips" })).toBeVisible();
});
