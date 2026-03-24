import { docs } from 'collections/docs';
import { loader } from 'fumadocs-core/source';

export const source = loader({
  source: docs,
  baseUrl: '/docs',
});
