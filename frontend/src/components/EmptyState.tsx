import type { ReactNode } from 'react';

interface EmptyStateProps {
  title: ReactNode;
  message: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ title, message, icon, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      {icon ? <div className="empty-state__icon" aria-hidden="true">{icon}</div> : null}
      <h2>{title}</h2>
      <p>{message}</p>
      {action ? <div className="empty-state__action">{action}</div> : null}
    </div>
  );
}