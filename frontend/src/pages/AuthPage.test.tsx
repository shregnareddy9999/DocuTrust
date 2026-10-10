import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AuthPage } from './AuthPage';
import { loginUser, registerUser } from '../utils/auth';
import { getDemoSession, refreshAuthSession } from '../state/demoAuth';

vi.mock('../utils/auth', () => ({
  loginUser: vi.fn(),
  registerUser: vi.fn(),
}));

vi.mock('../state/demoAuth', () => ({
  getDemoSession: vi.fn(),
  refreshAuthSession: vi.fn(),
}));

const mockedLoginUser = vi.mocked(loginUser);
const mockedRegisterUser = vi.mocked(registerUser);
const mockedGetDemoSession = vi.mocked(getDemoSession);
const mockedRefreshAuthSession = vi.mocked(refreshAuthSession);

function renderAuthPage(mode: 'login' | 'register') {
  return render(
    <MemoryRouter initialEntries={[mode === 'login' ? '/login' : '/register']}>
      <Routes>
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/register" element={<AuthPage mode="register" />} />
        <Route path="/" element={<div>Dashboard placeholder</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('AuthPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedRefreshAuthSession.mockResolvedValue();
    mockedGetDemoSession.mockReturnValue({
      displayName: 'Aarav Demo',
      email: 'aarav.demo@example.test',
    });
  });

  it('tells users to confirm email when registration returns no active session', async () => {
    mockedRegisterUser.mockResolvedValue({ needsEmailConfirmation: true });
    renderAuthPage('register');

    await userEvent.setup().type(screen.getByLabelText('Display name'), 'Aarav Demo');
    await userEvent.setup().type(screen.getByLabelText('Email'), 'AARAV.DEMO@EXAMPLE.TEST ');
    await userEvent.setup().type(screen.getByLabelText('Password'), 'demo-password-1');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Create account' }));

    expect(mockedRegisterUser).toHaveBeenCalledWith(
      'Aarav Demo',
      'aarav.demo@example.test',
      'demo-password-1',
    );
    expect(await screen.findByText('Check your email to confirm the account before signing in.')).toBeInTheDocument();
    expect(screen.queryByText('Dashboard placeholder')).not.toBeInTheDocument();
  });

  it('shows the Supabase registration error message', async () => {
    mockedRegisterUser.mockRejectedValue(new Error('Email signups are disabled'));
    renderAuthPage('register');

    await userEvent.setup().type(screen.getByLabelText('Display name'), 'Aarav Demo');
    await userEvent.setup().type(screen.getByLabelText('Email'), 'aarav.demo@example.test');
    await userEvent.setup().type(screen.getByLabelText('Password'), 'demo-password-1');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Create account' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Supabase: Email signups are disabled');
  });

  it('shows the Supabase email rate-limit cause during registration', async () => {
    mockedRegisterUser.mockRejectedValue({
      code: 'over_email_send_rate_limit',
      message: 'email rate limit exceeded',
      status: 429,
    });
    renderAuthPage('register');

    await userEvent.setup().type(screen.getByLabelText('Display name'), 'Aarav Demo');
    await userEvent.setup().type(screen.getByLabelText('Email'), 'aarav.demo@example.test');
    await userEvent.setup().type(screen.getByLabelText('Password'), 'demo-password-1');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Create account' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Supabase: email rate limit exceeded. Wait a few minutes before trying to create another account, or configure a custom SMTP provider for the Supabase project.',
    );
  });

  it('navigates after login only when a session is restored', async () => {
    mockedLoginUser.mockResolvedValue();
    renderAuthPage('login');

    await userEvent.setup().type(screen.getByLabelText('Email'), 'aarav.demo@example.test');
    await userEvent.setup().type(screen.getByLabelText('Password'), 'demo-password-1');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Continue' }));

    expect(mockedLoginUser).toHaveBeenCalledWith('aarav.demo@example.test', 'demo-password-1');
    expect(mockedRefreshAuthSession).toHaveBeenCalled();
    expect(await screen.findByText('Dashboard placeholder')).toBeInTheDocument();
  });
});
