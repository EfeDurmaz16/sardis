/**
 * Quickstart example (legacy @sardis/sdk).
 *
 * Used by packages/sardis-js/__tests__/migrate.test.ts as corpus for
 * verifying the `sardis-migrate` codemod rewrites legacy imports.
 *
 * Migration target:
 *   import { Sardis } from "sardis"
 *   const sardis = new Sardis({ apiKey })
 */
import { SardisClient } from "@sardis/sdk"
import { createSardisTools } from "@sardis/ai-sdk"

const client = new SardisClient({ apiKey: process.env.SARDIS_API_KEY! })
const tools = createSardisTools({ client })

export { client, tools }
