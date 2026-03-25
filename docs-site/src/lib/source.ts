import { docs } from 'collections/index';
import { loader } from 'fumadocs-core/source';

// toFumadocsSource() returns { files: () => [...] } (lazy),
// but fumadocs-core@15 loader expects { files: [...] } (eager).
// Resolve eagerly by calling the files function.
const rawSource = docs.toFumadocsSource();
const files =
  typeof rawSource.files === 'function'
    ? (rawSource.files as () => unknown[])()
    : rawSource.files;

export const source = loader({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  source: { files } as any,
  baseUrl: '/docs',
});
