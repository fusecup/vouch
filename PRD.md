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
- **UI:** React Native app (lives in the same binary as Tier 1).
  1. **Face ID** challenge via `react-native-biometrics` (Apple Secure Enclave on-device — template never leaves the device).
  2. **5–8s video selfie** via `react-native-vision-camera`, reading a randomized challenge phrase containing the amount and recipient name (anti-replay).
  3. **Facial + voice emotion** fused on the backend (Hume API or equivalent) on the captured clip — neutral / stressed / fearful / coerced. Sub-2s round-trip.
  4. Distress-signal heuristics (forced-cadence speech, micro-expression mismatch, speech-vs-text mismatch on the challenge phrase) flag the attestation as *coerced* even if Face ID passes.
- **Multi-party:** 2–4 approvers (configurable; demo uses 3) must each complete the biometric flow within a 30-min window. Coerced flags from any one approver block the txn.
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
| Money rails | Plaid sandbox (transactions + auth) | Member A |
| Agent + risk scoring | Django (existing base) + Celery, Anthropic SDK for Haiku/Opus, Specter API | Member B |
| Mobile app (Tier 1 + Tier 2) | React Native via Expo + dev client (`react-native-biometrics`, `react-native-vision-camera`); push via Expo Notifications + SMS fallback | Member C |
| Dashboard / activity log | Django + HTMX (Python, already in base); SSE for live txn stream | Member A (shared) |

The existing repo is a Django/Docker/Postgres/Celery base — agent, dashboard, and ledger live there. The React Native app is a sibling project; talks to Django over signed REST + Expo push tokens.

## 6. Specter Integration (bonus signal)

Specter is the **counterparty risk oracle**. Whenever a transaction names a recipient entity:
- Resolve recipient → Specter company ID (fuzzy match on name + domain + bank details).
- Pull: funding stage, headcount trend (3-month delta), recent news flags, founding date, signals matrix.
- Convert into a 0–100 **counterparty quality score**.
- Score directly shifts the tier threshold: a Specter-strong recipient drops one tier band; a Specter-empty recipient over £5k jumps to Tier 2 regardless of amount.
- Surface the Specter mini-card inside Tier 1 swipe and Tier 2 biometric review screens.

Specter API hits from the Django agent in production; Specter MCP wired into Cursor IDE for live company-data exploration during development and threshold tuning.

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
| Technical execution | 1 | Real rails via Plaid (Member A), edge biometric capture in React Native (Member C), Django agent with Specter + dual-model LLM (Member B). Three integrations that all work in the demo. |
| Demo clarity | 1 | The duress-replay moment in the last 20s is the entire pitch in one beat. |
| **Best use of Cursor** | +1 | Built end-to-end in Cursor IDE with Specter MCP wired in for live company-data exploration; Cursor agent runs the eval suite that calibrates risk thresholds against historical txns. |
| **Best use of Specter** | +1 | Counterparty quality score *changes the tier threshold* — Specter is load-bearing, not decorative. |
| **Best use of LLM models** | +1 | Two-model split: Haiku for per-txn scoring (cost), Opus for the human-facing explanation (quality). Coercion classifier is a separate small model. |

## 9. 6-Hour Build Plan

Brutal scope. Anything not on this list ships as a stub or doesn't ship.

**Hour 1 — scaffolding (parallel)**
- A: Plaid sandbox auth + 30 synthetic txns landing in Django via webhook.
- B: Django agent app, Anthropic SDK wired (Haiku 4.5), Specter API key + one working `/score` endpoint that returns a stub.
- C: Expo + dev client project, `react-native-biometrics` + `react-native-vision-camera` installed, Face ID prompt working on a physical phone.

**Hour 2 — happy path bones**
- A: Tier router (deterministic rules: amount + Specter score → tier 0/1/2) + ledger model + Plaid execution stub.
- B: Real risk scorer call to Haiku with txn JSON + Specter payload; returns score + reasons.
- C: Tier 1 swipe UI in RN — card stack of pending txns from Django, swipe right hits `/approve`.

**Hour 3 — Tier 2 capture + Specter live**
- A: Dashboard list view + SSE stream of receipts.
- B: Specter live integration — funding/headcount/news → counterparty quality score → tier shift logic.
- C: Tier 2 screen — Face ID gate, video capture of randomized challenge phrase, upload to Django.

**Hour 4 — emotion + multi-party**
- B: Hume (or chosen) emotion API call on uploaded clip; coercion fusion logic; Opus 4.7 explainer for Tier 1 cards.
- C: 3-approver orchestration — txn requires 3 vouches within 30 min; any coerced flag blocks.
- A: Dashboard polish — Tier 0 counter, live receipt feed.

**Hour 5 — end-to-end + demo wiring**
- All: full happy path runs three times: Tier 0 auto-pay, Tier 1 swipe, Tier 2 biometric multi-party. Pre-enroll the demo phones (presenter + 2 teammates as approvers). Pre-cache 3 demo recipients in Specter.

**Hour 6 — dry runs**
- All: run the 90s demo end-to-end 5×. Any step that fails twice gets cut or stubbed. Lock the duress-replay moment last — it's the only sacred segment.

## 10. What Vouch Will Not Do (Guardrail on the Guardrail)

- Will not move money without rails approval — Tier 2 multi-party block is hard, not advisory.
- Will not store the Face ID template off-device — it stays in the Secure Enclave. Challenge-phrase video/audio is sent to the server for emotion analysis with a hard 24h retention TTL.
- Will not auto-pay an unknown counterparty over £5k regardless of risk score.
- Will not adapt thresholds without an audit trail — every threshold change is a signed config event.
- Will not silently override a coerced flag — a coerced attestation always blocks, even with sufficient other approvals.

## 11. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Expo dev client / RN native module flakes day-of | Pre-build the binary via EAS the night before; install on all 3 demo phones in advance. |
| Specter rate-limits during demo | Pre-cache the 3 demo recipients' Specter payloads, with a "live API" toggle for the judges who care. |
| Emotion API misfires on the duress demo | Tune threshold against the presenter's voice in Hour 6 dry runs; keep a "force coerced" debug button as fallback theatre — but the live one is the goal. |
| Plaid sandbox flakes | Local mock ledger with identical interface; demo can fall through. |
| 90-second pacing slips | Cut the Tier 0 cold-open down to 5s if needed; the duress moment is the only sacred segment. |

---

*Built in Cursor. Moves money on Plaid. Reads Specter. Asks for a vouch.*
