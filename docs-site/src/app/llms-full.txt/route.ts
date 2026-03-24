import { source } from '@/lib/source';

export const revalidate = false;

export function GET() {
  const pages = source.getPages();

  const sections = pages.map((page) => {
    const title = page.data.title;
    const description = page.data.description ?? '';
    const url = `https://docs.sardis.sh${page.url}`;

    // Get the raw MDX content from the page
    const content = page.data.structuredData?.contents
      ?.map((c: { content: string }) => c.content)
      .join('\n\n') ?? '';

    return [
      `# ${title}`,
      '',
      `> ${description}`,
      `> URL: ${url}`,
      '',
      content,
      '',
      '---',
      '',
    ].join('\n');
  });

  const fullContent = [
    '# Sardis Documentation (Full Content)',
    '',
    '> This file contains the complete documentation for Sardis, the Payment OS for the Agent Economy.',
    '> It is generated automatically from the documentation source files.',
    '',
    '---',
    '',
    ...sections,
  ].join('\n');

  return new Response(fullContent, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
    },
  });
}
