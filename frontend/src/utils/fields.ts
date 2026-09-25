import type { DocumentType } from '../types/api';

export function humanizeField(field: string): string {
  return field
    .split('_')
    .map((word) => {
      const lower = word.toLowerCase();
      if (lower === 'id') return 'ID';
      if (['or', 'of', 'and', 'in', 'on', 'for'].includes(lower)) return lower;
      return word.charAt(0).toUpperCase() + word.slice(1);
    })
    .join(' ');
}

export function buildFieldLabels(documentTypes: DocumentType[]): Record<string, string> {
  const labels: Record<string, string> = {};
  for (const type of documentTypes) {
    for (const field of type.fields) {
      labels[field.name] = field.label;
    }
  }
  return labels;
}

export function fieldLabel(field: string, labels: Record<string, string>): string {
  return labels[field] ?? humanizeField(field);
}