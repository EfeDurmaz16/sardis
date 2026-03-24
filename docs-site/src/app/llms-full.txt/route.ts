import { source } from '@/lib/source';

export const revalidate = false;

export function GET() {
  const pages = source.getPages();

  const sections = pages.map((page) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const data = page.data as any;
    const title = String(data.title ?? '');
    const description = String(data.description ?? '');
    const url = `https://docs.sardis.sh${page.url}`;

    const content = data.structuredData?.contents
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
