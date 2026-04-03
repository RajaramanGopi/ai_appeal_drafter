# Downloaded payor forms (official PDFs)

PDFs in this folder are **copies of publicly posted** payer or CMS forms for local reference, offline access, and auditability. **Always** confirm you are using the **current** version on the payer’s or CMS website before submission; forms and instructions change.

| File | Source (verify before use) |
|------|----------------------------|
| `Medicare_CMS-20027_Redetermination.pdf` | CMS — Medicare redetermination (first-level appeal) |
| `Aetna_Provider_Complaint_And_Appeal_Request.pdf` | Aetna — healthcare professionals / disputes |
| `UnitedHealthcare_Claim_Reconsideration_Form.pdf` | UnitedHealthcare — UHCprovider.com claims |
| `Cigna_Request_For_Health_Care_Professional_Payment_Review.pdf` | Cigna — static provider appeal PDF |
| `BCBSM_Clinical_Editing_Reconsideration_Sample.pdf` | Blue Cross Blue Shield of Michigan — **example** clinical editing form (BCBS is plan-specific; not universal) |

## Trust and compliance

- These files are **not** legal advice. Operational teams should validate addresses, fax numbers, and deadlines against the **member’s EOB** or **plan portal**.
- Re-download after payer or CMS updates; update `knowledge_base/sources.txt` if landing URLs move.

## Re-download (PowerShell)

```powershell
$base = Join-Path $PSScriptRoot "."
Invoke-WebRequest -Uri "https://www.cms.gov/medicare/cms-forms/cms-forms/downloads/cms20027.pdf" -OutFile (Join-Path $base "Medicare_CMS-20027_Redetermination.pdf") -UseBasicParsing
Invoke-WebRequest -Uri "https://www.aetna.com/document-library/healthcare-professionals/documents-forms/provider-complaint-appeal-request.pdf" -OutFile (Join-Path $base "Aetna_Provider_Complaint_And_Appeal_Request.pdf") -UseBasicParsing
Invoke-WebRequest -Uri "https://www.uhcprovider.com/content/dam/provider/docs/public/claims/UHC-Single-Paper-Claim-Reconsideration-Form.pdf" -OutFile (Join-Path $base "UnitedHealthcare_Claim_Reconsideration_Form.pdf") -UseBasicParsing
Invoke-WebRequest -Uri "https://www.cigna.com/static/www-cigna-com/docs/appeal_request_others.pdf" -OutFile (Join-Path $base "Cigna_Request_For_Health_Care_Professional_Payment_Review.pdf") -UseBasicParsing
Invoke-WebRequest -Uri "https://www.bcbsm.com/amslibs/content/dam/public/providers/documents/forms/clinical-editing-form.pdf" -OutFile (Join-Path $base "BCBSM_Clinical_Editing_Reconsideration_Sample.pdf") -UseBasicParsing
```
