// Legacy quickstart corpus.
// Used by migrate.test.ts as input for the sardis-migrate codemod.
import { SardisClient } from '@sardis/sdk';
import { createSardisTools } from '@sardis/ai-sdk';

const client = new SardisClient({ apiKey: process.env.SARDIS_API_KEY! });
const tools = createSardisTools({ client });

export { client, tools };
