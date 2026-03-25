import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';

export const baseOptions: BaseLayoutProps = {
  nav: {
    title: (
      <div className="flex items-center gap-2">
        <svg
          width="28"
          height="28"
          viewBox="0 0 32 32"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <rect width="32" height="32" rx="6" fill="#0a0a0a" />
          <path
            d="M22 6H12a8 8 0 000 16h2"
            stroke="#ff4f00"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M10 26h10a8 8 0 000-16h-2"
            stroke="#ff4f00"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span className="font-semibold text-lg">Sardis</span>
      </div>
    ),
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
