import { useState } from 'react';
import { getDemoSession, clearDemoSession, deleteDemoAccount } from '../state/demoAuth';
import { ShieldIcon, LogOutIcon, TrashIcon } from '../components/icons';
import { useNavigate } from 'react-router-dom';
import { ConfirmModal } from '../components/ConfirmModal';

export function ProfilePage() {
  const navigate = useNavigate();
  const session = getDemoSession();
  const displayName = session?.displayName ?? 'Demo user';
  const email = session?.email ?? 'demo@example.com';
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);

  const handleLogout = () => {
    clearDemoSession();
    navigate('/login', { replace: true });
  };

  const handleDeleteAccount = () => {
    deleteDemoAccount();
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
        <div className="actions" style={{ marginTop: '16px', borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
          <button
            type="button"
            className="button button--ghost"
            onClick={() => setDeleteConfirmOpen(true)}
            style={{ color: 'var(--error)', borderColor: 'var(--error)' }}
          >
            <TrashIcon style={{ marginRight: '6px', verticalAlign: 'middle' }} />
            Delete Account
          </button>
        </div>
      </section>

      <ConfirmModal
        isOpen={deleteConfirmOpen}
        onClose={() => setDeleteConfirmOpen(false)}
        onConfirm={handleDeleteAccount}
        title="Delete Account"
        message="This will permanently delete your demo account and all associated document history. This action cannot be undone."
        confirmText="Delete Account"
        cancelText="Cancel"
      />
    </div>
  );
}