import { describe, expect, it } from 'vitest';
import { buildFieldLabels, fieldLabel, humanizeField } from './fields';
import type { DocumentType } from '../types/api';

const types: DocumentType[] = [
  {
    category: 'demarksheet',
    label: 'Demarksheet',
    fields: [
      { name: 'student_name', label: 'Student Name', type: 'text', required: true, match_field: true },
      { name: 'semester_or_year', label: 'Semester or Year', type: 'text', required: true, match_field: true },
    ],
  },
];

describe('field labels', () => {
  it('uses the document-type label when it is known', () => {
    const labels = buildFieldLabels(types);
    expect(fieldLabel('semester_or_year', labels)).toBe('Semester or Year');
  });

  it('falls back to a humanized name for unknown fields', () => {
    expect(fieldLabel('certificate_or_marksheet_id', {})).toBe('Certificate or Marksheet ID');
  });

  it('humanizes snake_case names', () => {
    expect(humanizeField('student_id')).toBe('Student ID');
    expect(humanizeField('course_name')).toBe('Course Name');
  });
});