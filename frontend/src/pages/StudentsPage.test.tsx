import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithRouter } from '../test/render';
import * as studentsApi from '../api/students';
import { StudentsPage } from './StudentsPage';

vi.mock('../api/students');

const api = vi.mocked(studentsApi);

beforeEach(() => {
  vi.resetAllMocks();
  api.listStudents.mockResolvedValue([
    { student_ref: 'DEMO-STU-101', display_name: 'Aarav Demo', aadhaar_masked: 'XXXX XXXX 0001', source_label: 'synthetic-demo' },
    { student_ref: 'DEMO-STU-103', display_name: 'Kabir Demo', aadhaar_masked: 'XXXX XXXX 0003', source_label: 'synthetic-demo' },
  ]);
  api.getStudentDocuments.mockResolvedValue([]);
  api.getGovernmentRecords.mockImplementation(async (ref: string) =>
    ref === 'DEMO-STU-101'
      ? {
          student_ref: ref, status: 'FOUND', source_label: 'synthetic-demo',
          records: [{ id: 'g1', record_type: 'Caste Certificate (demo)', fields: { issuer: 'Demo Office' }, is_synthetic: true, source_label: 'synthetic-demo', created_at: '2026-09-30T00:00:00Z' }],
        }
      : { student_ref: ref, status: 'NO_LINKED_DOCUMENTS_FOUND', source_label: 'synthetic-demo', records: [] }
  );
  api.getMarksheetHistory.mockResolvedValue({
    student_ref: 'DEMO-STU-101', source_label: 'synthetic-demo',
    history: [
      { id: 'm1', semester: 1, subjects: { Mathematics: 68 }, total: 68, cgpa: 6.8, uploaded_at: '2026-09-30T00:00:00Z' },
      { id: 'm2', semester: 2, subjects: { Mathematics: 72 }, total: 72, cgpa: 7.3, uploaded_at: '2026-09-30T00:00:00Z' },
    ],
    summary: { available: true, limited_history: false, derived: true, note: 'Derived from the stored records above; it does not change them.', points: ['CGPA moved from 6.8 (semester 1) to 7.3 (semester 2): improving.'] },
  });
});

describe('StudentsPage', () => {
  it('shows masked identifiers, synthetic labels, records and the derived summary', async () => {
    renderWithRouter(<StudentsPage />, { route: '/students', path: '/students' });
    expect(await screen.findByText('Caste Certificate (demo)')).toBeInTheDocument();
    expect(screen.getByText('Synthetic demo')).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /XXXX XXXX 0001/ })).toBeInTheDocument();
    expect(screen.getByText(/improving/)).toBeInTheDocument();
    expect(screen.getByText(/does not change them/)).toBeInTheDocument();
  });

  it('shows a neutral message when no government record is linked', async () => {
    const user = userEvent.setup();
    renderWithRouter(<StudentsPage />, { route: '/students', path: '/students' });
    await screen.findByText('Caste Certificate (demo)');
    await user.selectOptions(screen.getByRole('combobox'), 'DEMO-STU-103');
    const note = await screen.findByText(/No matching reference found in the demo registry/);
    expect(note.textContent).toMatch(/not evidence of a fake document/);
    expect(document.body.textContent).not.toMatch(/\b(fraud|forged|authentic|genuine)\b/i);
  });

  it('refetches when Refresh is pressed so new records appear without a page reload', async () => {
    const user = userEvent.setup();
    renderWithRouter(<StudentsPage />, { route: '/students', path: '/students' });
    await screen.findByText('Caste Certificate (demo)');
    const before = api.getGovernmentRecords.mock.calls.length;
    await user.click(screen.getByRole('button', { name: 'Refresh' }));
    await waitFor(() => expect(api.getGovernmentRecords.mock.calls.length).toBeGreaterThan(before));
  });

  it('shows an error state with retry when loading fails, without a verdict', async () => {
    api.getGovernmentRecords.mockRejectedValue(new Error('Database unavailable. This is a technical failure, not a verification result.'));
    renderWithRouter(<StudentsPage />, { route: '/students', path: '/students' });
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/technical failure/));
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });
});
