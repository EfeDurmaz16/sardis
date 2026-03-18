---
name: deploy-all
description: Deploy all Sardis services (landing, dashboard, API)
disable-model-invocation: true
context: fork
agent: deploy-manager
---

Deploy all Sardis services in sequence:

1. Build and deploy landing page: cd landing && pnpm build && vercel --prod --yes
2. Build and deploy dashboard: cd dashboard && vercel --prod --yes
3. Verify API health: curl -s https://api.sardis.sh/health
4. Verify landing: curl -s -o /dev/null -w "%{http_code}" https://sardis.sh
5. Verify dashboard: curl -s -o /dev/null -w "%{http_code}" https://app.sardis.sh

Report status of each deployment.
