import { useState, type ReactElement } from 'react';
import { NavLink, Outlet, useLocation, useNavigate, type NavLinkRenderProps } from 'react-router-dom';
import { SearchContext } from '../state/shellSearch';
import { getDemoSession, sessionInitials } from '../state/demoAuth';
import {
  BellIcon,
  BlockchainIcon,
  CloseIcon,
  DashboardIcon,
  DocumentsIcon,
  HistoryIcon,
  MenuIcon,
  ProfileIcon,
  ReviewIcon,
  SearchIcon,
  UploadIcon,
  type IconProps,
} from './icons';

const SEARCHABLE_ROUTES = ['/', '/documents', '/review-queue', '/history'];

interface NavItem {
  to: string;
  label: string;
  Icon: (props: IconProps) => ReactElement;
  end?: boolean;
}

const NAV_MAIN: NavItem[] = [
  { to: '/', label: 'Dashboard', Icon: DashboardIcon, end: true },
  { to: '/verify', label: 'Upload Document', Icon: UploadIcon, end: true },
  { to: '/documents', label: 'Documents', Icon: DocumentsIcon },
  { to: '/review-queue', label: 'Review Queue', Icon: ReviewIcon },
  { to: '/history', label: 'History', Icon: HistoryIcon },
  { to: '/blockchain-receipts', label: 'Blockchain Receipts', Icon: BlockchainIcon },
];

const NAV_SETTINGS: NavItem[] = [{ to: '/profile', label: 'Profile', Icon: ProfileIcon }];

function isSidebarActive(to: string, pathname: string, isActive: boolean): boolean {
  if (to === '/review-queue') {
    return isActive || /\/verifications\/[^/]+\/review\/?$/.test(pathname);
  }
  if (to === '/history') {
    return isActive || /\/verifications\/[^/]+\/blockchain\/?$/.test(pathname);
  }
  if (to === '/blockchain-receipts') {
    return isActive || pathname.startsWith('/blockchain-receipts');
  }
  return isActive;
}

function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const location = useLocation();

  return (
    <nav className="sidebar-nav" aria-label="Primary">
      <div className="sidebar-group">
        {NAV_MAIN.map(({ to, label, Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }: NavLinkRenderProps) =>
              `sidebar-link${isSidebarActive(to, location.pathname, isActive) ? ' sidebar-link--active' : ''}`
            }
            onClick={onNavigate}
          >
            <Icon className="sidebar-link__icon" />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>
      <div className="sidebar-group sidebar-group--settings">
        {NAV_SETTINGS.map(({ to, label, Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }: NavLinkRenderProps) =>
              `sidebar-link${isActive ? ' sidebar-link--active' : ''}`
            }
            onClick={onNavigate}
          >
            <Icon className="sidebar-link__icon" />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}

export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);
  const session = getDemoSession();
  const displayName = session?.displayName ?? 'Demo user';

  const canSearch = SEARCHABLE_ROUTES.includes(location.pathname);

return (
    <div className="app-shell">
      {menuOpen ? (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Close menu"
          onClick={() => setMenuOpen(false)}
        />
      ) : null}

      <aside className={`sidebar${menuOpen ? ' sidebar--open' : ''}`}>
        <div className="sidebar-brand">
          <img src="/logo.svg" alt="DocuTrust" className="sidebar-brand__logo" />
          <span className="sidebar-brand__text">
            <strong>DocuTrust</strong>
          </span>
          <button
            type="button"
            className="sidebar-close"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
          >
            <CloseIcon />
          </button>
        </div>
        <SidebarNav onNavigate={() => setMenuOpen(false)} />
      </aside>

      <div className="app-content">
        <header className="topbar">
          <button
            type="button"
            className="topbar__menu"
            aria-label="Open menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(true)}
          >
            <MenuIcon />
          </button>

          <img src="/logo.svg" alt="DocuTrust" className="topbar__logo" />

          <div className="topbar__history" role="group" aria-label="Page history">
            <button type="button" className="topbar__history-btn" aria-label="Go back" onClick={() => navigate(-1)}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </button>
            <button type="button" className="topbar__history-btn" aria-label="Go forward" onClick={() => navigate(1)}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </button>
          </div>

          {canSearch ? (
            <label className="topbar__search">
              <SearchIcon className="topbar__search-icon" />
              <span className="visually-hidden">Search local lists</span>
              <input
                type="search"
                placeholder="Search…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </label>
          ) : (
            <div className="topbar__spacer" />
          )}

          <div className="topbar__right">
            <span className="topbar__bell" aria-hidden="true" title="Notifications">
              <BellIcon />
            </span>
            <span className="topbar__avatar" aria-hidden="true">
              {sessionInitials(displayName)}
            </span>
            <span className="topbar__user">{displayName}</span>
          </div>
        </header>

        <SearchContext.Provider value={search}>
          <main className="app-main">
            <Outlet />
          </main>
        </SearchContext.Provider>
      </div>
    </div>
  );
}
