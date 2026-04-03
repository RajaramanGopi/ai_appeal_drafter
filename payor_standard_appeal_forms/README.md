# Payor standard appeal forms

Place one folder per payor (e.g. `Aetna/`, `UnitedHealthcare/`). The app matches the **Payer Name** entered by the user to these folder names (case-insensitive; partial match is used if no exact match).

Inside each payor folder, add one or more form templates:

- **appeal_form.txt** – used when request type is "appeal"
- **reconsideration_form.txt** – used when request type is "reconsideration"
- **form.txt** – fallback if the above are missing

## Placeholders in templates

Use `{{PLACEHOLDER}}` in your `.txt` file. These are replaced when the form is filled:

| Placeholder      | Source                |
|------------------|-----------------------|
| `{{PATIENT_NAME}}` | Claim details         |
| `{{DATE_OF_SERVICE}}` | Claim details     |
| `{{PROVIDER_NAME}}`  | Claim details     |
| `{{PAYER_NAME}}`     | Claim details     |
| `{{DENIAL_CODE}}`    | Claim details     |
| `{{CPT_CODE}}`       | Claim details     |
| `{{ICD_CODE}}`       | Claim details     |
| `{{DENIAL_REASON}}`  | Claim details     |
| `{{REQUEST_DATE}}`   | Today’s date      |
| `{{APPEAL_BODY}}`    | AI-generated appeal letter |

## Bundled top payors

Folders **Aetna**, **BCBS**, **Cigna**, **Medicare**, and **UnitedHealthcare** ship with appeal and reconsideration `.txt` templates. Official PDF copies for reference and submission checks live in `payor_forms_downloads/` (see that folder’s README).

## Adding a new payor

1. Create a folder: `payor_standard_appeal_forms/YourPayorName/`
2. Add `appeal_form.txt` (and optionally `reconsideration_form.txt`) with the payor’s form text and the placeholders above.
3. Restart or refresh the app; the payor will appear in the sidebar and the form will be used when Payer Name matches.
