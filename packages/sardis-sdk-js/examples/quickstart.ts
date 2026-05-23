// Legacy quickstart corpus.
//
// Used by packages/sardis-js/__tests__/migrate.test.ts as input for verifying
// the sardis-migrate codemod rewrites pre-v2 imports to the unified SDK.
//
// Run: npx sardis-migrate
//
// Migration target:
//   import { Sardis } from "sardis"
//   const sardis = new Sardis({ apiKey })

import { SardisClient } from '@sardis/sdk';
import { createSardisTools } from '@sardis/ai-sdk';

const client = new SardisClient({ apiKey: process.env.SARDIS_API_KEY! });
const tools = createSardisTools({ client });

export { client, tools };
