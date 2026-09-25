import { describe, expect, it, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { VerificationResultPage } from './VerificationResultPage';
import { renderWithRouter } from '../test/render';
import { server } from '../test/setup';
import { setMockConfig, resetMockConfig } from '../mocks/config';
import { resetMockCounters } from '../mocks/handlers';

const TEST_VERIFICATION_ID = 'ver-demo-0001';
const ROUTE = `/verifications/${TEST_VERIFICATION_ID}`;
const PATH = '/verifications/:verificationId';

describe('VerificationResultPage', () => {
  beforeEach(() => {
    resetMockConfig();
    resetMockCounters();
    server.resetHandlers();
  });

  it('renders the verification status badge and a separate blockchain badge', async () => {
    renderWithRouter(<VerificationResultPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByText('Matched our synthetic demo reference')).toBeInTheDocument();
    expect(screen.getByText('Verification outcome recorded on-chain')).toBeInTheDocument();
    expect(document.querySelector('.status-badge--matched')).not.toBeNull();
    expect(document.querySelector('.chain-badge--confirmed')).not.toBeNull();
  });

  it('renders the synthetic data banner on the result view', async () => {
    renderWithRouter(<VerificationResultPage />, { route: ROUTE, path: PATH });
    await screen.findByText('Matched our synthetic demo reference');
    expect(screen.getByText('SYNTHETIC DEMO DATA')).toBeInTheDocument();
  });

  it('shows every field comparison, including mismatches, without a toggle', async () => {
    setMockConfig({ mock: 'INTEGRITY_MISMATCH' });
    renderWithRouter(<VerificationResultPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByText('Mismatch found')).toBeInTheDocument();
    expect(screen.getAllByText('Semester or Year').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Mismatch').length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: /show details|expand/i })).not.toBeInTheDocument();
  });

  it('lists the mismatched fields without hiding them behind a button', async () => {
    setMockConfig({ mock: 'INTEGRITY_MISMATCH' });
    renderWithRouter(<VerificationResultPage />, { route: ROUTE, path: PATH });
    await screen.findByText('Mismatch found in:');
    const heading = screen.getByText('Mismatch found in:');
    expect(heading.parentElement?.textContent).toContain('Semester or Year');
    expect(screen.queryByRole('button', { name: /show details|expand/i })).not.toBeInTheDocument();
  });

  it('explains a matched outcome in honest, non-overclaiming terms', async () => {
    setMockConfig({ mock: 'VERIFIED_MATCH' });
    renderWithRouter(<VerificationResultPage />, { route: ROUTE, path: PATH });
    expect(
      await screen.findByText(/match the reference for this category in the synthetic demo registry/)
    ).toBeInTheDocument();
    expect(screen.queryByText('authentic', { exact: false })).not.toBeInTheDocument();
  });

  it('shows the reason from rule results', async () => {
    setMockConfig({ mock: 'INTEGRITY_MISMATCH' });
    renderWithRouter(<VerificationResultPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByText(/semester_or_year does not match registry record/)).toBeInTheDocument();
  });

  it('shows a review button only when review is required or a mismatch is found', async () => {
    setMockConfig({ mock: 'INTEGRITY_MISMATCH' });
    renderWithRouter(<VerificationResultPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByRole('button', { name: 'Review this document' })).toBeInTheDocument();
  });

  it('shows verification history using is_current rather than sorting timestamps', async () => {
    renderWithRouter(<VerificationResultPage />, { route: ROUTE, path: PATH });
    await screen.findByText('Verification history');
    expect(screen.getByText('Current result')).toBeInTheDocument();
    expect(screen.getByText('Earlier')).toBeInTheDocument();
  });

  it('shows a network error state with retry', async () => {
    server.use(http.get(`*/api/v1/verifications/${TEST_VERIFICATION_ID}`, () => HttpResponse.error()));
    renderWithRouter(<VerificationResultPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });

  it('shows a loading indicator while the result loads', async () => {
    const delayedJson = async () => {
      await new Promise((resolve) => setTimeout(resolve, 100));
      return HttpResponse.json({});
    };
    server.use(
      http.get(`*/api/v1/verifications/${TEST_VERIFICATION_ID}`, async () => {
        await new Promise((resolve) => setTimeout(resolve, 100));
        return HttpResponse.json({
          verification_id: TEST_VERIFICATION_ID,
          document_id: 'doc-demo-0001',
          status: 'VERIFIED_MATCH',
          registry_record_key: 'DEMO-STU-001',
          field_comparisons: [],
          rule_results: [],
          reason_codes: [],
          is_current: true,
          supersedes_verification_id: null,
          review_actions: [],
          created_at: new Date().toISOString(),
        });
      })
    );
    server.use(
      http.get(`*/api/v1/verifications/${TEST_VERIFICATION_ID}/blockchain`, delayedJson)
    );
    server.use(
      http.get(`*/api/v1/verifications/${TEST_VERIFICATION_ID}/documents`, delayedJson)
    );
    renderWithRouter(<VerificationResultPage />, { route: ROUTE, path: PATH });
    expect(await screen.findByText('Loading verification result…')).toBeInTheDocument();
  });
});