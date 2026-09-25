import { getDemoSession, clearDemoSession } from '../state/demoAuth';
import { ShieldIcon, LogOutIcon } from '../components/icons';
import { useNavigate } from 'react-router-dom';

export function ProfilePage() {
  const navigate = useNavigate();
  const session = getDemoSession();
  const displayName = session?.displayName ?? 'Demo user';
  const email = session?.email ?? 'demo@example.com';

  const handleLogout = () => {
    clearDemoSession();
    navigate('/login', { replace: true });
  };

  return (
    <div className="page profile-page">
      <h1>Profile</h1>
      <p className="page-intro">Demo build, synthetic data.</p>
      <section className="card">
        <div className="profile-header">
          <span className="profile-avatar" aria-hidden="true">
            <ShieldIcon />
          </span>
          <div>
            <h2>{displayName}</h2>
            <p className="profile-email">{email}</p>
          </div>
        </div>
        <p className="note">
          No real account exists. Authentication is not part of this demonstration.
        </p>
        <div className="actions" style={{ marginTop: '16px' }}>
          <button
            type="button"
            className="button button--secondary"
            onClick={handleLogout}
          >
            <LogOutIcon style={{ marginRight: '6px', verticalAlign: 'middle' }} />
            Logout
          </button>
        </div>
      </section>
    </div>
  );
}