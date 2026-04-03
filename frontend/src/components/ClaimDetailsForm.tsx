import AssignmentIndRoundedIcon from '@mui/icons-material/AssignmentIndRounded';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import type { AppealDraftRequest, RequestType } from '../types/appeal';

export interface ClaimDetailsFormProps {
  form: AppealDraftRequest;
  onFieldChange: <K extends keyof AppealDraftRequest>(key: K, value: AppealDraftRequest[K]) => void;
  onSubmit: () => void;
  loading: boolean;
  payorsCaption: string;
}

export function ClaimDetailsForm({
  form,
  onFieldChange,
  onSubmit,
  loading,
  payorsCaption,
}: ClaimDetailsFormProps) {
  return (
    <Box
      component="form"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      noValidate
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25, mb: 2.5, mt: 0.5 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 40,
            height: 40,
            borderRadius: 2,
            background: (t) =>
              `linear-gradient(135deg, ${alpha(t.palette.primary.main, 0.15)} 0%, ${alpha(t.palette.secondary.main, 0.12)} 100%)`,
            color: 'primary.dark',
          }}
        >
          <AssignmentIndRoundedIcon />
        </Box>
        <Box>
          <Typography
            variant="overline"
            sx={{
              color: 'primary.dark',
              display: 'block',
              lineHeight: 1.2,
            }}
          >
            Claim intake
          </Typography>
          <Typography variant="subtitle1" color="text.primary" sx={{ mt: 0.25 }}>
            Denial &amp; claim details
          </Typography>
        </Box>
      </Box>

      <Stack spacing={2.25}>
        <TextField
          label="Payer name"
          value={form.payer}
          onChange={(e) => onFieldChange('payer', e.target.value)}
          placeholder="Aetna, BCBS, Cigna, Medicare, UnitedHealthcare…"
          fullWidth
          size="small"
          helperText="Match a payor folder under payor_standard_appeal_forms/ for auto-filled templates."
        />

        <FormControl fullWidth size="small">
          <InputLabel id="request-type-label">Request type</InputLabel>
          <Select<RequestType>
            labelId="request-type-label"
            label="Request type"
            value={form.request_type}
            onChange={(e) => onFieldChange('request_type', e.target.value as RequestType)}
          >
            <MenuItem value="appeal">Appeal</MenuItem>
            <MenuItem value="reconsideration">Reconsideration</MenuItem>
          </Select>
        </FormControl>

        <TextField
          label="Denial code (CARC / RARC)"
          value={form.denial_code}
          onChange={(e) => onFieldChange('denial_code', e.target.value)}
          fullWidth
          size="small"
        />
        <TextField
          label="CPT code"
          value={form.cpt_code}
          onChange={(e) => onFieldChange('cpt_code', e.target.value)}
          fullWidth
          size="small"
        />
        <TextField
          label="ICD code"
          value={form.icd_code}
          onChange={(e) => onFieldChange('icd_code', e.target.value)}
          fullWidth
          size="small"
        />
        <TextField
          label="Denial reason"
          value={form.denial_reason}
          onChange={(e) => onFieldChange('denial_reason', e.target.value)}
          fullWidth
          size="small"
          multiline
          minRows={3}
        />
        <TextField
          label="Patient name"
          value={form.patient_name}
          onChange={(e) => onFieldChange('patient_name', e.target.value)}
          fullWidth
          size="small"
        />
        <TextField
          label="Date of service"
          value={form.dos}
          onChange={(e) => onFieldChange('dos', e.target.value)}
          fullWidth
          size="small"
        />
        <TextField
          label="Provider name"
          value={form.provider}
          onChange={(e) => onFieldChange('provider', e.target.value)}
          fullWidth
          size="small"
        />

        <Button
          type="submit"
          variant="contained"
          color="primary"
          size="large"
          disabled={loading}
          fullWidth
          sx={{ mt: 1 }}
        >
          {loading ? (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <CircularProgress size={22} color="inherit" thickness={4} />
              Drafting your appeal…
            </Box>
          ) : (
            'Generate appeal letter'
          )}
        </Button>

        {payorsCaption ? (
          <Alert severity="info" icon={false} sx={{ mt: 0.5 }}>
            <Typography variant="caption" component="span" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
              Standard forms on file
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {payorsCaption}
            </Typography>
          </Alert>
        ) : null}
      </Stack>
    </Box>
  );
}
