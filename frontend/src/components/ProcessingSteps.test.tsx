import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProcessingSteps } from './ProcessingSteps';

describe('ProcessingSteps', () => {
  it('renders each step with the correct state', () => {
    render(
      <ProcessingSteps
        steps={[
          { label: 'Document uploaded', state: 'done' },
          { label: 'Reading and comparing', state: 'active' },
          { label: 'Preparing result', state: 'pending' },
        ]}
      />
    );

    const items = screen.getAllByRole('listitem');
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent('Document uploaded');
    expect(items[0]).toHaveAttribute('data-state', 'done');
    expect(items[1]).toHaveAttribute('data-state', 'active');
    expect(items[1]).toHaveTextContent('in progress');
    expect(items[2]).toHaveAttribute('data-state', 'pending');
  });

  it('advances only when the steps prop changes, never on a timer', () => {
    const { rerender } = render(
      <ProcessingSteps steps={[{ label: 'Reading and comparing', state: 'active' }]} />
    );

    expect(screen.getByRole('listitem')).toHaveAttribute('data-state', 'active');

    rerender(<ProcessingSteps steps={[{ label: 'Reading and comparing', state: 'done' }]} />);
    expect(screen.getByRole('listitem')).toHaveAttribute('data-state', 'done');
  });
});

const RAW_SOURCES = import.meta.glob('./../**/*.{ts,tsx}', {
  eager: true,
  query: '?raw',
  import: 'default',
}) as Record<string, string>;

describe('processing uses no timers', () => {
  const sources = Object.entries(RAW_SOURCES).filter(
    ([path]) => !path.includes('.test.') && !path.includes('/test/') && !path.includes('setup')
  );

  it('has no scripted progress timers in non-test source', () => {
    const offenders = sources
      .map(([path, content]) =>
        /setInterval|\bsetTimeout\s*\(/.test(content)
          ? `${path}: ${content.match(/setInterval|\bsetTimeout\s*\(/)?.[0]}`
          : undefined
      )
      .filter((line): line is string => Boolean(line));

    expect(offenders).toEqual([]);
  });
});