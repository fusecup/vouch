# Vouch — PRD

**Hackathon:** Cursor × Briefcase · Halkin Offices · London 2026
**Tracks:** Hybrid — primary **Track 01 Money Movement**, with **Track 02 Financial Intelligence** as the gating mechanism.
**Team:** 3
**One-liner:** *Vouch is a tiered guardrail layer for an agent that moves money — auto-approving the boring, swiping the borderline, and biometrically vouching for the dangerous.*

---

## 1. Problem

Finance agents that move money are now technically capable of running payroll, paying invoices, and sweeping cash. The blocker is no longer capability — it is **trust calibration**. Today's options are binary: either the agent has authority and a fraud incident bankrupts you, or every transaction needs a human and the agent is theatre.

Vouch makes the trust gradient explicit. The agent acts alone where it should, asks lightly where it should ask lightly, and demands a wall of human attestation where the money is large enough to matter.

## 2. Users

- **Primary:** Finance lead at a 10–500 person business (CFO / Head of Finance / Founder-operator).
- **Approvers:** Founders, exec team, designated approvers — the people who get pinged.
- **Counterparties:** Vendors, payroll recipients, intercompany accounts.

## 3. The Three-Tier Guardrail

The product *is* the escalation ladder. Each tier has a distinct UI, distinct latency target, and distinct failure mode.

### Tier 0 — Silent auto-approve
- **Triggers:** Known counterparty, amount inside historical band, no anomaly signal, healthy Specter score on the recipient entity.
- **UI:** None. Receipt drops in dashboard + Slack with one-click "this was wrong" reverse-link.
- **Latency target:** < 2s end-to-end.
- **Failure mode:** Agent paid something it shouldn't. Mitigation: every Tier 0 is reversible-by-default for 60 minutes; log + Slack ping per action.

### Tier 1 — Tinder swipe
- **Triggers:** Mid-band amount, mild anomaly, first-time vendor with *acceptable* Specter signal, or category drift.
- **UI:** Mobile card stack — vendor logo, amount, "why this is being asked" (1 line LLM summary), Specter mini-card (funding, headcount trend, last news), historical context. **Swipe right = approve, left = reject, up = ask agent for more, down = escalate to Tier 2.**
- **Latency target:** < 5s of approver attention per card.
- **Approvers:** Single designated approver, fall-through to second after 10 min.
- **Failure mode:** Approval fatigue, rubber-stamping. Mitigation: max 20 cards/day per approver; auto-escalate excess.

### Tier 2 — Biometric vouch
- **Triggers:** High-band amount (configurable, default £10k+), strong anomaly score, poor Specter signal (shell-like, dormant, sanctioned-adjacent), multiple risk factors stacked, or *any* request to a never-seen recipient over £25k.
- **UI:** Native iOS app, edge-only.
  1. **Face ID** challenge (Apple Secure Enclave).
  2. **5–8s video selfie** reading a randomized challenge phrase containing the amount and recipient name (anti-replay).
  3. On-device **facial emotion** classification (Vision + CoreML — neutral / stressed / fearful / coerced).
  4. On-device **voice emotion** + speaker-verification (Apple Speech + sound classifier).
  5. Distress-signal heuristics (forced-cadence speech, micro-expression mismatch) flag the attestation as *coerced* even if Face ID passes.
- **Multi-party:** 3–4 approvers must each complete the biometric flow within a 30-min window. Coerced flags from any one approver block the txn.
- **Latency target:** < 90s per approver.
- **Failure mode:** Coerced approval (kidnap / phishing / SIM-swap social engineering). Mitigation: emotion-flag short-circuits, randomized challenge phrase prevents pre-recorded replay, geolocation diversity check across approvers.

## 4. The Agent Loop

```
                    ┌─────────────────────────┐
   Txn intent ─────▶│  Risk scorer (LLM +     │
   (from rails)     │  Specter + history)     │
                    └────────────┬────────────┘
                                 │ score + reasons
                    ┌────────────▼────────────┐
                    │   Tier router            │
                    │   (deterministic rules   │
                    │    + LLM tie-breaker)    │
                    └─┬──────────┬───────────┬─┘
                      │          │           │
                  Tier 0      Tier 1      Tier 2
                  execute     swipe        biometric vouch
                      │          │           │
                      └──────────┴───────────┘
                                 │
                          Rails executor ──▶ ledger + receipt
```

Two LLM roles, deliberately split:
- **Risk scorer** — Claude Haiku 4.5 (cheap, fast, runs on every txn). Outputs: risk score 0–100, top-3 reasons, recommended tier.
- **Explainer** — Claude Opus 4.7 (called only on Tier 1+). Generates the "why this is being asked" line, vendor summary, and post-hoc audit narrative.

## 5. Architecture

| Layer | Stack | Owner |
|---|---|---|
| Money rails | Stripe Issuing / Plaid sandbox / Mercury sandbox | Member A |
| Agent + risk scoring | Django (existing base) + Celery, Cursor SDK for the agent runtime, Anthropic SDK for Haiku/Opus, Specter API + MCP | Member B |
| Tier 1 web/mobile-web swipe UI | Next.js + shadcn, deployed on Vercel; push via Web Push / SMS fallback | Member B (shared) |
| Tier 2 native iOS app | SwiftUI + Vision + CoreML + AVFoundation + LocalAuthentication | Member C |
| Dashboard / activity log | Django + HTMX (already in base) | Member A (shared) |

The existing repo is a Django/Docker/Postgres/Celery base — agent and ledger live there. iOS app is a sibling project; talks to Django over signed REST.

## 6. Specter Integration (bonus signal)

