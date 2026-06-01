/**
 * Singular/plural category matching — verbatim port of
 * `SpendingPolicy._categories_match`.
 */
export function categoriesMatch(ruleCat: string, resolvedCat: string): boolean {
  const a = ruleCat.toLowerCase().trim();
  const b = resolvedCat.toLowerCase().trim();
  if (a === b) {
    return true;
  }
  const variants = new Set<string>([a]);
  if (a.endsWith('ies')) {
    variants.add(a.slice(0, -3) + 'y'); // groceries -> grocery
  } else if (a.endsWith('s')) {
    variants.add(a.slice(0, -1)); // alcohols -> alcohol
  } else {
    variants.add(a + 's'); // alcohol -> alcohols
    if (a.endsWith('y')) {
      variants.add(a.slice(0, -1) + 'ies'); // grocery -> groceries
    }
  }
  return variants.has(b);
}
