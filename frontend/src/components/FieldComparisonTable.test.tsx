import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { FieldComparisonTable } from './FieldComparisonTable';
import type { FieldComparison } from '../types/api';

const comparisons: FieldComparison[] = [
  { field: 'student_name', extracted_value: 'Aarav Demo', registry_value: 'Aarav Demo', matched: true },
  { field: 'semester_or_year', extracted_value: '6', registry_value: '5', matched: false },
  { field: 'student_id', extracted_value: 'DEMO-STU-001', registry_value: '(no value)', matched: false },
];

describe('FieldComparisonTable', () => {
  it('renders every field including unmatched ones', () => {
    const { getByText, getAllByText } = render(<FieldComparisonTable comparisons={comparisons} />);
    expect(getByText('student_name')).toBeInTheDocument();
    expect(getByText('semester_or_year')).toBeInTheDocument();
    expect(getByText('student_id')).toBeInTheDocument();
    expect(getAllByText('Aarav Demo')).toHaveLength(2);
  });

  it('shows extracted and registry values side by side', () => {
    const { getByText } = render(<FieldComparisonTable comparisons={comparisons} />);
    expect(getByText('6')).toBeInTheDocument();
    expect(getByText('5')).toBeInTheDocument();
  });

  it('marks mismatches and does not hide them behind a toggle', () => {
    const { getAllByText, queryByRole } = render(<FieldComparisonTable comparisons={comparisons} />);
    expect(getAllByText('Mismatch')).toHaveLength(2);
    expect(queryByRole('button', { name: /show details|expand/i })).not.toBeInTheDocument();
  });

  it('shows "(not found)" for missing extracted values', () => {
    const { container } = render(
      <FieldComparisonTable comparisons={[{ ...comparisons[0], extracted_value: null }]} />
    );
    expect(container.textContent).toContain('(not found)');
  });

  it('renders an empty message when there are no comparisons', () => {
    const { getByText } = render(<FieldComparisonTable comparisons={[]} />);
    expect(getByText('No field comparisons are available.')).toBeInTheDocument();
  });
});