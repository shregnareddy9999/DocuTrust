import type { FieldComparison } from '../types/api';

interface FieldComparisonTableProps {
  comparisons: FieldComparison[];
  labels?: Record<string, string>;
}

export function FieldComparisonTable({ comparisons, labels }: FieldComparisonTableProps) {
  if (comparisons.length === 0) {
    return (
      <div className="field-comparison-table">
        <p>No field comparisons are available.</p>
      </div>
    );
  }

  return (
    <div className="table-scroll">
      <table className="field-comparison-table">
        <thead>
          <tr>
            <th>Field</th>
            <th>Extracted value</th>
            <th>Registry value</th>
            <th>Match</th>
          </tr>
        </thead>
        <tbody>
          {comparisons.map((cmp) => (
            <tr key={cmp.field} className={cmp.matched ? 'comparison-row' : 'comparison-row comparison-row--mismatch'}>
              <td>{labels?.[cmp.field] ?? cmp.field}</td>
              <td>{cmp.extracted_value ?? '(not found)'}</td>
              <td>{cmp.registry_value ?? '(no value)'}</td>
              <td>{cmp.matched ? 'Match' : 'Mismatch'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}