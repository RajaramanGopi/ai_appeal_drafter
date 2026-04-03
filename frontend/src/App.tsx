import AutoAwesomeRoundedIcon from '@mui/icons-material/AutoAwesomeRounded';
import DescriptionRoundedIcon from '@mui/icons-material/DescriptionRounded';
import { AppBar, Box, Chip, Container, Paper, Toolbar, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import { AppealResultsPanel } from './components/AppealResultsPanel';
import { ClaimDetailsForm } from './components/ClaimDetailsForm';
import { useAppealDraft } from './hooks/useAppealDraft';

export default function App() {
  const draft = useAppealDraft();

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          background: 'linear-gradient(120deg, #0f766e 0%, #0e7490 42%, #1d4ed8 100%)',
          borderBottom: (t) => `1px solid ${alpha(t.palette.common.white, 0.15)}`,
        }}
      >
        <Toolbar
          sx={{
            py: 1.25,
            gap: 2,
            flexWrap: 'wrap',
            alignItems: { xs: 'flex-start', sm: 'center' },
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexGrow: 1, minWidth: 0 }}>
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 44,
                height: 44,
                borderRadius: 2,
                bgcolor: alpha('#fff', 0.18),
                color: 'common.white',
                flexShrink: 0,
              }}
              aria-hidden
            >
              <DescriptionRoundedIcon sx={{ fontSize: 26 }} />
            </Box>
            <Box sx={{ minWidth: 0 }}>
              <Typography
                variant="h6"
                component="h1"
                sx={{
                  color: 'common.white',
                  fontWeight: 800,
                  letterSpacing: '-0.02em',
                  lineHeight: 1.25,
                }}
              >
                Appeal Drafter AI
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  color: alpha('#fff', 0.88),
                  display: 'block',
                  mt: 0.25,
                  fontWeight: 500,
                }}
              >
                US healthcare · Medical billing · Denial appeals
              </Typography>
            </Box>
          </Box>
          <Chip
            icon={<AutoAwesomeRoundedIcon sx={{ color: `${alpha('#fff', 0.95)} !important` }} />}
            label="AI-assisted drafting"
            size="small"
            sx={{
              bgcolor: alpha('#fff', 0.2),
              color: 'common.white',
              fontWeight: 700,
              border: `1px solid ${alpha('#fff', 0.35)}`,
              backdropFilter: 'blur(8px)',
              '& .MuiChip-label': { px: 1 },
            }}
          />
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ py: { xs: 2.5, md: 4 }, flex: 1, position: 'relative' }}>
        {/* Soft decorative orbs */}
        <Box
          aria-hidden
          sx={{
            pointerEvents: 'none',
            position: 'absolute',
            top: -40,
            right: -60,
            width: 280,
            height: 280,
            borderRadius: '50%',
            background: (t) => `radial-gradient(circle, ${alpha(t.palette.primary.main, 0.12)} 0%, transparent 70%)`,
            zIndex: 0,
          }}
        />
        <Box
          aria-hidden
          sx={{
            pointerEvents: 'none',
            position: 'absolute',
            bottom: 80,
            left: -80,
            width: 320,
            height: 320,
            borderRadius: '50%',
            background: (t) => `radial-gradient(circle, ${alpha(t.palette.secondary.main, 0.1)} 0%, transparent 70%)`,
            zIndex: 0,
          }}
        />

        <Box sx={{ position: 'relative', zIndex: 1 }}>
          <Paper
            sx={{
              px: { xs: 2, sm: 3 },
              py: { xs: 2, sm: 2.5 },
              mb: 3,
              borderRadius: 3,
              background: (t) =>
                `linear-gradient(135deg, ${alpha(t.palette.common.white, 0.92)} 0%, ${alpha('#ecfeff', 0.85)} 100%)`,
              border: (t) => `1px solid ${alpha(t.palette.primary.main, 0.12)}`,
              boxShadow: '0 8px 32px rgba(15, 118, 110, 0.08)',
            }}
          >
            <Typography variant="body1" color="text.secondary" sx={{ maxWidth: '62rem' }}>
              Turn claim and payer denial details into a clear, professional appeal letter. Optional
              payer-specific forms are filled when templates match your{' '}
              <Box component="span" sx={{ color: 'primary.dark', fontWeight: 600 }}>
                payor_standard_appeal_forms
              </Box>{' '}
              library — built for revenue cycle and billing teams.
            </Typography>
          </Paper>

          <Box
            sx={{
              display: 'grid',
              gap: { xs: 2.5, md: 3 },
              gridTemplateColumns: { xs: '1fr', md: 'minmax(300px, 400px) 1fr' },
              alignItems: 'start',
            }}
          >
            <Paper
              sx={{
                p: { xs: 2, sm: 2.75 },
                overflow: 'hidden',
                position: 'relative',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  height: 4,
                  background: 'linear-gradient(90deg, #14b8a6, #2563eb)',
                  borderRadius: '16px 16px 0 0',
                },
              }}
            >
              <ClaimDetailsForm
                form={draft.form}
                onFieldChange={draft.setFormField}
                onSubmit={draft.submit}
                loading={draft.loading}
                payorsCaption={draft.payorsCaption}
              />
            </Paper>

            <Paper
              sx={{
                p: { xs: 2, sm: 2.75 },
                minHeight: { md: 360 },
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <AppealResultsPanel
                apiError={draft.apiError}
                networkError={draft.networkError}
                result={draft.result}
                noFormInfo={draft.noFormInfo}
                filledFormText={draft.filledFormText}
                onFilledFormChange={draft.setFilledFormText}
                formDownloadSlug={draft.formDownloadSlug}
              />
            </Paper>
          </Box>
        </Box>
      </Container>
    </Box>
  );
}
