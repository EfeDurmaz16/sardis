/**
 * Funding Resource
 *
 * Manages funding commitments and cells for liquidity provisioning.
 * Commitments reserve liquidity that can be split into discrete cells
 * for granular allocation across agents and transactions.
 */

import { BaseResource } from './base.js';
import type {
  FundingCommitment,
  FundingCell,
  CreateFundingCommitmentInput,
  ListFundingCommitmentsParams,
  ListFundingCellsParams,
  SplitCellResponse,
  MergeCellsResponse,
  RequestOptions,
} from '../types.js';

export class FundingResource extends BaseResource {
  /**
   * Create a funding commitment.
   *
   * Reserves a pool of liquidity from a wallet for future use.
   *
   * @param params - Commitment creation parameters
   * @param options - Request options (signal, timeout)
   * @returns The created funding commitment
   */
  async createCommitment(
    params: CreateFundingCommitmentInput,
    options?: RequestOptions
  ): Promise<FundingCommitment> {
    return this._post<FundingCommitment>('/api/v2/funding/commitments', params, options);
  }

  /**
   * List funding commitments.
   *
   * @param params - Optional filter and pagination parameters
   * @param options - Request options (signal, timeout)
   * @returns List of funding commitments
   */
  async listCommitments(
    params?: ListFundingCommitmentsParams,
    options?: RequestOptions
  ): Promise<FundingCommitment[]> {
    const response = await this._get<{ commitments: FundingCommitment[] } | FundingCommitment[]>(
      '/api/v2/funding/commitments',
      params as Record<string, unknown>,
      options
    );

    if (Array.isArray(response)) {
      return response;
    }
    return response.commitments || [];
  }

  /**
   * List funding cells.
   *
   * @param params - Optional filter and pagination parameters
   * @param options - Request options (signal, timeout)
   * @returns List of funding cells
   */
  async listCells(
    params?: ListFundingCellsParams,
    options?: RequestOptions
  ): Promise<FundingCell[]> {
    const response = await this._get<{ cells: FundingCell[] } | FundingCell[]>(
      '/api/v2/funding/cells',
      params as Record<string, unknown>,
      options
    );

    if (Array.isArray(response)) {
      return response;
    }
    return response.cells || [];
  }

  /**
   * Split a funding cell into multiple smaller cells.
   *
   * The original cell is consumed and replaced by new cells
   * with the specified amounts.
   *
   * @param cellId - Cell ID to split
   * @param amounts - Array of amounts for the new cells
   * @param options - Request options (signal, timeout)
   * @returns The original cell and newly created cells
   */
  async splitCell(
    cellId: string,
    amounts: string[],
    options?: RequestOptions
  ): Promise<SplitCellResponse> {
    return this._post<SplitCellResponse>(
      `/api/v2/funding/cells/${cellId}/split`,
      { amounts },
      options
    );
  }

  /**
   * Merge multiple funding cells into a single cell.
   *
   * All source cells must belong to the same commitment and token.
   * The source cells are consumed and replaced by a single new cell.
   *
   * @param cellIds - Array of cell IDs to merge
   * @param options - Request options (signal, timeout)
   * @returns The merged cells and newly created cell
   */
  async mergeCells(
    cellIds: string[],
    options?: RequestOptions
  ): Promise<MergeCellsResponse> {
    return this._post<MergeCellsResponse>(
      '/api/v2/funding/cells/merge',
      { cell_ids: cellIds },
      options
    );
  }
}
