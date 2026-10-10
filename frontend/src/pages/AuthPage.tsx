import type { FormEvent } from 'react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { EyeIcon, EyeOffIcon } from '../components/icons';
import { getDemoSession, refreshAuthSession } from '../state/demoAuth';
import { loginUser, registerUser } from '../utils/auth';

interface AuthPageProps {
  mode: 'login' | 'register';
}

interface SupabaseLikeError {
  code?: string;
  message?: string;
  status?: number;
}

function readSupabaseError(error: unknown): SupabaseLikeError {
  if (!error || typeof error !== 'object') {
    return {};
  }

  const candidate = error as Record<string, unknown>;
  return {
    code: typeof candidate.code === 'string' ? candidate.code : undefined,
    message: typeof candidate.message === 'string' ? candidate.message : undefined,
    status: typeof candidate.status === 'number' ? candidate.status : undefined,
  };
}

function getAuthErrorMessage(error: unknown): string {
  const supabaseError = readSupabaseError(error);
  const rawMessage =
    supabaseError.message?.trim() ||
    (error instanceof Error ? error.message.trim() : '');

  if (rawMessage) {
    const normalizedMessage = rawMessage.toLowerCase();
    const normalizedCode = supabaseError.code?.toLowerCase();

    if (
      supabaseError.status === 429 ||
      normalizedCode === 'over_email_send_rate_limit' ||
      normalizedMessage.includes('rate limit')
    ) {
      return `Supabase: ${rawMessage}. Wait a few minutes before trying to create another account, or configure a custom SMTP provider for the Supabase project.`;
    }

    if (normalizedMessage.includes('login credentials')) {
      return 'The email or password was not accepted.';
    }

    if (normalizedMessage.includes('email not confirmed')) {
      return 'Check your email confirmation link before signing in.';
    }

    if (normalizedMessage.includes('api key') || normalizedMessage.includes('jwt')) {
      return 'Supabase did not accept the frontend API key. Check the Supabase publishable key in frontend/.env.';
    }

    if (
      normalizedMessage.includes('signup') ||
      normalizedMessage.includes('sign up') ||
      normalizedMessage.includes('signups')
    ) {
      return `Supabase: ${rawMessage}`;
    }

    if (normalizedMessage.includes('redirect')) {
      return `Supabase: ${rawMessage}. Add this frontend URL to the allowed redirect URLs in Supabase.`;
    }

    if (
      normalizedMessage.includes('failed to fetch') ||
      normalizedMessage.includes('network') ||
      normalizedMessage.includes('fetch')
    ) {
      return 'Could not reach Supabase. Check the Supabase URL in frontend/.env and your network connection.';
    }

    if (rawMessage) {
      return `Supabase: ${rawMessage}`;
    }
  }

  return 'Authentication could not be completed. Please try again.';
}

export function AuthPage({ mode }: AuthPageProps) {
  const navigate = useNavigate();
  const isRegister = mode === 'register';
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formNotice, setFormNotice] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    const normalizedEmail = email.trim().toLowerCase();
    const trimmedName = displayName.trim();

    if (!normalizedEmail || !password || (isRegister && !trimmedName)) {
      setFormError('Enter the required fields to continue.');
      setFormNotice(null);
      return;
    }

    setPending(true);
    setFormError(null);
    setFormNotice(null);

    try {
      if (isRegister) {
        const result = await registerUser(trimmedName, normalizedEmail, password);

        if (result.needsEmailConfirmation) {
          setFormNotice('Check your email to confirm the account before signing in.');
          return;
        }
      } else {
        await loginUser(normalizedEmail, password);
      }

      await refreshAuthSession();

      if (!getDemoSession()) {
        setFormError('Authentication succeeded, but no active session was restored. Please try signing in again.');
        return;
      }

      navigate('/', { replace: true });
    } catch (error) {
      setFormError(getAuthErrorMessage(error));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="auth-card__brand">
          <span className="auth-card__mark" aria-hidden="true">
            <img src="/logo.png" alt="" />
          </span>
          <h1>DocuTrust</h1>
        </div>
        <p className="auth-card__intro">
          {isRegister ? 'Create your DocuTrust account' : 'Sign in to DocuTrust'}
        </p>

        <form className="auth-form" onSubmit={handleSubmit}>
          {isRegister ? (
            <label className="field">
              <span>Display name</span>
              <input
                type="text"
                autoComplete="name"
                value={displayName}
                disabled={pending}
                onChange={(event) => setDisplayName(event.target.value)}
              />
            </label>
          ) : null}
          <label className="field">
            <span>Email</span>
            <input
              type="email"
              autoComplete="username"
              value={email}
              disabled={pending}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label className="field">
            <span>Password</span>
            <div className="password-field">
              <input
                type={showPassword ? 'text' : 'password'}
                autoComplete={isRegister ? 'new-password' : 'current-password'}
                value={password}
                disabled={pending}
                onChange={(event) => setPassword(event.target.value)}
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                aria-pressed={showPassword}
                disabled={pending}
              >
                {showPassword ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
          </label>
          {formError ? (
            <p className="error-inline" role="alert">
              {formError}
            </p>
          ) : null}
          {formNotice ? (
            <p className="note" role="status">
              {formNotice}
            </p>
          ) : null}
          <button type="submit" className="button button--primary" disabled={pending}>
            {pending ? 'Please wait...' : isRegister ? 'Create account' : 'Continue'}
          </button>
        </form>

        <p className="auth-card__switch">
          {isRegister ? (
            <>
              Already have an account? <Link to="/login">Sign in</Link>
            </>
          ) : (
            <>
              Need an account? <Link to="/register">Register</Link>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
