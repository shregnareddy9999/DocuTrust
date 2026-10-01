import { describe, expect, it, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { ReviewPage } from './ReviewPage';
import { renderWithRouter } from '../test/render';
import { server } from '../test/setup';
import { resetMockConfig } from '../mocks/config';
import { resetMockCounters } from '../mocks/handlers';

const TEST_VERIFICATION_ID = 'ver-demo-0001';
const ROUTE = `/verifications/${TEST_VERIFICATION_ID}/review`;
const PATH = '/verifications/:verificationId/review';

function reviewableVerification(status = 'INTEGRITY_MISMATCH') {
  return {
    verification_id: TEST_VERIFICATION_ID,
    document_id: 'doc-demo-0001',
    status,
    registry_record_key: 'DEMO-STU-001',
    field_comparisons: [
      { field: 'student_name', extracted_value: 'Aarav Demo', registry_value: 'Aarav Demo', matched: true },
      { field: 'institution_name', extracted_value: 'Example Technical Institute', registry_value: 'Example Technical Institute', matched: true },
      { field: 'student_id', extracted_value: 'DEMO-STU-001', registry_value: 'DEMO-STU-001', matched: true },
      { field: 'course_name', extracted_value: 'B.Tech CSE', registry_value: 'B.Tech CSE', matched: true },
      { field: 'semester_or_year', extracted_value: '6', registry_value: '5', matched: false },
      { field: 'certificate_or_marksheet_id', extracted_value: 'DEMO-MARK-001', registry_value: 'DEMO-MARK-001', matched: true },
    ],
    rule_results: [
      { rule_id: 'required_field_presence', passed: true, reason: 'All required fields present' },
      { rule_id: 'field_match', passed: false, reason: 'semester_or_year does not match registry record DEMO-STU-001' },
    ],
    reason_codes: ['FIELD_MISMATCH:semester_or_year'],
    is_current: true,
    supersedes_verification_id: null,
    review_actions: [],
    created_at: new Date().toISOString(),
  };
}

describe('ReviewPage', () => {
  beforeEach(() => {
    resetMockConfig();
    resetMockCounters();
    server.resetHandlers();
    server.use(
      http.get('*/api/v1/verifications/:verificationId', () =>
        HttpResponse.json(reviewableVerification())
      )
    );
  });

  it('does not offer human review when the current result already matches the synthetic demo reference', async () => {
    server.use(
      http.get('*/api/v1/verifications/:verificationId', () =>
        HttpResponse.json({ ...reviewableVerification('VERIFIED_MATCH'), reason_codes: ['ALL_FIELDS_MATCH'] })
      )
    );
    renderWithRouter(<ReviewPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByText('No human review needed')).toBeInTheDocument();
    expect(screen.queryByText('Record review')).not.toBeInTheDocument();
  });

  it('pre-fills the correction form with extracted values when CORRECT is chosen', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ReviewPage />, { route: ROUTE, path: PATH });
    await screen.findByText('Review this document');
    await user.click(screen.getByText('Correct a value'));
    const input = await screen.findByLabelText(/Corrected value for Student Name/i);
    expect(input).toHaveValue('Aarav Demo');
  });

  it('shows the original OCR value next to the correction, visually distinct', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ReviewPage />, { route: ROUTE, path: PATH });
    await screen.findByText('Review this document');
    await user.click(screen.getByText('Correct a value'));
    await screen.findByLabelText(/Corrected value for Student Name/i);
    const original = document.querySelector('.corrections-table .original-value');
    expect(original).not.toBeNull();
    expect(original?.textContent).toContain('Aarav Demo');
  });

  it('records a reviewed result and includes "(reviewer-corrected)" for a corrected match', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ReviewPage />, { route: ROUTE, path: PATH });
    await screen.findByText('Review this document');
    await user.type(screen.getByTestId('reviewer-ref'), 'Priya (Reviewer)');
    await user.click(screen.getByText('Correct a value'));
    await screen.findByLabelText(/Corrected value for Student Name/i);
    await user.click(screen.getByRole('button', { name: 'Record review' }));
    expect(await screen.findByText('Review recorded')).toBeInTheDocument();
    expect(screen.getByText(/reviewer-corrected/)).toBeInTheDocument();
    expect(screen.getByText(/new verification record was created/)).toBeInTheDocument();
  });

  it('requires a reviewer name before recording', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ReviewPage />, { route: ROUTE, path: PATH });
    await screen.findByText('Review this document');
    const submit = screen.getByRole('button', { name: 'Record review' });
    expect(submit).toBeDisabled();
    await user.type(screen.getByTestId('reviewer-ref'), 'R');
    expect(screen.getByRole('button', { name: 'Record review' })).toBeEnabled();
  });

  it('shows the demo reference value beside the original OCR value', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ReviewPage />, { route: ROUTE, path: PATH });
    await screen.findByText('Review this document');
    await user.click(screen.getByText('Correct a value'));
    await screen.findByLabelText(/Corrected value for Student Name/i);
    expect(screen.getByText('Demo reference')).toBeInTheDocument();
    const original = document.querySelector('.corrections-table .original-value');
    const reference = document.querySelector('.corrections-table .reference-value');
    expect(original?.textContent).toContain('Aarav Demo');
    expect(reference?.textContent).toBe('Aarav Demo');
  });

  it('sends only the fields that actually changed when a correction is recorded', async () => {
    const user = userEvent.setup();
    let sentCorrections: Record<string, string> | undefined;
    server.use(
      http.post('*/api/v1/verifications/*/review', async ({ request }) => {
        const body = (await request.json()) as { corrections?: Record<string, string> };
        sentCorrections = body.corrections;
        return HttpResponse.json(
          { review_action_id: 'rev-demo-0001', new_verification_id: 'ver-demo-0002', new_status: 'VERIFIED_MATCH' },
          { status: 201 }
        );
      })
    );
    renderWithRouter(<ReviewPage />, { route: ROUTE, path: PATH });
    await screen.findByText('Review this document');
    await user.type(screen.getByTestId('reviewer-ref'), 'Priya (Reviewer)');
    await user.click(screen.getByText('Correct a value'));
    const input = await screen.findByLabelText(/Corrected value for Student Name/i);
    await user.clear(input);
    await user.type(input, 'Aarav Demo Kumar');
    await user.click(screen.getByRole('button', { name: 'Record review' }));
    await screen.findByText('Review recorded');
    expect(sentCorrections).toEqual({ student_name: 'Aarav Demo Kumar' });
  });

  it('reserves green for the ACCEPT action button', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ReviewPage />, { route: ROUTE, path: PATH });
    await screen.findByText('Review this document');
    expect(screen.getByRole('button', { name: 'Record review' })).toHaveClass('button--accent');
    await user.click(screen.getByText('Correct a value'));
    expect(screen.getByRole('button', { name: 'Record review' })).toHaveClass('button--primary');
  });

  it('does not claim a match is reviewer-corrected for a plain ACCEPT action', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ReviewPage />, { route: ROUTE, path: PATH });
    await screen.findByText('Review this document');
    await user.type(screen.getByTestId('reviewer-ref'), 'Priya (Reviewer)');
    await user.click(screen.getByRole('button', { name: 'Record review' }));
    await screen.findByText('Review recorded');
    expect(screen.queryByText(/reviewer-corrected/)).not.toBeInTheDocument();
  });

  it('renders the synthetic data banner', async () => {
    renderWithRouter(<ReviewPage />, { route: ROUTE, path: PATH });
    await screen.findByText('Review this document');
    expect(screen.getByText('SYNTHETIC DEMO DATA')).toBeInTheDocument();
  });
});
