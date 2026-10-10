import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ProfilePage } from './ProfilePage';
import { deleteCurrentAccount } from '../api/account';

vi.mock('../api/account', () => ({
  deleteCurrentAccount: vi.fn(),
}));

vi.mock('../utils/auth', () => ({
  clearSupabaseSession: vi.fn(),
  logoutUser: vi.fn(),
}));

vi.mock('../state/demoAuth', () => ({
  clearDemoSession: vi.fn(),
  getDemoSession: () => ({
    displayName: 'Aarav Demo',
    email: 'aarav.demo@example.test',
  }),
  onSessionChange: vi.fn(),
  useAuthSession: () => ({
    session: {
      displayName: 'Aarav Demo',
      email: 'aarav.demo@example.test',
    },
  }),
}));

const mockedDeleteCurrentAccount = vi.mocked(deleteCurrentAccount);

function installLocalStorageMock(): Map<string, string> {
  const store = new Map<string, string>();
  vi.stubGlobal('localStorage', {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => {
      store.set(key, value);
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
    clear: () => {
      store.clear();
    },
  });
  return store;
}

function renderProfilePage() {
  return render(
    <MemoryRouter initialEntries={['/profile']}>
      <Routes>
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/register" element={<div>Register placeholder</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ProfilePage', () => {
  let storage: Map<string, string>;

  beforeEach(() => {
    vi.clearAllMocks();
    storage = installLocalStorageMock();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('deletes the account and returns to registration', async () => {
    mockedDeleteCurrentAccount.mockResolvedValue();
    storage.set(
      'docutrust.recentDocuments.aarav.demo@example.test',
      JSON.stringify([{ documentId: 'doc-demo-0001' }]),
    );
    storage.set(
      'docutrust.preview.doc-demo-0001',
      JSON.stringify({ url: 'data:image/png;base64,AA==', size: 1, kind: 'image' }),
    );

    renderProfilePage();

    await userEvent.setup().click(screen.getByRole('button', { name: 'Delete Account' }));
    await userEvent.setup().click(screen.getByRole('button', { name: 'Delete account' }));

    await waitFor(() => {
      expect(mockedDeleteCurrentAccount).toHaveBeenCalled();
    });
    expect(storage.has('docutrust.recentDocuments.aarav.demo@example.test')).toBe(false);
    expect(storage.has('docutrust.preview.doc-demo-0001')).toBe(false);
    expect(await screen.findByText('Register placeholder')).toBeInTheDocument();
  });

  it('shows a useful account deletion error', async () => {
    mockedDeleteCurrentAccount.mockRejectedValue(new Error('not configured'));
    renderProfilePage();

    await userEvent.setup().click(screen.getByRole('button', { name: 'Delete Account' }));
    await userEvent.setup().click(screen.getByRole('button', { name: 'Delete account' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not delete this account. Check that backend Supabase account deletion is configured, then try again.',
    );
  });
});
