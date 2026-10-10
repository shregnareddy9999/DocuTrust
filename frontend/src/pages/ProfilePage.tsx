import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { deleteCurrentAccount } from '../api/account';
import { ConfirmModal } from '../components/ConfirmModal';
import { LogOutIcon, TrashIcon } from '../components/icons';
import { clearDemoSession, useAuthSession } from '../state/demoAuth';
import { clearLocalPreviews } from '../state/preview';
import {
  clearRecentDocumentsForEmail,
  getRecentDocumentIds,
} from '../state/recentDocuments';
import { clearSupabaseSession, logoutUser } from '../utils/auth';

export function ProfilePage() {
  const navigate = useNavigate();
  const { session } = useAuthSession();
  const displayName = session?.displayName ?? 'DocuTrust User';
  const email = session?.email ?? '';
  const [deleteNoticeOpen, setDeleteNoticeOpen] = useState(false);
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [logoutPending, setLogoutPending] = useState(false);
  const [deletePending, setDeletePending] = useState(false);

  const handleLogout = async () => {
    setLogoutPending(true);
    setLogoutError(null);

    try {
      await logoutUser();
      clearDemoSession();
      navigate('/login', { replace: true });
    } catch {
      setLogoutError('Could not sign out. Please try again.');
    } finally {
      setLogoutPending(false);
    }
  };

  const handleDeleteAccount = async () => {
    setDeletePending(true);
    setDeleteError(null);

    const accountEmail = email;
    const localDocumentIds = getRecentDocumentIds();

    try {
      await deleteCurrentAccount();
      clearRecentDocumentsForEmail(accountEmail);
      clearLocalPreviews(localDocumentIds);
      await clearSupabaseSession();
      clearDemoSession();
      navigate('/register', { replace: true });
    } catch {
      setDeleteError('Could not delete this account. Check that backend Supabase account deletion is configured, then try again.');
    } finally {
      setDeletePending(false);
      setDeleteNoticeOpen(false);
    }
  };

  return (
    <div className="page profile-page">
      <h1>Profile</h1>
      <p className="page-intro">Supabase account for this DocuTrust demo.</p>
      <section className="card">
        <div className="profile-header">
          <span className="profile-avatar" aria-hidden="true">
            <img src="/logo.png" alt="" />
          </span>
          <div>
            <h2>{displayName}</h2>
            <p className="profile-email">{email}</p>
          </div>
        </div>
        <p className="note">
          Account access is handled by Supabase email and password authentication.
        </p>
        {logoutError ? (
          <p className="error-inline" role="alert">
            {logoutError}
          </p>
        ) : null}
        {deleteError ? (
          <p className="error-inline" role="alert">
            {deleteError}
          </p>
        ) : null}
        <div className="actions" style={{ marginTop: '16px' }}>
          <button
            type="button"
            className="button button--secondary"
            onClick={handleLogout}
            disabled={logoutPending}
          >
            <LogOutIcon style={{ marginRight: '6px', verticalAlign: 'middle' }} />
            {logoutPending ? 'Signing out...' : 'Logout'}
          </button>
        </div>
        <div className="actions" style={{ marginTop: '16px', borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
          <button
            type="button"
            className="button button--ghost"
            onClick={() => setDeleteNoticeOpen(true)}
            disabled={deletePending}
            style={{ color: 'var(--error)', borderColor: 'var(--error)' }}
          >
            <TrashIcon style={{ marginRight: '6px', verticalAlign: 'middle' }} />
            {deletePending ? 'Deleting...' : 'Delete Account'}
          </button>
        </div>
      </section>

      <ConfirmModal
        isOpen={deleteNoticeOpen}
        onClose={() => {
          if (!deletePending) {
            setDeleteNoticeOpen(false);
          }
        }}
        onConfirm={() => void handleDeleteAccount()}
        title="Delete account"
        message="This deletes your Supabase account and clears this account's local DocuTrust document list in this browser. Registering again with the same email starts with an empty local workspace."
        confirmText={deletePending ? 'Deleting...' : 'Delete account'}
        cancelText="Close"
      />
    </div>
  );
}
