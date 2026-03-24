import defaultMdxComponents from 'fumadocs-ui/mdx';
import { openapi } from '@/lib/openapi';
import type { MDXComponents } from 'mdx/types';

export function useMDXComponents(components?: MDXComponents): MDXComponents {
  return {
    ...defaultMdxComponents,
    APIPage: openapi.APIPage,
    ...components,
  };
}
