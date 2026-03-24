import { source } from '@/lib/source';

export const revalidate = false;

export function GET() {
  const pages = source.getPages();

  const content = [
    '# Sardis Documentation',
    '',
    '> Sardis is the Payment OS for the Agent Economy — infrastructure enabling AI agents to make real financial transactions safely through non-custodial MPC wallets with natural language spending policies.',
    '',
    '## Documentation Pages',
    '',
    ...pages.map((page) => {
      const url = `https://docs.sardis.sh${page.url}`;
      const title = page.data.title;
      const desc = page.data.description ?? '';
      return `- [${title}](${url}): ${desc}`;
    }),
    '',
    '## Full Content',
    '',
    'For the full documentation content suitable for LLM consumption, see:',
    '- [llms-full.txt](https://docs.sardis.sh/llms-full.txt)',
  ].join('\n');

  return new Response(content, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
    },
  });
}
