# Sardis Phase 2 Target Universe

## Scope

This file contains the structured 100-company target universe for Sardis Phase 2.

The list is built from the Phase 1 product thesis:

- Sardis is strongest as a governed payment execution and control layer for agents.
- The highest-confidence wedge is safe agent spend, not generic checkout replacement.
- The best targets are companies where agent workflows are moving closer to real purchases, financial actions, booking flows, card-like spend, procurement, or merchant checkout.

## Tracks

1. Agent platforms / agent builders
2. Internal enterprise AI and automation teams
3. Fintech / commerce / payment design partners
4. Commerce / marketplace / travel / procurement platforms

## Scoring

- `fit_score`: directness of Sardis to a real workflow pain
- `confidence_score`: confidence in the public signal and fit hypothesis
- `reachability_score`: odds of reaching the right buyer or champion
- `personalization_richness_score`: amount of public context available for custom outreach
- `pilot_likelihood_score`: odds of a near-term design-partner or pilot conversation

## Tiering Logic

- `Tier 1`: top 25 companies with the strongest blend of fit, pilot plausibility, and usable public context
- `Tier 2`: next 35 strong-fit companies with real relevance but more friction, lower reachability, or weaker immediacy
- `Tier 3`: final 40 broader but still defensible companies that are useful for testing message pull and adjacent ICP hypotheses

## Tier Mix

- `Tier 1`: 8 agent platforms, 3 internal enterprise AI teams, 8 fintech / payment partners, 6 commerce / procurement platforms
- `Tier 2`: 12 agent platforms, 10 internal enterprise AI teams, 8 fintech / payment partners, 5 commerce / procurement platforms
- `Tier 3`: 5 agent platforms, 12 internal enterprise AI teams, 9 fintech / payment partners, 14 commerce / procurement platforms

## Top 10 Immediate Priorities

1. LangChain
2. Stripe
3. Circle
4. Shopify
5. Zip
6. Workday
7. Lithic
8. Klarna
9. Relevance AI
10. Browserbase

## Recommended Sequencing

1. Start with `Tier 1` and split the first wave across all four tracks.
2. Do not over-index on the hyperscalers first. They are useful signal targets but weak learning targets.
3. Use the first 15 to 20 outbound attempts to test which framing gets the strongest response:
   - safe agent spend
   - approval and audit for financial actions
   - checkout and booking insertion points
   - procurement and travel control
4. Expand into `Tier 2` once reply patterns reveal whether Sardis pulls harder with builders, fintech design partners, or workflow-heavy commerce operators.

## Notes

- Some companies are strategically prestigious but harder pilot targets. Those remain in the universe, but they are tiered lower when reachability or pilot odds are weak.
- The CSV is the working dataset for Phase 3. It is the file to use when selecting companies for contact research and email drafting.

## Representative Source Basket

These are representative live sources used to shape the scoring and "why now" fields. They are not exhaustive.

- OpenAI agents tooling: https://openai.com/index/new-tools-for-building-agents/
- Salesforce Agentforce 2dx: https://investor.salesforce.com/news/news-details/2025/Salesforce-Launches-Agentforce-2dx-with-New-Capabilities-to-Embed-Proactive-Agentic-AI-into-Any-Workflow-Create-Multimodal-Experiences-and-Extend-Digital-Labor-Throughout-the-Enterprise/default.aspx
- ServiceNow AI Agent Orchestrator: https://www.servicenow.com/company/media/press-room/ai-agents-studio.html
- Google Gemini Enterprise: https://cloud.google.com/blog/products/ai-machine-learning/introducing-gemini-enterprise
- Stripe Agentic Commerce Suite: https://stripe.com/newsroom/news/stripe-launches-worlds-first-agentic-commerce-suite
- Visa Intelligent Commerce: https://usa.visa.com/about-visa/newsroom/press-releases.releaseId.20701.html
- Mastercard Agent Pay: https://www.mastercard.com/news/perspectives/2025/mastercard-agent-pay/
- DoorDash inside ChatGPT: https://about.doordash.com/en-us/news/doordash-app-within-chatgpt
