import ArticleRoundedIcon from '@mui/icons-material/ArticleRounded';
import DrawRoundedIcon from '@mui/icons-material/DrawRounded';
import {
  Alert,
  Box,
  Button,
  Divider,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import type { AppealDraftErrorBody, AppealDraftResponse } from '../types/appeal';
import { downloadTextFile } from '../utils/download';

export interface AppealResultsPanelProps {
  apiError: AppealDraftErrorBody | null;
  networkError: string | null;
  result: AppealDraftResponse | null;
  noFormInfo: string;
  filledFormText: string;
  onFilledFormChange: (value: string) => void;
  formDownloadSlug: string;
}

export function AppealResultsPanel({
  apiError,
  networkError,
  result,
  noFormInfo,
  filledFormText,
  onFilledFormChange,
  formDownloadSlug,
}: AppealResultsPanelProps) {
  const hasContent = Boolean(apiError || networkError || result);

  if (!hasContent) {
    return (
      <Box
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          py: 4,
          px: 2,
          minHeight: 280,
          borderRadius: 3,
          border: (t) => `2px dashed ${alpha(t.palette.primary.main, 0.22)}`,
          background: (t) =>
            `linear-gradient(160deg, ${alpha(t.palette.primary.main, 0.04)} 0%, ${alpha(t.palette.secondary.main, 0.05)} 100%)`,
        }}
      >
        <Box
          sx={{
            width: 72,
            height: 72,
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            mb: 2,
            background: (t) =>
              `linear-gradient(135deg, ${alpha(t.palette.primary.main, 0.18)} 0%, ${alpha(t.palette.secondary.main, 0.15)} 100%)`,
            color: 'primary.dark',
          }}
        >
          <DrawRoundedIcon sx={{ fontSize: 36 }} />
        </Box>
        <Typography variant="h2" sx={{ mb: 1, color: 'primary.dark' }}>
          Ready when you are
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 320 }}>
          Complete the claim details and generate an AI-assisted appeal letter. Your draft and any
          matched payer form will show up here.
        </Typography>
      </Box>
    );
  }

  return (
    <Stack spacing={2.25}>
      {apiError ? (
        <>
          <Alert severity="error" variant="outlined" role="alert" sx={{ borderWidth: 2 }}>
            {apiError.detail}
          </Alert>
          {apiError.resolution_steps.length > 0 ? (
            <Box
              sx={{
                borderRadius: 2,
                p: 2,
                background: (t) => alpha(t.palette.info.main, 0.08),
                border: (t) => `1px solid ${alpha(t.palette.info.main, 0.25)}`,
              }}
            >
              <Typography variant="subtitle2" gutterBottom sx={{ color: 'info.dark' }}>
                What to do next
              </Typography>
              <Box component="ol" sx={{ m: 0, pl: 2.5, '& li': { mb: 0.75 } }}>
                {apiError.resolution_steps.map((step) => (
                  <Typography key={step} component="li" variant="body2" color="text.secondary">
                    {step}
                  </Typography>
                ))}
              </Box>
            </Box>
          ) : null}
          <Typography variant="caption" color="text.secondary">
            correlation_id:{' '}
            <Box component="code" sx={{ bgcolor: 'action.hover', px: 0.75, py: 0.25, borderRadius: 1 }}>
              {apiError.correlation_id}
            </Box>
            {' — '}search <code>logs/appeal_drafter.log</code>.
          </Typography>
        </>
      ) : null}

      {networkError ? (
        <Alert severity="error" variant="outlined" sx={{ borderWidth: 2 }}>
          {networkError}
        </Alert>
      ) : null}

      {result ? (
        <>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
            <ArticleRoundedIcon color="primary" sx={{ fontSize: 28 }} />
            <Typography variant="h2" component="h2" sx={{ color: 'primary.dark' }}>
              Generated appeal letter
            </Typography>
          </Box>
          <Button
            variant="outlined"
            color="secondary"
            size="medium"
            onClick={() => downloadTextFile('appeal_letter.txt', result.appeal_text)}
            sx={{ alignSelf: 'flex-start' }}
          >
            Download appeal letter
          </Button>
          <Box
            component="pre"
            sx={{
              m: 0,
              p: 2.5,
              background: (t) =>
                `linear-gradient(180deg, ${alpha(t.palette.success.main, 0.06)} 0%, ${alpha(t.palette.primary.main, 0.04)} 100%)`,
              border: (t) => `1px solid ${alpha(t.palette.success.main, 0.2)}`,
              borderRadius: 2,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
              maxHeight: '50vh',
              overflow: 'auto',
              fontSize: '0.875rem',
              fontFamily: '"Consolas", "Monaco", "Courier New", ui-monospace, monospace',
              lineHeight: 1.65,
            }}
          >
            {result.appeal_text}
          </Box>

          {noFormInfo ? (
            <Alert severity="info" variant="outlined">
              {noFormInfo}
            </Alert>
          ) : null}

          {filledFormText ? (
            <>
              <Divider sx={{ my: 1 }} />
              <Typography variant="h2" component="h2" sx={{ color: 'secondary.dark' }}>
                Filled standard form · {result.filled_form_payor_name ?? 'Payer'}
              </Typography>
              <Button
                variant="outlined"
                color="secondary"
                size="medium"
                onClick={() =>
                  downloadTextFile(`appeal_form_${formDownloadSlug}.txt`, filledFormText)
                }
                sx={{ alignSelf: 'flex-start' }}
              >
                Download filled form
              </Button>
              <TextField
                multiline
                minRows={12}
                fullWidth
                value={filledFormText}
                onChange={(e) => onFilledFormChange(e.target.value)}
                size="small"
                label="Edit before download"
              />
            </>
          ) : null}

          <Typography variant="caption" color="text.secondary">
            correlation_id:{' '}
            <Box component="code" sx={{ bgcolor: 'action.hover', px: 0.75, py: 0.25, borderRadius: 1 }}>
              {result.correlation_id}
            </Box>
          </Typography>
        </>
      ) : null}
    </Stack>
  );
}
