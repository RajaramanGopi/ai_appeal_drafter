---
payer: reference
title: Top payors denial and appeal playbook
---

# Top five payors: denial handling and appeal reliability

Use this playbook with the in-app **denial code** field and the **denial knowledge CSV**. It does **not** replace legal advice, plan documents, or the member’s **specific** EOB/portal instructions.

---

## Aetna (commercial / Medicare / Medicaid products vary)

**Typical denial themes**: medical necessity, prior authorization, coding/bundling, timely filing, eligibility.

**Appeal / review**: Formal written appeal or provider complaint/appeal process as described on Aetna’s healthcare professional **disputes and appeals** pages. Attach claim/EOB identifiers, DOS, codes, and clinical support for clinical denials.

**Reliability tips**: Match **product** (commercial vs Medicare Advantage vs Medicaid) to the correct submission channel; deadlines are often **180 days** for commercial but can vary by state or line of business.

---

## Blue Cross Blue Shield (BCBS)

**Typical denial themes**: plan-specific medical policies, authorization, out-of-network, coding edits, benefit limits.

**Appeal / review**: There is **no single national claim appeal form** for all BCBS plans. Use the **member’s plan** (state / licensee) forms, portal, or address on the EOB.

**Reliability tips**: Name the **exact plan** (e.g., Anthem, Horizon, BCBSM) in the appeal header; cite that plan’s medical policy or precert rules when disputing clinical denials.

---

## Cigna Healthcare

**Typical denial themes**: medical necessity, experimental/investigational, authorization, reimbursement edits, modifier disputes.

**Appeal / review**: Follow Cigna’s **healthcare professional** appeals and disputes instructions; payment review / appeal forms are published for provider use where applicable.

**Reliability tips**: Include EOP/EOB copy, original claim summary, and line-item reasons; clinical denials need **progress notes**, orders, and policy-aligned justification.

---

## Medicare (CMS — Part A, Part B, Part C, Part D)

**Typical denial themes**: LCD/NCD criteria, medical necessity, not medically reasonable and necessary, billing errors, timely filing.

**Appeal / review**: **Fee-for-service**: redetermination (MAC), then reconsideration (QIC), then further levels per CMS. **Medicare Advantage (Part C)** and **Part D**: plan reconsideration / grievance / coverage determination rules per CMS.

**Reliability tips**: Use **MBI**, claim number, and MAC jurisdiction; cite **LCD/NCD** or applicable CMS manual provisions when arguing medical necessity.

---

## UnitedHealthcare (UHC)

**Typical denial themes**: UHC medical policies, authorization, claim edits, benefit interpretation, Medicare Advantage compliance.

**Appeal / review**: Commercial: portal or written appeal per EOB. **Reconsideration** (claim payment dispute) is distinct from formal **appeal** in many UHC materials—use the path that matches the denial type.

**Reliability tips**: Reference **claim control number**, PRA/ERA codes, and line-level denial reasons; Medicare Advantage appeals follow **CMS timeframes** for plan-level decisions.

---

## Cross-cutting accuracy rules for live use

1. Never invent payer addresses, fax numbers, or deadlines—pull them from the **current** EOB, portal, or downloaded form in `payor_forms_downloads/`.
2. Prefer **structured** denial fields in the UI (CARC/RARC, CPT, ICD) so the model grounds the letter in the same codes the payer used.
3. Re-run **ingest** periodically after updating `sources.txt` so RAG snippets stay aligned with published pages.
