import type { EntityType } from '../types';

export const ENTITY_TYPES: EntityType[] = [
  'PERSON',
  'ORG',
  'LOCATION',
  'DATE',
  'MONEY',
  'EMAIL',
  'URL',
  'PRODUCT',
  'LAW',
  'CONCEPT',
  'OTHER',
];

const COLORS: Record<string, string> = {
  PERSON: '#6366f1',
  ORG: '#0ea5e9',
  LOCATION: '#10b981',
  DATE: '#f59e0b',
  MONEY: '#84cc16',
  EMAIL: '#ec4899',
  URL: '#06b6d4',
  PRODUCT: '#f97316',
  LAW: '#ef4444',
  CONCEPT: '#a855f7',
  OTHER: '#a1a1aa',
};

const LABELS: Record<string, string> = {
  PERSON: 'Person',
  ORG: 'Organization',
  LOCATION: 'Location',
  DATE: 'Date',
  MONEY: 'Money',
  EMAIL: 'Email',
  URL: 'URL',
  PRODUCT: 'Product',
  LAW: 'Law / regulation',
  CONCEPT: 'Concept',
  OTHER: 'Other',
};

export const normType = (t?: string | null): string => (t ? t.toUpperCase() : 'OTHER');

export function entityColor(type?: string | null): string {
  return COLORS[normType(type)] ?? COLORS.OTHER;
}

export function entityLabel(type?: string | null): string {
  const t = normType(type);
  return LABELS[t] ?? t.charAt(0) + t.slice(1).toLowerCase();
}
