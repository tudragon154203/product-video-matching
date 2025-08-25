/**
 * Generic grouping helper function
 */
export function groupBy<T, K extends string>(arr: T[], key: (t: T) => K): Record<K, T[]> {
  const result: Record<K, T[]> = {} as Record<K, T[]>;
  
  for (const item of arr) {
    const keyValue = key(item);
    if (!result[keyValue]) {
      result[keyValue] = [];
    }
    result[keyValue].push(item);
  }
  
  return result;
}