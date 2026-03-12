# Sardis Phase 3 Tier 1 Contact Map

## Scope

- `companies_covered`: 25
- `contact_rows`: 73
- `goal`: identify the best primary, secondary, and tertiary contact paths for the 25 Tier 1 accounts before drafting outreach

## Method

- Reused the Tier 1 scoring model from Phase 2 and added ranked contacts inside each account.
- Preferred official leadership pages, official product announcements, and official blog posts where possible.
- Used The Org, LinkedIn profiles, or credible external interviews only when official pages were weak or missing.
- Marked email availability conservatively. No guessed addresses were added.

## Source Quality

- `high`: official company leadership page, newsroom item, product post, or founder site
- `medium`: public org chart, LinkedIn profile, investor or media interview, or reputable third-party coverage

## Most Actionable Primary Contacts

- `Lindy`: Flo Crivello, Founder and CEO | contact_priority `10` | reachability `9` | pilot `9`
- `Zip`: Rujul Zaparde, Co-founder and Chief Executive Officer | contact_priority `10` | reachability `8` | pilot `9`
- `CrewAI`: João Moura, Founder and CEO | contact_priority `10` | reachability `8` | pilot `8`
- `Navan`: Michael Sindicich, President, Navan Expense | contact_priority `10` | reachability `8` | pilot `8`
- `LangChain`: Harrison Chase, Co-founder and CEO | contact_priority `10` | reachability `7` | pilot `8`
- `Shopify`: Vanessa Lee, Vice President of Product and General Manager, B2B and Retail | contact_priority `10` | reachability `6` | pilot `7`
- `Stripe`: Ahmed Gharib, Product Lead, Agentic Commerce | contact_priority `10` | reachability `5` | pilot `7`
- `Gumloop`: Max Brodeur-Urbas, Co-founder and CEO | contact_priority `9` | reachability `9` | pilot `9`
- `Browserbase`: Paul Klein IV, Co-founder and CEO | contact_priority `9` | reachability `8` | pilot `8`
- `Relevance AI`: Daniel Vassilev, Co-founder | contact_priority `9` | reachability `8` | pilot `8`

## Strategic But Slower Accounts

- `Shopify`: Vanessa Lee, Vice President of Product and General Manager, B2B and Retail | reachability `6` | note: strong strategic fit but likely longer-cycle enterprise motion
- `Stripe`: Ahmed Gharib, Product Lead, Agentic Commerce | reachability `5` | note: strong strategic fit but likely longer-cycle enterprise motion
- `Circle`: Nikhil Chandhok, Chief Product and Technology Officer | reachability `6` | note: strong strategic fit but likely longer-cycle enterprise motion
- `Expedia Group`: Xavier Amatriain, Chief AI and Data Officer | reachability `6` | note: strong strategic fit but likely longer-cycle enterprise motion
- `Klarna`: Yaron Shaer, Chief Technology Officer | reachability `6` | note: strong strategic fit but likely longer-cycle enterprise motion
- `Coinbase`: Rob Witoff, Vice President, Platform | reachability `5` | note: strong strategic fit but likely longer-cycle enterprise motion
- `SAP`: Philipp Herzig, Chief AI Officer and Chief Technology Officer | reachability `5` | note: strong strategic fit but likely longer-cycle enterprise motion
- `Marqeta`: Rahul Shah, Chief Product and Engineering Officer | reachability `6` | note: strong strategic fit but likely longer-cycle enterprise motion

## Email Availability

- `public_direct`: Lindy
- `public_routing_only`: Browserbase, Circle
- `not_publicly_confirmed`: all remaining contacts

## Open Gaps

- `Gumloop` and `Circle` currently have only two strong public people mapped. A third contact path would need more manual digging or a data provider.
- `LangChain`, `Lindy`, `Lithic`, `Highnote`, and `Unit` lean partly on The Org or LinkedIn for non-founder contacts because official leadership pages are thin.
- Direct email coverage is intentionally sparse. Most buyer and champion emails are not publicly confirmed, so Phase 4 should start with the best 10 to 15 contacts and enrich emails carefully rather than forcing full coverage for all 73 rows.

## Recommended Next Sequencing

- Draft initial outbound first for the 10 most actionable primaries where workflow fit and personalization are strongest.
- Use founder-led messaging for early-stage agent builders and workflow-led messaging for procurement, travel, and commerce platforms.
- Delay direct outreach to the largest enterprise logos until email coverage is stronger or a warmer route is available.

## Files

- `research/phase3-tier1-contact-map.csv`: detailed row-level contact map
- `research/phase3-tier1-contact-map.md`: short operating summary
- `research/phase3-top10-multithread-contact-map.csv`: deeper contact coverage for the 10 most actionable Tier 1 accounts
- `research/phase3-top10-multithread-contact-map.md`: summary of the multithread contact set and public contact paths
