/* ============================================================
   Sardis Canvas — shared nav + theme toggle
   Built with DOM APIs (no innerHTML) for CSP-safe injection.
   ============================================================ */

(function () {
  // ---------- Sidebar scroll persistence (UX) ----------
  // Preserve sidebar scroll position across page navigations so the user
  // doesn't get teleported to the top of the nav on every click.
  const SIDEBAR_SCROLL_KEY = "sardis-canvas-sidebar-scroll";
  function saveSidebarScroll() {
    const el = document.querySelector("[data-canvas-sidebar]");
    if (el) {
      try { sessionStorage.setItem(SIDEBAR_SCROLL_KEY, String(el.scrollTop)); } catch (_) {}
    }
  }
  function restoreSidebarScroll() {
    const el = document.querySelector("[data-canvas-sidebar]");
    if (!el) return;
    try {
      const v = sessionStorage.getItem(SIDEBAR_SCROLL_KEY);
      if (v != null) el.scrollTop = parseInt(v, 10) || 0;
    } catch (_) {}
  }
  window.addEventListener("beforeunload", saveSidebarScroll);
  window.addEventListener("pagehide", saveSidebarScroll);

  // ---------- Sidebar collapse state ----------
  const SIDEBAR_COLLAPSED_KEY = "sardis-canvas-sidebar-collapsed";
  function setSidebarCollapsed(collapsed) {
    if (!document.body) return;
    document.body.classList.toggle("sardis-sidebar-collapsed", collapsed);
    // Also mirror on .canvas-page for any legacy selectors
    const page = document.querySelector("[data-canvas-page]");
    if (page) page.classList.toggle("sidebar-collapsed", collapsed);
    try { localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? "1" : "0"); } catch (_) {}
  }
  function initSidebarCollapsedFromStorage() {
    let stored = null;
    try { stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY); } catch (_) {}
    setSidebarCollapsed(stored === "1");
  }
  window.__sardisToggleSidebar = function () {
    const isCollapsed = document.body.classList.contains("sardis-sidebar-collapsed");
    setSidebarCollapsed(!isCollapsed);
  };
  // Cmd/Ctrl + \ keyboard shortcut
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "\\") {
      e.preventDefault();
      window.__sardisToggleSidebar();
    }
  });

  // ---------- Theme ----------
  const STORAGE_KEY = "sardis-canvas-theme";
  function applyTheme(t) {
    document.documentElement.setAttribute("data-theme", t);
    try {
      localStorage.setItem(STORAGE_KEY, t);
    } catch (_) {}
  }
  function initTheme() {
    let t = null;
    try { t = localStorage.getItem(STORAGE_KEY); } catch (_) {}
    if (!t) t = "dark";
    applyTheme(t);
  }
  window.__sardisToggleTheme = function () {
    const cur = document.documentElement.getAttribute("data-theme") || "light";
    applyTheme(cur === "dark" ? "light" : "dark");
  };
  initTheme();

  // ---------- Canvas registry ----------
  const CANVASES = [
    {
      id: "index",
      num: "00",
      group: "Overview",
      title: "Canvas Index",
      desc: "Navigation hub.",
      href: "/",
    },
    {
      id: "manifesto",
      num: "M",
      group: "Overview",
      title: "Manifesto",
      desc: "The missing substrate for trustworthy agents.",
      href: "/manifesto",
      starred: true,
    },
    {
      id: "architecture",
      num: "01",
      group: "System",
      title: "Architecture Overview",
      desc: "Layered system view — SDK to chain.",
      href: "/architecture",
      starred: true,
    },
    {
      id: "repo-structure",
      num: "02",
      group: "System",
      title: "Repo Structure",
      desc: "Folder-by-folder tree.",
      href: "/repo-structure",
    },
    {
      id: "packages",
      num: "03",
      group: "System",
      title: "Packages (51)",
      desc: "Every package, purpose, key files.",
      href: "/packages",
    },
    {
      id: "api-surface",
      num: "04",
      group: "Backend",
      title: "API Surface",
      desc: "123 routers grouped by domain.",
      href: "/api-surface",
    },
    {
      id: "database",
      num: "05",
      group: "Backend",
      title: "Database Schema",
      desc: "107 migrations, core tables.",
      href: "/database",
    },
    {
      id: "contracts",
      num: "06",
      group: "Backend",
      title: "Smart Contracts",
      desc: "9 Solidity contracts.",
      href: "/contracts",
    },
    {
      id: "payment-flow",
      num: "07",
      group: "Flows",
      title: "Payment Flow",
      desc: "End-to-end agent payment execution.",
      href: "/payment-flow",
    },
    {
      id: "policy-engine",
      num: "08",
      group: "Flows",
      title: "Policy Engine",
      desc: "Spending policies + mandates + NL.",
      href: "/policy-engine",
    },
    {
      id: "wallet-mpc",
      num: "09",
      group: "Flows",
      title: "Wallet + MPC",
      desc: "Non-custodial wallet infra.",
      href: "/wallet-mpc",
    },
    {
      id: "settlement",
      num: "10",
      group: "Flows",
      title: "Settlement & Chains",
      desc: "Multi-chain, CCTP, Tempo, paymaster.",
      href: "/settlement",
    },
    {
      id: "checkout",
      num: "11",
      group: "Product",
      title: "Checkout & Merchants",
      desc: "Pay with Sardis + Sardis Connect.",
      href: "/checkout",
    },
    {
      id: "compliance",
      num: "12",
      group: "Product",
      title: "Compliance Stack",
      desc: "KYC (Didit) + AML (Elliptic).",
      href: "/compliance",
    },
    {
      id: "protocols",
      num: "13",
      group: "Product",
      title: "Protocol Gateway",
      desc: "AP2, TAP, x402, A2A.",
      href: "/protocols",
    },
    {
      id: "sdks",
      num: "14",
      group: "Product",
      title: "SDKs & CLIs",
      desc: "Python, JS, CLI, MCP, n8n.",
      href: "/sdks",
    },
    {
      id: "integrations",
      num: "15",
      group: "Product",
      title: "AI Framework Integrations",
      desc: "18 framework adapters.",
      href: "/integrations",
    },
    {
      id: "external",
      num: "17",
      group: "Ops",
      title: "External Services",
      desc: "25+ third-party integrations.",
      href: "/external",
    },
    {
      id: "cicd",
      num: "18",
      group: "Ops",
      title: "CI/CD & Deployment",
      desc: "24 GitHub Actions, Cloud Run, Vercel.",
      href: "/cicd",
    },
    {
      id: "security",
      num: "19",
      group: "Ops",
      title: "Security Model",
      desc: "Trust boundaries + threat model.",
      href: "/security",
    },
    {
      id: "protocol-objects",
      num: "20",
      group: "Protocol",
      title: "Protocol Objects (10)",
      desc: "Agent Certificate, Spending Mandate, FundingCell, Payment Object…",
      href: "/protocol-objects",
      starred: true,
    },
    {
      id: "state-machine",
      num: "21",
      group: "Protocol",
      title: "22-State Machine",
      desc: "Full payment lifecycle — issue through settle, escrow, dispute.",
      href: "/state-machine",
      starred: true,
    },
    {
      id: "dual-rail",
      num: "22",
      group: "Protocol",
      title: "Dual-Rail Architecture",
      desc: "Internal ledger as primary rail; external rails as on/off-ramps.",
      href: "/dual-rail",
      starred: true,
    },
    {
      id: "credit",
      num: "23",
      group: "Extended",
      title: "Agent Credit",
      desc: "Facility Gate — non-custodial credit authority for agents.",
      href: "/credit",
      isNew: true,
    },
    {
      id: "sardis-connect",
      num: "24",
      group: "Extended",
      title: "Sardis Connect",
      desc: "Zero-crypto merchant SDK — USD in, stablecoin handled.",
      href: "/sardis-connect",
      starred: true,
    },
    {
      id: "osp-integration",
      num: "25",
      group: "Extended",
      title: "OSP Integration",
      desc: "Open Service Protocol — agents pay for services end-to-end.",
      href: "/osp-integration",
    },
    {
      id: "zk-privacy",
      num: "26",
      group: "Extended",
      title: "ZK Privacy Stack",
      desc: "Noir circuits, ZK policy proofs, 3 privacy tiers.",
      href: "/zk-privacy",
    },
  ];
  window.__sardisCanvases = CANVASES;

  // ---------- DOM helpers ----------
  function h(tag, attrs, children) {
    const el = document.createElement(tag);
    if (attrs) {
      for (const k in attrs) {
        if (k === "class") el.className = attrs[k];
        else if (k === "onclick") el.addEventListener("click", attrs[k]);
        else el.setAttribute(k, attrs[k]);
      }
    }
    if (children != null) {
      const arr = Array.isArray(children) ? children : [children];
      for (const c of arr) {
        if (c == null) continue;
        el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
      }
    }
    return el;
  }
  function svgEl(tag, attrs) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    if (attrs) for (const k in attrs) el.setAttribute(k, attrs[k]);
    return el;
  }

  function logo() {
    const svg = svgEl("svg", {
      width: "22",
      height: "22",
      viewBox: "0 0 28 28",
      fill: "none",
      "aria-hidden": "true",
    });
    svg.appendChild(
      svgEl("path", {
        d: "M20 5H10a7 7 0 000 14h2",
        stroke: "currentColor",
        "stroke-width": "3",
        "stroke-linecap": "round",
        fill: "none",
      }),
    );
    svg.appendChild(
      svgEl("path", {
        d: "M8 23h10a7 7 0 000-14h-2",
        stroke: "currentColor",
        "stroke-width": "3",
        "stroke-linecap": "round",
        fill: "none",
      }),
    );
    return svg;
  }

  function sunIcon() {
    const svg = svgEl("svg", {
      width: "14",
      height: "14",
      viewBox: "0 0 24 24",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
    });
    svg.appendChild(svgEl("circle", { cx: "12", cy: "12", r: "4" }));
    svg.appendChild(
      svgEl("path", {
        d: "M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41",
      }),
    );
    return svg;
  }

  function renderSidebar() {
    const el = document.querySelector("[data-canvas-sidebar]");
    if (!el) return;
    const currentId = el.dataset.current || "";
    // Detect whether we're on the root index.html (no /pages/ segment in path)
    // and rewrite hrefs accordingly so the sidebar works from both root and /pages/.
    // Astro clean routes — no prefix logic.
    const pagePrefix = "";
    const indexHref = "/";

    // Collapse toggle (desktop, inside brand row)
    const cbSvg = svgEl("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": "2", "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true" });
    cbSvg.appendChild(svgEl("polyline", { points: "15 18 9 12 15 6" }));
    const collapseBtn = h("button", {
      class: "sidebar-collapse-btn",
      "aria-label": "Hide navigation",
      title: "Hide navigation (⌘\\)",
      onclick: () => setSidebarCollapsed(true),
    }, [cbSvg]);

    // Brand (with collapse button on the right)
    const brand = h("div", { class: "brand" }, [
      logo(),
      h("div", null, [
        h("div", { class: "brand-name" }, "Sardis"),
        h("div", { class: "text-xs text-muted text-mono" }, "Canvas"),
      ]),
      collapseBtn,
    ]);
    el.appendChild(brand);

    // Index link
    const indexLink = h(
      "a",
      {
        class: "nav-item" + (currentId === "index" ? " active" : ""),
        href: indexHref,
      },
      "Canvas Index",
    );
    el.appendChild(indexLink);

    // Groups
    const groups = {};
    for (const c of CANVASES) {
      if (c.id === "index") continue;
      (groups[c.group] ||= []).push(c);
    }
    for (const [group, items] of Object.entries(groups)) {
      const g = h("div", { class: "nav-group" });
      g.appendChild(h("div", { class: "nav-group-title" }, group));
      for (const c of items) {
        const numSpan = h(
          "span",
          { class: "text-mono text-xs text-faint", style: "margin-right:8px" },
          c.num,
        );
        const starSpan = c.starred
          ? h("span", { class: "nav-star", title: "Recommended", "aria-hidden": "true" }, "★")
          : null;
        const newSpan = c.isNew
          ? h("span", { class: "nav-new", title: "New" }, "NEW")
          : null;
        const children = [numSpan, c.title];
        if (newSpan) children.push(newSpan);
        if (starSpan) children.push(starSpan);
        const a = h(
          "a",
          {
            class: "nav-item" + (c.id === currentId ? " active" : "") + (c.starred || c.isNew ? " nav-item-starred" : ""),
            href: c.href,
          },
          children,
        );
        g.appendChild(a);
      }
      el.appendChild(g);
    }

    // External
    const ext = h("div", { class: "nav-group" });
    ext.appendChild(h("div", { class: "nav-group-title" }, "External"));
    ext.appendChild(
      h(
        "a",
        {
          class: "nav-item",
          href: "https://sardis.sh",
          target: "_blank",
          rel: "noopener",
        },
        "sardis.sh ↗",
      ),
    );
    ext.appendChild(
      h(
        "a",
        {
          class: "nav-item",
          href: "https://docs.sardis.sh",
          target: "_blank",
          rel: "noopener",
        },
        "Docs ↗",
      ),
    );
    ext.appendChild(
      h(
        "a",
        {
          class: "nav-item",
          href: "https://github.com/EfeDurmaz16",
          target: "_blank",
          rel: "noopener",
        },
        "GitHub ↗",
      ),
    );
    el.appendChild(ext);

    // Theme toggle
    const toggleWrap = h("div", {
      class: "nav-group",
      style:
        "margin-top:24px; padding-top:16px; border-top:1px solid var(--border)",
    });
    const btn = h(
      "button",
      {
        class: "theme-toggle",
        title: "Toggle theme",
        style: "margin-left:8px",
        onclick: () => window.__sardisToggleTheme(),
      },
      [sunIcon()],
    );
    toggleWrap.appendChild(btn);
    el.appendChild(toggleWrap);
  }

  function renderIndexGrid() {
    const el = document.querySelector("[data-canvas-grid]");
    if (!el) return;
    for (const c of CANVASES) {
      if (c.id === "index") continue;
      const card = h("a", { class: "canvas-card", href: c.href }, [
        h("div", { class: "canvas-card-num" }, [
          c.num + " · " + c.group,
          c.isNew ? h("span", { class: "canvas-card-badge" }, "NEW") : null,
        ]),
        h("div", { class: "canvas-card-title" }, c.title),
        h("div", { class: "canvas-card-desc" }, c.desc),
      ]);
      el.appendChild(card);
    }
  }

  function initPage() {
    const sidebarEl = document.querySelector("[data-canvas-sidebar]");
    if (sidebarEl && !sidebarEl.querySelector(".brand")) {
      renderSidebar();
    } else {
      updateSidebarActive();
    }
    renderIndexGrid();
    restoreSidebarScroll();

    if (sidebarEl && !sidebarEl.__sardisClickBound) {
      sidebarEl.__sardisClickBound = true;
      sidebarEl.addEventListener("click", function (e) {
        const a = e.target.closest("a[href]");
        if (a && !a.target) {
          saveSidebarScroll();
          closeMobileMenu();
        }
      });
    }

    // Mobile menu toggle — bind once
    const btn = document.querySelector("[data-mobile-menu-btn]");
    const scrim = document.querySelector("[data-sidebar-scrim]");
    if (btn && !btn.__sardisBound) {
      btn.__sardisBound = true;
      btn.addEventListener("click", openMobileMenu);
    }
    if (scrim && !scrim.__sardisBound) {
      scrim.__sardisBound = true;
      scrim.addEventListener("click", closeMobileMenu);
    }

    // Desktop sidebar open button (shown when collapsed)
    const openBtn = document.querySelector("[data-sidebar-open]");
    if (openBtn && !openBtn.__sardisBound) {
      openBtn.__sardisBound = true;
      openBtn.addEventListener("click", () => setSidebarCollapsed(false));
    }
    initSidebarCollapsedFromStorage();
  }

  function openMobileMenu() {
    const s = document.querySelector("[data-canvas-sidebar]");
    const sc = document.querySelector("[data-sidebar-scrim]");
    if (s) s.classList.add("is-open");
    if (sc) sc.classList.add("is-open");
    document.body.style.overflow = "hidden";
  }
  function closeMobileMenu() {
    const s = document.querySelector("[data-canvas-sidebar]");
    const sc = document.querySelector("[data-sidebar-scrim]");
    if (s) s.classList.remove("is-open");
    if (sc) sc.classList.remove("is-open");
    document.body.style.overflow = "";
  }

  function updateSidebarActive() {
    const el = document.querySelector("[data-canvas-sidebar]");
    if (!el) return;
    const path = window.location.pathname.replace(/\/$/, "") || "/";
    el.querySelectorAll(".nav-item").forEach((a) => {
      const href = a.getAttribute("href");
      if (!href || href.startsWith("http")) return;
      const matches = href === path || (path === "" && href === "/");
      a.classList.toggle("active", matches);
    });
  }

  document.addEventListener("DOMContentLoaded", initPage);
  // Astro View Transitions fire astro:page-load on every client-side nav.
  document.addEventListener("astro:page-load", initPage);
  document.addEventListener("astro:before-swap", saveSidebarScroll);
})();
