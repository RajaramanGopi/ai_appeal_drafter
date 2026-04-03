import { CssBaseline, ThemeProvider } from '@mui/material';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { appTheme } from './theme/appTheme';

function renderWithProviders(ui: ReactElement) {
  return render(
    <ThemeProvider theme={appTheme}>
      <CssBaseline />
      {ui}
    </ThemeProvider>,
  );
}

describe('App', () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn((input: RequestInfo) => {
        const url = typeof input === 'string' ? input : input.url;
        if (url.includes('/api/v1/payors')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ payors: [] }),
          } as Response);
        }
        return Promise.resolve({ ok: false, status: 404 } as Response);
      }),
    );
  });

  it('renders primary heading', async () => {
    renderWithProviders(<App />);
    expect(screen.getByRole('heading', { name: /appeal drafter ai/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(fetch).toHaveBeenCalled();
    });
  });

  it('renders generate action', () => {
    renderWithProviders(<App />);
    expect(screen.getByRole('button', { name: /generate appeal letter/i })).toBeInTheDocument();
  });
});
