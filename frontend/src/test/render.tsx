import { render } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import type { ReactElement } from 'react';

interface RenderWithRouterOptions {
  route?: string;
  path?: string;
}

export function renderWithRouter(ui: ReactElement, { route = '/', path = '*' }: RenderWithRouterOptions = {}) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path={path} element={ui} />
      </Routes>
    </MemoryRouter>
  );
}