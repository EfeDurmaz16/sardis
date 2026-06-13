/**
 * Auto-paginating list responses — Anthropic-SDK ergonomics.
 *
 * A {@link Page} is the object returned by `list()` methods. It is *directly*
 * async-iterable, so you can stream every item across every page without ever
 * touching a cursor:
 *
 * ```ts
 * // Iterate every item across all pages.
 * for await (const agent of sardis.agents.list()) {
 *   console.log(agent.id);
 * }
 *
 * // Or work one page at a time.
 * let page = await sardis.agents.list();
 * for (const agent of page.data) console.log(agent.id);
 * while (page.hasNextPage()) {
 *   page = await page.getNextPage();
 * }
 *
 * // Or iterate page objects.
 * for await (const p of (await sardis.agents.list()).iterPages()) {
 *   console.log(p.data.length);
 * }
 * ```
 *
 * This mirrors `@anthropic-ai/sdk`'s `Page` / `for await ... of client.x.list()`
 * surface so agent developers feel at home.
 */

/** Cursor/offset-style params accepted by a page fetcher. */
export interface PageParams {
  cursor?: string;
  offset?: number;
  limit?: number;
  [key: string]: unknown;
}

/**
 * The raw response shape a paginated endpoint must expose. Sardis endpoints
 * return either `{ data, has_more, next_cursor }` or a named array envelope
 * (e.g. `{ agents: [...] }`); {@link Page} normalizes both.
 */
export interface PageResponse<Item> {
  data: Item[];
  has_more?: boolean;
  next_cursor?: string | null;
  /** Total count, when the server provides one. */
  total?: number;
}

/** Fetches one page given page params. */
export type PageFetcher<Item> = (params: PageParams) => Promise<PageResponse<Item>>;

/**
 * A single page of results that knows how to fetch the next page and is itself
 * an async-iterable over *all* items across *all* pages.
 */
export class Page<Item> implements AsyncIterable<Item> {
  /** Items on this page only. */
  readonly data: Item[];
  /** Whether more pages exist after this one (when the server reports it). */
  readonly has_more?: boolean;
  /** Opaque cursor for the next page (when the server uses cursors). */
  readonly next_cursor?: string | null;
  /** Total result count, when the server provides one. */
  readonly total?: number;

  private readonly _fetch: PageFetcher<Item>;
  private readonly _params: PageParams;

  constructor(response: PageResponse<Item>, fetcher: PageFetcher<Item>, params: PageParams) {
    this.data = response.data ?? [];
    this.has_more = response.has_more;
    this.next_cursor = response.next_cursor ?? undefined;
    this.total = response.total;
    this._fetch = fetcher;
    this._params = params;
  }

  /**
   * Whether a next page is available. Uses an explicit `has_more`/`next_cursor`
   * signal when present, otherwise infers from a full page (when a `limit` was
   * requested and exactly that many items came back).
   */
  hasNextPage(): boolean {
    if (this.has_more !== undefined) return this.has_more;
    if (this.next_cursor) return true;
    const limit = this._params.limit;
    if (limit !== undefined && this.data.length >= limit) return true;
    return false;
  }

  /** Params to fetch the page after this one. */
  private nextPageParams(): PageParams | null {
    if (!this.hasNextPage()) return null;
    if (this.next_cursor) {
      return { ...this._params, cursor: this.next_cursor };
    }
    const limit = this._params.limit ?? this.data.length;
    const offset = (this._params.offset ?? 0) + this.data.length;
    return { ...this._params, offset, limit };
  }

  /** Fetch the next {@link Page}. Throws if there is none. */
  async getNextPage(): Promise<Page<Item>> {
    const params = this.nextPageParams();
    if (!params) {
      throw new Error('No next page expected; check `hasNextPage()` before calling `getNextPage()`.');
    }
    const response = await this._fetch(params);
    return new Page<Item>(response, this._fetch, params);
  }

  /** Async-iterate over page objects, starting with this one. */
  async *iterPages(): AsyncIterableIterator<Page<Item>> {
    let page: Page<Item> = this;
    for (;;) {
      yield page;
      if (!page.hasNextPage()) return;
      page = await page.getNextPage();
    }
  }

  /** Async-iterate over every item across every page. */
  async *[Symbol.asyncIterator](): AsyncIterableIterator<Item> {
    for await (const page of this.iterPages()) {
      for (const item of page.data) yield item;
    }
  }
}
