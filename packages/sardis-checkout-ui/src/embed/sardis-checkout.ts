/**
 * Sardis Checkout Embed SDK
 *
 * Usage:
 *   <script src="https://checkout.sardis.sh/sardis-checkout.js"></script>
 *   <script>
 *     SardisCheckout.open({
 *       sessionId: "mcs_...",
 *       onSuccess: (data) => console.log("Paid!", data),
 *       onCancel: () => console.log("Cancelled"),
 *     });
 *   </script>
 *
 * Or as a web component:
 *   <sardis-pay session-id="mcs_..." />
 */

const CHECKOUT_BASE =
  (typeof window !== "undefined" &&
    (window as unknown as Record<string, unknown>).__SARDIS_CHECKOUT_URL__) ||
  "https://checkout.sardis.sh";

interface OpenOptions {
  sessionId: string;
  onSuccess?: (data: { session_id: string; tx_hash?: string }) => void;
  onCancel?: () => void;
}

let overlay: HTMLDivElement | null = null;

function open(opts: OpenOptions) {
  if (overlay) close();

  overlay = document.createElement("div");
  overlay.id = "sardis-checkout-overlay";
  Object.assign(overlay.style, {
    position: "fixed",
    inset: "0",
    zIndex: "999999",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "rgba(0,0,0,0.5)",
    backdropFilter: "blur(4px)",
  } as CSSStyleDeclaration);

  // Close button
  const closeBtn = document.createElement("button");
  closeBtn.textContent = "\u00D7"; // multiplication sign (×)
  Object.assign(closeBtn.style, {
    position: "absolute",
    top: "16px",
    right: "16px",
    width: "36px",
    height: "36px",
    borderRadius: "50%",
    background: "rgba(255,255,255,0.9)",
    border: "none",
    fontSize: "20px",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#18181B",
    fontFamily: "system-ui",
  } as CSSStyleDeclaration);
  closeBtn.addEventListener("click", () => {
    close();
    opts.onCancel?.();
  });

  // Iframe
  const iframe = document.createElement("iframe");
  iframe.src = `${CHECKOUT_BASE}/${opts.sessionId}`;
  Object.assign(iframe.style, {
    width: "420px",
    maxWidth: "95vw",
    height: "640px",
    maxHeight: "90vh",
    border: "none",
    borderRadius: "12px",
    boxShadow: "0 25px 50px rgba(0,0,0,0.25)",
    background: "white",
  } as CSSStyleDeclaration);

  overlay.appendChild(closeBtn);
  overlay.appendChild(iframe);
  document.body.appendChild(overlay);

  // Close on overlay click
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) {
      close();
      opts.onCancel?.();
    }
  });

  // Close on Escape
  const onKey = (e: KeyboardEvent) => {
    if (e.key === "Escape") {
      close();
      opts.onCancel?.();
      document.removeEventListener("keydown", onKey);
    }
  };
  document.addEventListener("keydown", onKey);

  // Listen for postMessage from iframe
  const onMessage = (e: MessageEvent) => {
    if (e.data?.source !== "sardis-checkout") return;
    if (e.data.event === "success") {
      opts.onSuccess?.({
        session_id: e.data.session_id,
        tx_hash: e.data.tx_hash,
      });
      close();
      window.removeEventListener("message", onMessage);
    }
  };
  window.addEventListener("message", onMessage);
}

function close() {
  if (overlay) {
    overlay.remove();
    overlay = null;
  }
}

// Web component: <sardis-pay session-id="mcs_..." />
class SardisPayElement extends HTMLElement {
  connectedCallback() {
    const sessionId = this.getAttribute("session-id");
    if (!sessionId) return;

    const btn = document.createElement("button");
    btn.textContent = "Pay with Sardis";
    Object.assign(btn.style, {
      padding: "12px 24px",
      background: "#2563EB",
      color: "white",
      border: "none",
      borderRadius: "8px",
      fontSize: "14px",
      fontWeight: "500",
      cursor: "pointer",
      fontFamily: "system-ui, sans-serif",
    } as CSSStyleDeclaration);
    btn.addEventListener("click", () => {
      open({
        sessionId,
        onSuccess: (data) => {
          this.dispatchEvent(
            new CustomEvent("sardis-success", { detail: data }),
          );
        },
        onCancel: () => {
          this.dispatchEvent(new CustomEvent("sardis-cancel"));
        },
      });
    });
    this.appendChild(btn);
  }
}

if (
  typeof customElements !== "undefined" &&
  !customElements.get("sardis-pay")
) {
  customElements.define("sardis-pay", SardisPayElement);
}

// Expose on window
const SardisCheckout = { open, close };
(window as unknown as Record<string, unknown>).SardisCheckout = SardisCheckout;
export default SardisCheckout;
