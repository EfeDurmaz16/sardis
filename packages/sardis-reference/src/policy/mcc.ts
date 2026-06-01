/**
 * MCC (Merchant Category Code) — a STATIC mirror of the high-risk / default-
 * blocked set used by `SpendingPolicy._check_mcc_policy` (Checks 3–4).
 *
 * This is **data, not IO**. The authoritative MCC table lives server-side
 * (`core/mcc_service.py` loads it from a JSON data file that ships only in the
 * private backend). This package ships a representative subset of the well-known
 * high-risk categories plus the fail-closed semantics, documented as
 * "category heuristics; the authoritative set lives server-side".
 *
 * Fidelity rules mirrored from `mcc_service.is_blocked_category`:
 *   - an MCC whose category is in `blockedMerchantCategories` → blocked;
 *   - an UNKNOWN MCC (not in this table) → blocked (fail-closed);
 *   - a known MCC with `defaultBlocked` → blocked as a high-risk merchant.
 */

export interface MccInfo {
  code: string;
  description: string;
  category: string;
  riskLevel: 'low' | 'medium' | 'high';
  defaultBlocked: boolean;
}

/**
 * Representative MCC mirror. The high-risk / default-blocked codes are the ones
 * that materially affect the decision; common low-risk codes are included so
 * legitimate spends resolve to a category and are NOT fail-closed-blocked.
 */
const MCC_TABLE: Record<string, MccInfo> = {
  // ── High-risk, default-blocked ──
  '7995': { code: '7995', description: 'Betting/Casino Gambling', category: 'gambling', riskLevel: 'high', defaultBlocked: true },
  '7800': { code: '7800', description: 'Government-Owned Lottery', category: 'gambling', riskLevel: 'high', defaultBlocked: true },
  '7801': { code: '7801', description: 'Government-Licensed Online Casinos', category: 'gambling', riskLevel: 'high', defaultBlocked: true },
  '7802': { code: '7802', description: 'Government-Licensed Horse/Dog Racing', category: 'gambling', riskLevel: 'high', defaultBlocked: true },
  '5993': { code: '5993', description: 'Cigar Stores and Stands', category: 'tobacco', riskLevel: 'high', defaultBlocked: true },
  '5921': { code: '5921', description: 'Package Stores - Beer, Wine, Liquor', category: 'alcohol', riskLevel: 'high', defaultBlocked: true },
  '5912': { code: '5912', description: 'Drug Stores and Pharmacies', category: 'pharmacy', riskLevel: 'medium', defaultBlocked: false },
  '5816': { code: '5816', description: 'Digital Goods - Games', category: 'digital', riskLevel: 'low', defaultBlocked: false },
  '6051': { code: '6051', description: 'Quasi Cash / Crypto', category: 'crypto', riskLevel: 'high', defaultBlocked: true },
  '6211': { code: '6211', description: 'Security Brokers/Dealers', category: 'investments', riskLevel: 'high', defaultBlocked: true },
  '5967': { code: '5967', description: 'Direct Marketing - Inbound Telemarketing', category: 'adult', riskLevel: 'high', defaultBlocked: true },

  // ── Common low-risk (resolve cleanly, not fail-closed) ──
  '5411': { code: '5411', description: 'Grocery Stores, Supermarkets', category: 'groceries', riskLevel: 'low', defaultBlocked: false },
  '5734': { code: '5734', description: 'Computer Software Stores', category: 'software', riskLevel: 'low', defaultBlocked: false },
  '7372': { code: '7372', description: 'Computer Programming / Cloud Services', category: 'cloud', riskLevel: 'low', defaultBlocked: false },
  '4816': { code: '4816', description: 'Computer Network / Information Services', category: 'cloud', riskLevel: 'low', defaultBlocked: false },
  '5045': { code: '5045', description: 'Computers, Peripherals, Software', category: 'hardware', riskLevel: 'low', defaultBlocked: false },
  '5942': { code: '5942', description: 'Book Stores', category: 'retail', riskLevel: 'low', defaultBlocked: false },
};

/** Look up MCC info, or null if unknown (matches `get_mcc_info`). */
export function getMccInfo(mccCode: string): MccInfo | null {
  return MCC_TABLE[mccCode] ?? null;
}

/**
 * Whether an MCC belongs to a blocked category. Fail-closed on unknown codes,
 * exactly mirroring `mcc_service.is_blocked_category`.
 */
export function isBlockedCategory(mccCode: string, blockedCategories: string[]): boolean {
  const info = getMccInfo(mccCode);
  if (!info) {
    // Fail-closed: unknown MCC codes are blocked by default.
    return true;
  }
  return blockedCategories.includes(info.category);
}
