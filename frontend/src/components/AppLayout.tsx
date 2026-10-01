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

import {
  NavLink,
  Outlet,
  useLocation,
} from 'react-router-dom';

import { useState, type ReactElement } from 'react';

import { SearchContext } from '../state/shellSearch';
import { getDemoSession, sessionInitials } from '../state/demoAuth';

interface NavItem {
  to: string;
  label: string;
  Icon: (props: IconProps) => ReactElement;
  end?: boolean;
}

const SEARCHABLE_ROUTES = ['/', '/documents', '/review-queue', '/history'];

const NAV_MAIN: NavItem[] = [
  {
    to: '/',
    label: 'Dashboard',
    Icon: DashboardIcon,
    end: true,
  },
  {
    to: '/verify',
    label: 'Upload Document',
    Icon: UploadIcon,
    end: true,
  },
  {
    to: '/documents',
    label: 'Documents',
    Icon: DocumentsIcon,
  },
  {
    to: '/academic-summary',
    label: 'AI Academic Summary',
    Icon: DocumentsIcon,
  },
  {
    to: '/review-queue',
    label: 'Review Queue',
    Icon: ReviewIcon,
  },
  {
    to: '/history',
    label: 'History',
    Icon: HistoryIcon,
  },
  {
    to: '/blockchain-receipts',
    label: 'Blockchain Receipts',
    Icon: BlockchainIcon,
  },
];

const NAV_SETTINGS: NavItem[] = [
  {
    to: '/profile',
    label: 'Profile',
    Icon: ProfileIcon,
  },
];

export function AppLayout() {
  const location = useLocation();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [search, setSearch] = useState('');

  const session = getDemoSession();
  const displayName = session?.displayName ?? 'Demo user';

  const canSearch = SEARCHABLE_ROUTES.includes(location.pathname);

  const closeMobileMenu = () => {
    setMobileMenuOpen(false);
  };

  return (
    <div className="app-shell">

      {/* Sidebar mobile backdrop */}
      {mobileMenuOpen && (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={closeMobileMenu}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`sidebar ${
          mobileMenuOpen ? 'sidebar--open' : ''
        }`}
      >
        <div className="sidebar-brand">
          <NavLink
            to="/"
            onClick={closeMobileMenu}
            aria-label="DocuTrust dashboard"
          >
            <img
              src="/logo.png"
              alt="DocuTrust"
              className="sidebar-brand__logo"
            />
          </NavLink>

          <div className="sidebar-brand__text">
            <strong>DocuTrust</strong>
            <span>Document Intelligence</span>
          </div>

          <button
            type="button"
            className="sidebar-close"
            onClick={closeMobileMenu}
            aria-label="Close navigation"
          >
            <CloseIcon />
          </button>
        </div>

        <nav
          className="sidebar-nav"
          aria-label="Main navigation"
        >
          <div className="sidebar-group">
            {NAV_MAIN.map(
              ({
                to,
                label,
                Icon,
                end,
              }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  onClick={closeMobileMenu}
                  className={({ isActive }) =>
                    `sidebar-link ${
                      isActive
                        ? 'sidebar-link--active'
                        : ''
                    }`
                  }
                >
                  <span className="sidebar-link__icon">
                    <Icon />
                  </span>

                  <span>{label}</span>
                </NavLink>
              ),
            )}
          </div>
        </nav>

        <div className="sidebar-group sidebar-group--settings">
          {NAV_SETTINGS.map(
            ({ to, label, Icon }) => (
              <NavLink
                key={to}
                to={to}
                onClick={closeMobileMenu}
                className={({ isActive }) =>
                  `sidebar-link ${
                    isActive
                      ? 'sidebar-link--active'
                      : ''
                  }`
                }
              >
                <span className="sidebar-link__icon">
                  <Icon />
                </span>

                <span>{label}</span>
              </NavLink>
            ),
          )}
        </div>
      </aside>

      {/* Main application area */}
      <div className="app-content">

        {/* Topbar */}
        <header className="topbar">

          <button
            type="button"
            className="topbar__menu"
            onClick={() => setMobileMenuOpen(true)}
            aria-label="Open navigation"
            aria-expanded={mobileMenuOpen}
          >
            <MenuIcon />
          </button>

          <img
            src="/logo.png"
            alt="DocuTrust"
            className="topbar__logo"
          />

          <div
            className="topbar__history"
            role="group"
            aria-label="Current page"
          >
            <span>DocuTrust</span>
            <span aria-hidden="true">/</span>
            <span>{getPageTitle(location.pathname)}</span>
          </div>

          {canSearch ? (
            <label className="topbar__search">
              <SearchIcon className="topbar__search-icon" />
              <input
                type="search"
                placeholder="Search…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                aria-label="Search"
              />
            </label>
          ) : (
            <div className="topbar__spacer" />
          )}

          <div className="topbar__right">

            <button
              type="button"
              className="topbar__bell"
              aria-label="Notifications"
              title="Notifications"
            >
              <BellIcon />
            </button>

            <span className="topbar__avatar" aria-hidden="true">
              {sessionInitials(displayName)}
            </span>

            <span className="topbar__user">{displayName}</span>

          </div>
        </header>

        {/* Page content */}
        <SearchContext.Provider value={search}>
          <main className="app-main">
            <Outlet />
          </main>
        </SearchContext.Provider>

      </div>
    </div>
  );
}

function getPageTitle(pathname: string): string {
  if (pathname === '/' || pathname === '') {
    return 'Dashboard';
  }

  if (pathname === '/verify') {
    return 'Upload Document';
  }

  if (pathname === '/documents') {
    return 'Documents';
  }

  if (pathname === '/academic-summary') {
    return 'AI Academic Summary';
  }

  if (
    pathname.startsWith('/academic-summary/document/')
  ) {
    return 'Academic Document Preview';
  }

  if (pathname.startsWith('/documents/')) {
    return 'Document Details';
  }

  if (pathname.startsWith('/verifications/')) {
    if (pathname.endsWith('/review')) {
      return 'Review';
    }

    if (pathname.endsWith('/blockchain')) {
      return 'Blockchain Receipt';
    }

    return 'Verification Result';
  }

  if (pathname === '/review-queue') {
    return 'Review Queue';
  }

  if (pathname === '/history') {
    return 'History';
  }

  if (pathname === '/blockchain-receipts') {
    return 'Blockchain Receipts';
  }

  if (pathname.startsWith('/demo')) {
    return 'Demo Dashboard';
  }

  if (pathname === '/profile') {
    return 'Profile';
  }

  if (pathname === '/help') {
    return 'Help';
  }

  if (pathname === '/about') {
    return 'About';
  }

  return 'DocuTrust';
}
