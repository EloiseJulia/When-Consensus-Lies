# Phase 2 — Delivery Report (harness + metrics + labeling + integration)

> Manager delivery report. Phase-2 ENGINEERING is complete and merged to `main`. The remaining
> Phase-2 item — the **pre-registration freeze** — is owner-gated (Hard Law 7) and BLOCKS the MVP
> pilot and any full-scale run.

## Status: Phase-2 engineering COMPLETE ✅
`main` @ `90f3b2a`. Full suite independently verified on main: **`pytest -q` → 221 passed**.

## Merged slices
| Slice | PR | What | Provenance (impl → audit) |
|-------|----|------|---------------------------|
| S2a metrics | #6 | `convergent_delusion` PRIMARY + `marginal_rho`/`a_maj`/`ece`/`confidence_accuracy_slope`, golden tests | Claude → GPT (clean) |
| S2c run | #8 | 6 configs (single/sc/homogeneous-MAD/heterogeneous-MAD/verifier/interpretation-diverse) | Claude → GPT (clean after 5 fixes) |
| dataflaky fix | #7 | infra-error retry + cache discipline (subprocess harness) | Claude → GPT (clean) |
| **S2b label** | **#9** | executable-signal labeling; policy_qa structured-answer contract; parser hardened (string-aware JSON, strict ASCII money, conflict/empty/non-finite → I_perp, never raises) | Claude → GPT, **4 audit rounds → PASS** |
| **S2e answer-format** | **#10** | per-domain answer-format instruction in all 6 configs so prompts match the labeler | Claude → GPT (clean) |
| **S2d integration** | **#11** | real run→label→metrics; controlled golden `convergent_delusion=0.6`, `a_maj=0.0`; real-`run_task` wiring pass | Claude → GPT (clean, golden values independently recomputed) |

Cross-family provenance (implementer Claude ≠ auditor GPT) held on EVERY slice. `common/schema.py`
FROZEN and untouched throughout; no `config.yaml` changes in the label/answer-format/integration slices.

## Manager rulings this phase (owner-reversible)
- **policy_qa extra JSON keys:** the labeler accepts a JSON object with a finite `amount` even with
  extra keys (only *disagreeing* amounts → I_perp). Rationale: strict-exact rejection would inflate the
  I_perp rate on cooperative agents, biasing the primary metric. Documented in prereg §7.
- **Parser threat model:** cooperative-agent; exotic/adversarial inputs that correctly resolve to
  I_perp are out of scope; the invariant enforced is "never raise, never mislabel a plausible
  cooperative output." (Consistent with the merged harness threat model, PR #7 lineage.)

## What is DONE vs what remains
- DONE: benchmark (3 domains), metrics (primary locked), run (6 configs), executable-gold labeling,
  answer-format prompt contract, real end-to-end integration with a golden convergent-delusion value.
- REMAINING (owner-gated, Hard Law 7): **freeze the pre-registration** (`paper/preregistration/
  2026-07-15-prereg.md`, currently DRAFT) → then the **MVP pilot** (small real batch: confirm
  convergent_delusion >0 on real vs ≈0 under label-shuffle, per prereg §11) → then full-scale runs /
  Phase 3 detector.

## Immediate next action (BLOCKED on owner)
Owner review + sign-off of the draft pre-registration — especially §2 (construction-time H1/H2 regime
criterion), §4 (co-primary robustness nulls), §7 (answer-format + extra-keys ruling), §9 (decision
rules). On sign-off, the Manager freezes it (removes DRAFT banner, records the freeze SHA), then spawns
the MVP-pilot sub-agent. No full-scale run or metric-definition change occurs before the freeze.
