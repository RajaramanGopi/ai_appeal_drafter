import { alpha, createTheme } from '@mui/material/styles';

/**
 * Visual identity: US healthcare revenue cycle / medical billing — trustworthy,
 * calm, and slightly vibrant (teal + clinical blue) with clear AI-assisted cues.
 */
const fontStack = '"Plus Jakarta Sans", "Segoe UI", system-ui, -apple-system, sans-serif';

export const appTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#0f766e',
      light: '#14b8a6',
      dark: '#0d5c54',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#2563eb',
      light: '#3b82f6',
      dark: '#1d4ed8',
      contrastText: '#ffffff',
    },
    success: {
      main: '#059669',
      light: '#34d399',
      dark: '#047857',
    },
    info: {
      main: '#0891b2',
      light: '#22d3ee',
      dark: '#0e7490',
    },
    error: {
      main: '#dc2626',
    },
    warning: {
      main: '#d97706',
    },
    text: {
      primary: '#0f172a',
      secondary: '#475569',
    },
    background: {
      default: '#e8f4f2',
      paper: '#ffffff',
    },
    divider: alpha('#0f766e', 0.14),
  },
  shape: {
    borderRadius: 12,
  },
  typography: {
    fontFamily: fontStack,
    h1: { fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em', lineHeight: 1.2 },
    h2: { fontSize: '1.125rem', fontWeight: 700, letterSpacing: '-0.01em' },
    h6: { fontWeight: 700, letterSpacing: '-0.01em' },
    subtitle1: { fontWeight: 600, fontSize: '1rem' },
    body1: { fontSize: '0.9375rem', lineHeight: 1.6 },
    body2: { fontSize: '0.875rem', lineHeight: 1.55 },
    caption: { fontSize: '0.75rem', lineHeight: 1.5 },
    overline: {
      fontSize: '0.6875rem',
      fontWeight: 700,
      letterSpacing: '0.12em',
    },
    button: { fontWeight: 700, letterSpacing: '0.02em' },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundAttachment: 'fixed',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: ({ theme }) => ({
          textTransform: 'none',
          borderRadius: 12,
          cursor: 'pointer',
          fontWeight: 700,
          letterSpacing: '0.02em',
          transition: theme.transitions.create(
            ['transform', 'box-shadow', 'background-color', 'background', 'border-color', 'color', 'opacity'],
            { duration: theme.transitions.duration.short },
          ),
          '&:focus-visible': {
            outline: `3px solid ${alpha(theme.palette.primary.main, 0.45)}`,
            outlineOffset: 2,
          },
          '&.Mui-disabled': {
            cursor: 'not-allowed',
            opacity: 0.55,
          },
        }),
        sizeSmall: {
          minHeight: 36,
          padding: '8px 18px',
          fontSize: '0.8125rem',
        },
        sizeMedium: {
          minHeight: 44,
          padding: '11px 24px',
          fontSize: '0.875rem',
        },
        sizeLarge: {
          minHeight: 52,
          padding: '14px 32px',
          fontSize: '1rem',
          lineHeight: 1.3,
        },
        containedPrimary: {
          background: 'linear-gradient(135deg, #0d9488 0%, #0891b2 45%, #2563eb 100%)',
          boxShadow: '0 4px 14px rgba(13, 148, 136, 0.38)',
          color: '#ffffff',
          '&:hover:not(.Mui-disabled)': {
            background: 'linear-gradient(135deg, #0f766e 0%, #0e7490 45%, #1d4ed8 100%)',
            boxShadow: '0 8px 24px rgba(13, 148, 136, 0.48)',
            transform: 'translateY(-2px)',
          },
          '&:active:not(.Mui-disabled)': {
            background: 'linear-gradient(135deg, #0d5c54 0%, #0c6b7e 45%, #1e40af 100%)',
            boxShadow: '0 2px 10px rgba(13, 148, 136, 0.35)',
            transform: 'translateY(0) scale(0.98)',
          },
          '&.Mui-disabled': {
            background: 'linear-gradient(135deg, #94a3b8 0%, #64748b 100%)',
            boxShadow: 'none',
            transform: 'none',
            color: 'rgba(255,255,255,0.92)',
            opacity: 0.65,
          },
        },
        outlined: ({ theme }) => ({
          borderWidth: 2,
          transition: theme.transitions.create(
            ['transform', 'box-shadow', 'background-color', 'border-color'],
            { duration: theme.transitions.duration.short },
          ),
          '&:hover': { borderWidth: 2 },
        }),
        outlinedPrimary: ({ theme }) => ({
          borderColor: alpha(theme.palette.primary.main, 0.45),
          color: theme.palette.primary.dark,
          backgroundColor: alpha(theme.palette.common.white, 0.65),
          '&:hover:not(.Mui-disabled)': {
            borderColor: theme.palette.primary.main,
            backgroundColor: alpha(theme.palette.primary.main, 0.08),
            transform: 'translateY(-1px)',
            boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.18)}`,
          },
          '&:active:not(.Mui-disabled)': {
            transform: 'translateY(0) scale(0.98)',
            boxShadow: 'none',
            backgroundColor: alpha(theme.palette.primary.main, 0.14),
          },
        }),
        outlinedSecondary: ({ theme }) => ({
          borderColor: alpha(theme.palette.secondary.main, 0.55),
          color: theme.palette.secondary.dark,
          backgroundColor: alpha(theme.palette.common.white, 0.75),
          '&:hover:not(.Mui-disabled)': {
            borderColor: theme.palette.secondary.main,
            backgroundColor: alpha(theme.palette.secondary.main, 0.1),
            transform: 'translateY(-1px)',
            boxShadow: `0 4px 14px ${alpha(theme.palette.secondary.main, 0.22)}`,
          },
          '&:active:not(.Mui-disabled)': {
            transform: 'translateY(0) scale(0.98)',
            boxShadow: 'none',
            backgroundColor: alpha(theme.palette.secondary.main, 0.18),
          },
        }),
      },
    },
    MuiPaper: {
      defaultProps: {
        elevation: 0,
      },
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          borderRadius: 16,
          border: `1px solid ${alpha('#0f766e', 0.1)}`,
          boxShadow: '0 4px 24px rgba(15, 118, 110, 0.07), 0 1px 3px rgba(15, 23, 42, 0.04)',
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        variant: 'outlined',
      },
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 10,
            backgroundColor: alpha('#ffffff', 0.9),
            transition: 'box-shadow 0.2s ease, border-color 0.2s ease',
            '&:hover fieldset': {
              borderColor: alpha('#0f766e', 0.35),
            },
            '&.Mui-focused': {
              boxShadow: `0 0 0 3px ${alpha('#14b8a6', 0.22)}`,
            },
          },
        },
      },
    },
    MuiFormLabel: {
      styleOverrides: {
        root: {
          fontWeight: 600,
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        root: {
          borderRadius: 10,
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
        standardInfo: {
          backgroundColor: alpha('#0891b2', 0.1),
          color: '#0e7490',
          border: `1px solid ${alpha('#0891b2', 0.25)}`,
        },
        standardSuccess: {
          backgroundColor: alpha('#059669', 0.1),
          color: '#047857',
          border: `1px solid ${alpha('#059669', 0.25)}`,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        filled: {
          fontWeight: 700,
        },
      },
    },
  },
});
