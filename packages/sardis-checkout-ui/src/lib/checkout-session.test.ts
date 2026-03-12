import { describe, expect, it } from "vitest";
import {
  buildDemoUrlWithClientSecret,
  getPreferredCheckoutTab,
  isInternalSardisWalletEnabled,
  resolvePersistedDemoClientSecret,
  stripDemoClientSecret,
} from "./checkout-session";

describe("checkout-session helpers", () => {
  it("prefers the client secret already present in the URL", () => {
    expect(
      resolvePersistedDemoClientSecret("?client_secret=cs_live", "cs_stored"),
    ).toBe("cs_live");
  });

  it("falls back to the stored client secret when the URL is empty", () => {
    expect(resolvePersistedDemoClientSecret("", "cs_stored")).toBe("cs_stored");
  });

  it("adds the demo client secret to the current URL", () => {
    expect(
      buildDemoUrlWithClientSecret("/demo", "?foo=bar", "cs_live"),
    ).toBe("/demo?foo=bar&client_secret=cs_live");
  });

  it("strips the demo client secret without touching other params", () => {
    expect(
      stripDemoClientSecret("/demo", "?foo=bar&client_secret=cs_live"),
    ).toBe("/demo?foo=bar");
  });

  it("keeps the internal Sardis wallet hidden unless the new flag is enabled", () => {
    expect(isInternalSardisWalletEnabled(undefined)).toBe(false);
    expect(isInternalSardisWalletEnabled("false")).toBe(false);
    expect(isInternalSardisWalletEnabled("true")).toBe(true);
  });

  it("prefers the fund tab for externally verified wallets", () => {
    expect(
      getPreferredCheckoutTab({
        payment_method: "external_wallet",
        payer_wallet_address: "0xabc",
      }),
    ).toBe("fund");
    expect(getPreferredCheckoutTab({})).toBe("wallet");
  });
});
