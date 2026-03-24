import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { SardisSpendWidget } from "../src/SardisSpendWidget";
import type { SpendingData } from "../src/types";

const mockData: SpendingData = {
  budget: { used: 750, total: 1000, period: "7d" },
  chart: [
    { date: "Mar 18", amount: 100 },
    { date: "Mar 19", amount: 120 },
    { date: "Mar 20", amount: 80 },
    { date: "Mar 21", amount: 150 },
    { date: "Mar 22", amount: 110 },
    { date: "Mar 23", amount: 90 },
    { date: "Mar 24", amount: 100 },
  ],
  transactions: [
    { id: "tx_1", date: "2026-03-24", recipient: "OpenAI", amount: 49.99, status: "completed" },
    { id: "tx_2", date: "2026-03-23", recipient: "AWS", amount: 120.0, status: "completed" },
    {
      id: "tx_3",
      date: "2026-03-23",
      recipient: "Unknown Vendor",
      amount: 5000.0,
      status: "blocked",
      explanation: {
        checks_failed: ["exceeds_per_transaction_limit", "merchant_not_in_allowlist"],
        suggested_action: "Increase per-transaction limit or add vendor to allowlist",
      },
    },
  ],
};

function mockFetchSuccess(data: SpendingData) {
  return vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(data),
  });
}

function mockFetchError(status: number, statusText: string) {
  return vi.fn().mockResolvedValue({
    ok: false,
    status,
    statusText,
  });
}

describe("SardisSpendWidget", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("renders with valid props and shows data", async () => {
    global.fetch = mockFetchSuccess(mockData) as unknown as typeof fetch;

    render(<SardisSpendWidget agentId="agt_test" apiKey="sk_test" />);

    expect(screen.getByTestId("loading-skeleton")).toBeTruthy();

    await waitFor(() => {
      expect(screen.getByText(/\$750/)).toBeTruthy();
    });

    expect(screen.getByText("OpenAI")).toBeTruthy();
    expect(screen.getByText("AWS")).toBeTruthy();
  });

  it("shows empty state with no data", async () => {
    const emptyData: SpendingData = {
      budget: { used: 0, total: 1000, period: "7d" },
      chart: [],
      transactions: [],
    };
    global.fetch = mockFetchSuccess(emptyData) as unknown as typeof fetch;

    render(<SardisSpendWidget agentId="agt_test" apiKey="sk_test" />);

    await waitFor(() => {
      expect(screen.getByText("No transactions yet")).toBeTruthy();
    });
  });

  it("shows loading skeleton", () => {
    global.fetch = vi.fn().mockReturnValue(new Promise(() => {})) as unknown as typeof fetch;

    render(<SardisSpendWidget agentId="agt_test" apiKey="sk_test" />);
    expect(screen.getByTestId("loading-skeleton")).toBeTruthy();
  });

  it("handles API error", async () => {
    global.fetch = mockFetchError(500, "Internal Server Error") as unknown as typeof fetch;

    render(<SardisSpendWidget agentId="agt_test" apiKey="sk_test" />);

    await waitFor(() => {
      expect(screen.getByText("HTTP 500: Internal Server Error")).toBeTruthy();
    });
  });

  it("applies dark theme", async () => {
    global.fetch = mockFetchSuccess(mockData) as unknown as typeof fetch;

    render(<SardisSpendWidget agentId="agt_test" apiKey="sk_test" theme="dark" />);

    await waitFor(() => {
      const widget = screen.getByTestId("sardis-spend-widget");
      expect(widget.style.backgroundColor).toBe("rgb(26, 26, 26)");
    });
  });

  it("applies light theme by default", async () => {
    global.fetch = mockFetchSuccess(mockData) as unknown as typeof fetch;

    render(<SardisSpendWidget agentId="agt_test" apiKey="sk_test" />);

    await waitFor(() => {
      const widget = screen.getByTestId("sardis-spend-widget");
      expect(widget.style.backgroundColor).toBe("rgb(255, 255, 255)");
    });
  });

  it("passes correct URL and headers to fetch", async () => {
    global.fetch = mockFetchSuccess(mockData) as unknown as typeof fetch;

    render(
      <SardisSpendWidget
        agentId="agt_123"
        apiKey="sk_my_key"
        period="30d"
        baseUrl="https://api.sardis.sh/v2"
      />,
    );

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "https://api.sardis.sh/v2/agents/agt_123/spending?period=30d",
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer sk_my_key",
          }),
        }),
      );
    });
  });
});
