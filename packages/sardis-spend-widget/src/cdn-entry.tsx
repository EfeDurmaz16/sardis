import { createElement } from "react";
import { createRoot } from "react-dom/client";
import { SardisSpendWidget } from "./SardisSpendWidget";

class SardisSpendWidgetElement extends HTMLElement {
  private root: ReturnType<typeof createRoot> | null = null;

  connectedCallback() {
    const shadow = this.attachShadow({ mode: "open" });
    const container = document.createElement("div");
    shadow.appendChild(container);

    this.root = createRoot(container);
    this.render();
  }

  disconnectedCallback() {
    this.root?.unmount();
    this.root = null;
  }

  static get observedAttributes() {
    return ["agent-id", "api-key", "theme", "height", "period", "base-url"];
  }

  attributeChangedCallback() {
    this.render();
  }

  private render() {
    if (!this.root) return;

    const agentId = this.getAttribute("agent-id") ?? "";
    const apiKey = this.getAttribute("api-key") ?? "";
    const theme = (this.getAttribute("theme") as "light" | "dark") ?? "light";
    const height = Number(this.getAttribute("height")) || 400;
    const period = (this.getAttribute("period") as "7d" | "30d") ?? "7d";
    const baseUrl = this.getAttribute("base-url") ?? "/api/v2";

    this.root.render(
      createElement(SardisSpendWidget, { agentId, apiKey, theme, height, period, baseUrl }),
    );
  }
}

if (typeof customElements !== "undefined" && !customElements.get("sardis-spend-widget")) {
  customElements.define("sardis-spend-widget", SardisSpendWidgetElement);
}
