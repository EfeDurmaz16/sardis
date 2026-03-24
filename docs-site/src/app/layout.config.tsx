import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';

export const baseOptions: BaseLayoutProps = {
  nav: {
    title: 'Sardis',
  },
  links: [
    {
      text: 'Docs',
      url: '/docs',
      active: 'nested-url',
    },
    {
      text: 'API Reference',
      url: '/docs/api',
    },
    {
      text: 'Blog',
      url: 'https://sardis.sh/blog',
      external: true,
    },
    {
      text: 'GitHub',
      url: 'https://github.com/EfeDurmaz16/sardis',
      external: true,
    },
  ],
};
