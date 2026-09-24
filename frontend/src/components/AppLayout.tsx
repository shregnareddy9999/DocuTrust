import { useState } from 'react';
import { NavLink, Outlet, useLocation, type NavLinkRenderProps } from 'react-router-dom';
import { SearchContext } from '../state/shellSearch';
import {
  AboutIcon,
  BellIcon,
  CloseIcon,
  DashboardIcon,
  DemoIcon,
  DocumentsIcon,
  HelpIcon,
  HistoryIcon,
  MenuIcon,
  ProfileIcon,
  ReviewIcon,
  SearchIcon,
  ShieldIcon,
  UploadIcon,
  type IconProps,
} from './icons';

const SEARCHABLE_ROUTES = ['/', '/documents', '/review-queue', '/history'];

interface NavItem {
  to: string;
  label: string;
  Icon: (props: IconProps) => React.ReactElement;
  end?: boolean;
}

const NAV_MAIN: NavItem[] = [
  { to: '/', label: 'Dashboard', Icon: DashboardIcon, end: true },
  { to: '/verify', label: 'Verify Document', Icon: UploadIcon },
  { to: '/documents', label: 'Documents', Icon: DocumentsIcon },
  { to: '/review-queue', label: 'Review Queue', Icon: ReviewIcon },
  { to: '/history', label: 'History', Icon: HistoryIcon },
];

const NAV_SETTINGS: NavItem[] = [
  { to: '/demo', label: 'Demo Mode', Icon: DemoIcon },
  { to: '/profile', label: 'Profile', Icon: ProfileIcon },
  { to: '/help', label: 'Help', Icon: HelpIcon },
  { to: '/about', label: 'About', Icon: AboutIcon },
];

function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const navClass = ({ isActive }: NavLinkRenderProps) =>
    `sidebar-link${isActive ? ' sidebar-link--active' : ''}`;

  return (
    <nav className="sidebar-nav" aria-label="Primary">
      <div className="sidebar-group">
        {NAV_MAIN.map(({ to, label, Icon }) => (
          <NavLink key={to} to={to} end className={navClass} onClick={onNavigate}>
            <Icon className="sidebar-link__icon" />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>
      <div className="sidebar-group sidebar-group--settings">
        {NAV_SETTINGS.map(({ to, label, Icon }) => (
          <NavLink key={to} to={to} className={navClass} onClick={onNavigate}>
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
  const [search, setSearch] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);

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
          <span className="sidebar-brand__mark" aria-hidden="true">
            <ShieldIcon />
          </span>
          <span className="sidebar-brand__text">
            <strong>DOCUTRUST</strong>
            <small>Document Verification Platform</small>
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
              DU
            </span>
            <span className="topbar__user">Demo user</span>
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