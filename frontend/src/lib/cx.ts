export type ClassValue = string | false | null | undefined | 0;

/** Tiny className joiner. */
export function cx(...values: ClassValue[]): string {
  return values.filter(Boolean).join(' ');
}