Specter is the **counterparty risk oracle**. Whenever a transaction names a recipient entity:
- Resolve recipient → Specter company ID (fuzzy match on name + domain + bank details).
- Pull: funding stage, headcount trend (3-month delta), recent news flags, founding date, signals matrix.
- Convert into a 0–100 **counterparty quality score**.
- Score directly shifts the tier threshold: a Specter-strong recipient drops one tier band; a Specter-empty recipient over £5k jumps to Tier 2 regardless of amount.
- Surface the Specter mini-card inside Tier 1 swipe and Tier 2 biometric review screens.

MCP path used in the agent runtime; raw API path used for the dashboard's vendor-detail drill-down.

## 7. Demo Script — 90 Seconds

| t | What the judge sees |
|---|---|
| 0–10s | Dashboard live: 12 invoices arrived in the last hour. 9 already auto-paid (Tier 0). Receipts streaming. |
| 10–25s | A £4,200 invoice to a new vendor pops on the presenter's phone as a Tinder card. Specter mini-card shows the vendor is a real seed-stage co. Swipe right. Paid. |
| 25–45s | A £62,000 transfer triggers. Tier 2 escalation fires to **the actual judges' phones** (pre-enrolled). Face ID prompt → randomized challenge phrase ("authorize sixty-two thousand to Acme on April thirty"). Voice + face captured. |
| 45–70s | On-device emotion panel renders live: neutral / confident. Three approvers complete. Money moves. |
| 70–90s | Re-run the same £62k txn, but this time the presenter reads the phrase under fake duress (rushed cadence). Coerced flag fires red, txn blocks. *That* is the moment. |

## 8. Scoring Rubric Map

| Criterion | Pts | How Vouch lands it |
|---|---|---|
| Concrete workflow value | 2 | Replaces the "everyone CC'd on every payment approval" Slack chaos with calibrated automation. Quantified: the Tier 0 stat live on stage. |
| Track fit (hybrid) | 2 | Tier 0/2 = money movement; Tier 0→1→2 routing = financial intelligence. The intelligence isn't a side feature — it is the gate. |
| Human-in-the-loop | 1 | Three discrete tiers with explicit thresholds, confidence gates (Specter + LLM score), multi-party Tier 2, coercion detection as a *third* axis beyond authentication. |
| Technical execution | 1 | Real rails (Member A), edge biometrics with on-device ML (Member C), Cursor SDK agent runtime (Member B). Three integrations that all work in the demo. |
| Demo clarity | 1 | The duress-replay moment in the last 20s is the entire pitch in one beat. |
| **Best use of Cursor** | +1 | Cursor SDK runs the agent loop in production (not just the IDE built it). |
| **Best use of Specter** | +1 | Counterparty quality score *changes the tier threshold* — Specter is load-bearing, not decorative. |
| **Best use of LLM models** | +1 | Two-model split: Haiku for per-txn scoring (cost), Opus for the human-facing explanation (quality). Coercion classifier is a separate small model. |

## 9. 48-Hour Build Plan

**Day 1 — morning (kickoff → 4h)**
- A: Stand up Stripe / Plaid / Mercury sandbox; produce 50 synthetic txns.
- B: Wire Cursor SDK agent skeleton, Anthropic SDK keys, Specter MCP. Risk-score endpoint accepts a txn → returns score.
- C: Xcode project, Face ID flow, video capture flow. No ML yet.

**Day 1 — afternoon (4h)**
- A: Tier router rules engine + ledger.
- B: Tier 1 Next.js swipe UI hitting a real txn queue. Web Push.
- C: CoreML emotion model integrated (use a pretrained FER or Hume on-device equivalent); voice emotion via Apple sound classifier.

**Day 1 — evening (4h)**
- All three: end-to-end happy path — txn → Tier 0 receipt, txn → Tier 1 swipe, txn → Tier 2 biometric. Bugs ok.

**Day 2 — morning (4h)**
- B: Specter-driven tier shifting; Opus explainer integration.
- C: Multi-party orchestration, randomized challenge phrase, coercion flag.
- A: Dashboard polish + activity log streaming.

**Day 2 — afternoon (4h)**
- All: dry-run demo 5×. Pre-enroll judge phones. Cut anything that doesn't survive 3 dry runs.

**Day 2 — evening:** sleep.

## 10. What Vouch Will Not Do (Guardrail on the Guardrail)

- Will not move money without rails approval — Tier 2 multi-party block is hard, not advisory.
- Will not store biometric data off-device — Face/voice templates never leave the Secure Enclave; only the binary pass/fail and emotion flags hit the server.
- Will not auto-pay an unknown counterparty over £5k regardless of risk score.
- Will not adapt thresholds without an audit trail — every threshold change is a signed config event.
- Will not silently override a coerced flag — a coerced attestation always blocks, even with sufficient other approvals.

## 11. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| iOS provisioning blows up day-of | TestFlight links pre-distributed to judges + a web-fallback WebAuthn flow stays warm. |
| Specter rate-limits during demo | Pre-cache the 3 demo recipients' Specter payloads, with a "live API" toggle for the judges who care. |
| Voice emotion model misfires on the duress demo | Tune threshold against the presenter's voice in dry runs; have a "force coerced" debug button as last-resort theatre — but only as fallback, the live one is the goal. |
| Stripe/Plaid sandbox flakes | Local mock ledger with identical interface; demo can fall through. |
| 90-second pacing slips | Cut the Tier 0 cold-open down to 5s if needed; the duress moment is the only sacred segment. |

---

*Built in Cursor. Runs on Cursor SDK. Reads Specter. Asks for a vouch.*
