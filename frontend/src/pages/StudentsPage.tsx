import { useEffect, useState } from 'react';
import { listStudents } from '../api/students';
import { useStudentData } from '../state/useStudentData';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import type { StudentSummary } from '../types/api';

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString();
}

export function StudentsPage() {
  const [students, setStudents] = useState<StudentSummary[] | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const { data, error, loading, reload } = useStudentData(selected);

  useEffect(() => {
    let cancelled = false;
    listStudents()
      .then((rows) => {
        if (cancelled) return;
        setStudents(rows);
        setSelected((current) => current ?? rows[0]?.student_ref ?? null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setListError(err instanceof Error ? err.message : 'Could not load students.');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (listError) return <ErrorState message={listError} />;
  if (!students) return <LoadingState message="Loading students…" />;
  if (students.length === 0) {
    return (
      <div className="page students-page">
        <h1>Students</h1>
        <EmptyState title="No students yet" message="Run python -m app.fixtures.seed_students to load the synthetic demo students." />
      </div>
    );
  }

  const government = data?.government;
  const marksheets = data?.marksheets;

  return (
    <div className="page students-page">
      <h1>Students</h1>
      <p className="page-intro">
        Synthetic demo records only. Nothing here is an official government record. Records refresh when you return to this tab or press Refresh.
      </p>

      <label>
        Student{' '}
        <select value={selected ?? ''} onChange={(event) => setSelected(event.target.value)}>
          {students.map((student) => (
            <option key={student.student_ref} value={student.student_ref}>
              {student.student_ref} — {student.display_name} ({student.aadhaar_masked ?? 'no identifier'})
            </option>
          ))}
        </select>
      </label>

      <button type="button" className="button button--secondary" onClick={reload}>
        Refresh
      </button>

      {error ? <ErrorState message={error} onRetry={reload} /> : null}
      {loading && !data ? <LoadingState message="Loading records…" /> : null}

      {data ? (
        <>
          <section className="card" aria-label="Linked documents">
            <h2>Linked documents</h2>
            {data.documents.length === 0 ? (
              <p>No documents are linked to this student yet.</p>
            ) : (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr><th>Category</th><th>Version</th><th>Processing</th><th>Uploaded</th></tr>
                  </thead>
                  <tbody>
                    {data.documents.map((doc) => (
                      <tr key={doc.document_id}>
                        <td>{doc.category}</td>
                        <td>v{doc.version}</td>
                        <td>{doc.processing_state}</td>
                        <td>{formatDate(doc.uploaded_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="card" aria-label="Linked government records">
            <h2>Linked government records</h2>
            {government && government.records.length > 0 ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr><th>Record</th><th>Details</th><th>Source</th></tr>
                  </thead>
                  <tbody>
                    {government.records.map((record) => (
                      <tr key={record.id}>
                        <td>{record.record_type}</td>
                        <td>{Object.entries(record.fields).map(([key, value]) => `${key}: ${value}`).join(', ')}</td>
                        <td>{record.is_synthetic ? 'Synthetic demo' : record.source_label}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p>No matching reference found in the demo registry — not evidence of a fake document.</p>
            )}
          </section>

          <section className="card" aria-label="Marksheet history">
            <h2>Marksheet history</h2>
            {marksheets && marksheets.history.length > 0 ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr><th>Semester</th><th>Subjects</th><th>CGPA</th></tr>
                  </thead>
                  <tbody>
                    {marksheets.history.map((row) => (
                      <tr key={row.id}>
                        <td>{row.semester}</td>
                        <td>{Object.entries(row.subjects).map(([name, marks]) => `${name}: ${marks}`).join(', ')}</td>
                        <td>{row.cgpa ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p>No marksheets are stored for this student yet.</p>
            )}
            {marksheets ? (
              <div aria-label="Derived summary">
                <h3>Summary (derived)</h3>
                <p className="page-intro">{marksheets.summary.note}</p>
                <ul>
                  {marksheets.summary.points.map((point) => (
                    <li key={point}>{point}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>
        </>
      ) : null}
    </div>
  );
}
