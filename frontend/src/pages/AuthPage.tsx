import type { FormEvent } from 'react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShieldIcon, EyeIcon, EyeOffIcon } from '../components/icons';
import { setDemoSession, isEmailRegistered, registerEmail } from '../state/demoAuth';

interface AuthPageProps {
  mode: 'login' | 'register';
}

export function AuthPage({ mode }: AuthPageProps) {
  const navigate = useNavigate();
  const isRegister = mode === 'register';
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent): void {
    event.preventDefault();
    const trimmedEmail = email.trim();
    const trimmedPassword = password.trim();
    
    if (!trimmedEmail || !trimmedPassword || (isRegister && !displayName.trim())) {
      setFormError('Enter the required fields to continue this demonstration.');
      return;
    }

    if (!isRegister) {
      if (!isEmailRegistered(trimmedEmail)) {
        setFormError('for login please register');
        return;
      }
    }

    const name = (isRegister ? displayName : trimmedEmail.split('@')[0] || 'Demo user').trim();
    
    if (isRegister) {
      registerEmail(trimmedEmail);
    }
    
    setDemoSession({
      displayName: name || 'Demo user',
      email: trimmedEmail,
    });
    navigate('/', { replace: true });
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="auth-card__brand">
          <span className="auth-card__mark" aria-hidden="true">
            <ShieldIcon />
          </span>
          <h1>DocuTrust</h1>
        </div>
        <p className="auth-card__intro">
          {isRegister ? 'Create a demonstration profile' : 'Sign in to the demonstration'}
        </p>

        <form className="auth-form" onSubmit={handleSubmit}>
          {isRegister ? (
            <label className="field">
              <span>Display name</span>
              <input
                type="text"
                autoComplete="name"
                value={displayName}
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
                onChange={(event) => setPassword(event.target.value)}
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                aria-pressed={showPassword}
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
          <button type="submit" className="button button--primary">
            {isRegister ? 'Create demonstration profile' : 'Continue'}
          </button>
        </form>

        <p className="auth-card__switch">
          {isRegister ? (
            <>
              Already have a demonstration profile? <Link to="/login">Sign in</Link>
            </>
          ) : (
            <>
              Need a demonstration profile? <Link to="/register">Register</Link>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
