# Sardis Playground

Interactive sandbox for testing Sardis payment infrastructure without signup or API keys.

## Overview

The Sardis Playground is a single-page HTML application that provides developers with a hands-on experience of the Sardis payment platform. It's designed as a key developer acquisition tool - no barriers, no signup, just instant exploration.

## Features

- **Execute Payments** - Simulate AI agent payments with real policy enforcement logic
- **Policy Builder** - Test spending policies against different trust levels
- **Virtual Card Issuance** - See how Sardis issues cards for AI agents
- **Audit Ledger** - Explore the append-only transaction log
- **Code Examples** - Copy-paste Python, TypeScript, and cURL snippets

## Architecture

```
playground/
├── index.html          # Self-contained single-page app
└── README.md          # This file
```

The playground is a standalone HTML file with:
- **No build step** - runs directly in browser
- **No dependencies** - uses Tailwind CSS CDN
- **Sandbox API backend** - connects to `/api/v2/sandbox` endpoints
- **In-memory data** - all demo data is ephemeral

## Running Locally

### Option 1: With Sardis API Server

1. Start the Sardis API server:
```bash
cd /path/to/sardis
uvicorn sardis_api.main:create_app --factory --port 8000
```

2. Open the playground:
```bash
cd playground
python3 -m http.server 3000
```

3. Visit http://localhost:3000

The playground will connect to `http://localhost:8000/api/v2/sandbox` for the backend.

### Option 2: Standalone (static HTML)

You can open `index.html` directly in a browser, but you'll need to update the API_BASE URL in the script section to point to a running Sardis API instance.

```html
<!-- Update this line in index.html -->
<script>
    const API_BASE = 'https://api.sardis.sh/api/v2/sandbox';
    // ... rest of code
</script>
```

## Sandbox API Endpoints

The playground uses these sandbox endpoints (no authentication required):

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v2/sandbox/payment` | POST | Simulate a payment with policy enforcement |
| `/api/v2/sandbox/policy-check` | POST | Test a payment against policy (dry-run) |
| `/api/v2/sandbox/create-wallet` | POST | Create an ephemeral demo wallet |
| `/api/v2/sandbox/issue-card` | POST | Simulate virtual card issuance |
| `/api/v2/sandbox/demo-data` | GET | Get pre-seeded agents, wallets, transactions |
| `/api/v2/sandbox/ledger` | GET | View audit ledger entries |
| `/api/v2/sandbox/reset` | DELETE | Reset sandbox to initial state |

## Pre-Seeded Demo Data

The sandbox automatically creates:
- **3 demo agents** with different trust levels (Low, Medium, High)
- **3 wallets** with USDC balances on Base Sepolia
- **10 sample transactions** across different merchants
- **2 virtual cards** for testing

## Interactive Tutorial

First-time visitors see a guided walkthrough:
1. Welcome & overview
2. Execute a payment
3. Test spending policies
4. Explore code examples

The tutorial can be restarted anytime by clicking "Start Interactive Tutorial".

## Customization

### Changing the Theme

The playground uses a deep purple/indigo dark theme matching sardis.sh branding. To customize:

```html
<!-- In the <script> tag under tailwind.config -->
<script>
    tailwind.config = {
        theme: {
            extend: {
                colors: {
                    sardis: {
                        // Customize these colors
                        500: '#8b5cf6',  // Primary
                        600: '#7c3aed',  // Primary hover
                        // ... etc
                    }
                }
            }
        }
    }
</script>
```

### Adding New Tabs

1. Add tab button in the tabs section:
```html
<button onclick="switchTab('mytab')" id="tab-mytab" class="...">
    My New Tab
</button>
```

2. Add tab content section:
```html
<div id="content-mytab" class="tab-content hidden">
    <!-- Your content here -->
</div>
```

3. Update the `switchTab()` function to include the new tab name.

## Deployment

### Vercel (Recommended)

```bash
# From the sardis root
vercel --prod
```

The playground will be available at `https://yourdomain.vercel.app/playground/`

### Netlify

```bash
# From playground directory
netlify deploy --prod --dir=.
```

### GitHub Pages

1. Push to a `gh-pages` branch
2. Enable GitHub Pages in repository settings
3. Playground available at `https://username.github.io/sardis/playground/`

### Self-Hosted

Simply serve the playground directory with any static file server:

```bash
# Python
python3 -m http.server 3000

# Node.js
npx serve .

# PHP
php -S localhost:3000
```

## Browser Compatibility

- **Chrome/Edge**: ✅ Full support
- **Firefox**: ✅ Full support
- **Safari**: ✅ Full support (iOS 14+)
- **Opera**: ✅ Full support

The playground uses modern JavaScript features (async/await, fetch) but no cutting-edge APIs. It works on all browsers from the last 2-3 years.

## Security Notes

- All data is **ephemeral** and resets on server restart
- No real blockchain transactions occur
- No API keys or credentials required
- Sandbox endpoints are **not rate-limited** (production endpoints are)
- Demo wallets have simulated balances only

**Production Warning**: The sandbox API should be disabled or heavily rate-limited in production deployments. It's designed for developer onboarding, not production use.

## Code Examples

### Execute a Payment (Python)

```python
import requests

response = requests.post("http://localhost:8000/api/v2/sandbox/payment", json={
    "agent_id": "agent_demo_001",
    "amount": 25.00,
    "merchant": "OpenAI API",
    "chain": "base_sepolia",
    "token": "USDC"
})

print(response.json())
```

### Check Policy (TypeScript)

```typescript
const response = await fetch("http://localhost:8000/api/v2/sandbox/policy-check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
        agent_id: "agent_demo_002",
        amount: 150.00,
        merchant: "AWS Compute"
    })
});

const result = await response.json();
console.log(result.would_allow ? "✓ Allowed" : "✗ Denied");
```

### View Ledger (cURL)

```bash
curl http://localhost:8000/api/v2/sandbox/ledger?limit=10
```

## Troubleshooting

### "Failed to fetch" errors

- Ensure the Sardis API server is running on port 8000
- Check that CORS is enabled in the API (it should be by default)
- Verify the API_BASE URL in index.html matches your server

### Tutorial not showing

- Clear localStorage: `localStorage.removeItem('sardis-tutorial-seen')`
- Refresh the page
- Or click "Start Interactive Tutorial" button

### Sandbox data not loading

- Check browser console for errors
- Verify `/api/v2/sandbox/demo-data` endpoint is accessible
- Try clicking "Reset" in the sandbox API to re-seed data

## Contributing

The playground is intentionally a single HTML file for simplicity. When making changes:

1. Test on multiple browsers (Chrome, Firefox, Safari)
2. Verify mobile responsiveness
3. Check that all API calls use safe DOM methods (no innerHTML with untrusted data)
4. Maintain the glassmorphism aesthetic

## License

Same as Sardis core - see LICENSE.txt in repository root.

## Support

- Documentation: https://sardis.sh/docs
- Issues: https://github.com/sardis/sardis/issues
- Discord: https://discord.gg/sardis

---

**Ready to go live?** Get production API keys at [sardis.sh](https://sardis.sh)
