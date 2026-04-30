# Vouch — Design

This document captures the design language behind Vouch: how the three-tier guardrail surfaces visually, the tokens that hold it together, and the interaction model on each tier. It is the reference the team works from while building, and the lens judges should view the demo through.

The product is the escalation ladder. Every design choice — colour, typography, motion, latency — is in service of making *which tier you are in* unmistakable within the first 200ms of looking at a screen.

---

## 1. Design principles

**1. The tier is the brand.** A user should know, at a glance and without reading copy, whether they are looking at a Tier 0 receipt, a Tier 1 swipe, or a Tier 2 vouch. We earn that recognition with colour temperature, typographic weight, and motion energy — not with labels.

**2. Calm at the bottom, urgent at the top.** Tier 0 is monochrome and silent. Tier 1 is warm amber, swipeable, mid-energy. Tier 2 is hot — red pulses, dark ink, oxygen-deprived backgrounds. The intensity of the UI matches the consequence of the action.

**3. Money looks expensive.** Amounts are set in a serif at display sizes. Everything around them — labels, metadata, system chrome — is monospaced and small. The only thing on screen with weight is the number you are about to move.

**4. Show the reasoning, don't bury it.** Every tier surfaces the *why*: a one-line LLM explainer on Tier 1, a Specter mini-card alongside, a randomized challenge phrase on Tier 2. The agent is not a black box; trust comes from legibility.

**5. The biometric flow is theatre on purpose.** Tier 2 is rare and high-stakes. We treat it like a security ritual — Dynamic Island pulse, Face ID gate, randomized challenge phrase, on-device emotion panel. The drama is the trust signal.

---

## 2. Visual language

### Bloom gradient

The signature surface is a warm-to-black diagonal gradient — orange in the top-right corner, deepening through burnt sienna and warm black to pure black in the bottom-left. It reads as a single light source falling off into a dark room, which sets the emotional register: warm enough to be human, dark enough to be serious.

```
bloomStart       #FF6A1A   top-right corner, warm orange
bloomMid         #8A2A05   burnt sienna mid-tone
bloomWarmBlack   #1A0A04   warm shadow
bloomBlack       #050505   deep field
bloomEdge        #000000   bottom-left, pure void
```

Stops are placed at `0 / 0.18 / 0.45 / 0.75 / 1` along a top-right → bottom-left axis with an 18% darken overlay on top to keep contrast tight against light cards. Defined once in `mobile/src/components/BloomGradient.tsx` and used as the root surface on `/approve` and `/vouch`.

### Cards (the daylight surface)

Cards float on the bloom. They are an off-white paper tone (`cardFill #FFFDF8`) with a warm bone stroke (`cardStroke #E8E2D6`). Ink inside cards is near-black (`cardInkPrimary #0A0A0A`) for the amount, warm taupe (`cardInkSecondary #6B5C45`) for vendor metadata, and a muted clay (`cardInkMuted #9A8E78`) for tertiary captions. The Specter mini-card inverts this — black inset on a card, mono type, white ink — to read as "data the agent is showing you" rather than primary content.

### Tier accent colours

Each tier has a single accent colour that drives badges, dots, swipe-direction tints, and the Dynamic Island pill:

```
tier0    #5A5A5A    monochrome — silent, done, not worth your attention
tier1    #FF8A2E    warm amber — ask lightly, swipe quickly
tier2    #FF3B30    pulse red — stop, attest, vouch
```

The amber and red are distinct enough to be separable in peripheral vision. Tier 0 deliberately has *no* hue — it is grey because it is invisible by design.

### Ink hierarchy

On the bloom (dark) surfaces, ink runs:
- `inkPrimary #FFFFFF` for the amount and primary content
- `inkMono #C9B89A` for warm-toned monospaced captions ("VOUCH REQUIRED")
- `inkMuted #5A5A5A` for tertiary chrome

On cards (light) surfaces, the equivalent ladder is `cardInkPrimary → cardInkSecondary → cardInkMuted`. The two systems are intentional inverses so the same component can sit on either surface and feel native.

---

## 3. Typography

We use exactly two families, paired:

- **Serif** (`Georgia` on iOS, `serif` fallback on Android) for amounts, the Tier 2 challenge phrase, and the "why this is being asked" explainer.
- **Mono** (`Menlo` on iOS, `monospace` on Android) for everything else: captions, vendor names, system chrome, Dynamic Island titles.

The split is load-bearing. Serif means *human, considered, the thing you decide on*. Mono means *machine, telemetry, the context the agent provides*. A Tier 1 card is roughly 80% mono (vendor metadata, Specter signals, timestamps) wrapped around 20% serif (the amount, the explainer). Your eye lands on the serif first.

```
amountHero           serif 64 / -1 tracking      — Tier 2 amount
amountList           serif 36 / -0.5 tracking    — ledger row, Tier 1 card
explainer            serif italic 14 / 20 lh     — "why this is being asked"
challengePhrase      serif 28 / 36 lh            — randomized Tier 2 phrase
body                 mono 13 / 0.2 tracking      — vendor metadata, body copy
caption              mono 11 / 1.0 tracking UC   — labels, badges
islandTitle          mono 12 / 1.0 tracking UC   — Dynamic Island pill
```

Caption-class type is always uppercase with wide letter-spacing — it reads as a system label, not as content. No font-size between 14 and 28: the gap forces every screen to commit to either *number* or *label*, never an in-between voice.

---

## 4. Motion

Motion energy scales with tier consequence. Defined centrally in `mobile/src/tokens/motion.ts`:

```
pulse           1400ms loop, opacity 0.4↔1.0, scale 0.92↔1.0   — Tier 2 readiness, Dynamic Island
cardSpring      damping 18, stiffness 200, mass 0.6            — Tier 1 swipe return
swipeRotate     ±8° max at edges
swipeThreshold  28% of card width to commit
islandSpring    damping 18, stiffness 200, mass 0.7            — Dynamic Island expand
```

**Tier 0** has no motion. Receipts drop into the dashboard with a fade — no spring, no pulse. The absence of motion is the design.

**Tier 1** is springy and forgiving. Cards rotate up to 8° as you drag and snap back with a soft spring (mass 0.6) if you release before 28% of card width. Commit feels confident; cancel feels weightless. Up-swipe (escalate to Tier 2) and down-swipe (more info) use the same spring with different exit vectors.

**Tier 2** pulses. The Dynamic Island banner pulses red on a 1.4s cycle until acknowledged — slow enough to feel deliberate, fast enough to feel alive. The expand into Face ID uses a slightly heavier spring (mass 0.7) than the Tier 1 cards, so the transition feels physically more committed.

---

## 5. Tier-by-tier interaction

### Tier 0 — silent receipt

No screen. The receipt appears in the dashboard ledger as a row, with a tier-0 grey dot, vendor name in mono, amount in serif, and a one-click "this was wrong" reverse-link visible on hover. The Slack ping fires in parallel with the same content. Latency target end-to-end: under 2 seconds. The whole point is that the user does not look at this — they discover it later, in aggregate.

### Tier 1 — Tinder swipe

A card stack on the bloom surface. Each card has:
- Vendor logo + name (top, mono)
- Amount in serif `amountList` (centre)
- One-line italic serif explainer from Opus 4.7 ("Recurring AWS bill, in band, first-of-month")
- Specter mini-card inset (funding stage, headcount delta, last news flag) — black-on-card to read as injected telemetry
- Historical context strip (last 3 payments to this vendor)

Right swipe approves. Left rejects. Up escalates to Tier 2 ("I want a stronger signal"). Down asks the agent for more info ("explain again, more depth"). The four-direction model is deliberate: it lets the approver express intent beyond yes/no without leaving the swipe gesture.

Cap: 20 cards/day per approver, with auto-escalate-on-overflow to prevent rubber-stamping fatigue.

### Tier 2 — biometric vouch

The escalation surfaces first in the **iOS Dynamic Island** as a Live Activity: a compact red pill with a mono caption ("VOUCH REQUIRED · £62,000"). It pulses on the 1.4s motion cycle until tapped. Expanding launches the full Tier 2 screen.

The screen flow:

1. **Bloom surface, amountHero serif** — the amount fills the upper third in 64pt Georgia. There is nothing else above the fold.
2. **Face ID gate** via `react-native-biometrics`. Apple Secure Enclave on-device — the biometric template never leaves the device.
3. **Challenge phrase**, 28pt serif, randomized per attempt, containing the amount and recipient name and date ("authorize sixty-two thousand to Acme on April thirty"). This is the anti-replay primitive — pre-recorded video cannot match a phrase generated 0.5s ago.
4. **Video capture** via `react-native-vision-camera`, 5–8 seconds, recording the approver reading the phrase. A live waveform sits below the camera preview in mono accent amber.
5. **Result panel.** Server returns `{face_emotion, voice_emotion, transcript, transcript_match, cadence, coerced}` from the fused classifier. The on-device panel renders a small grid: face emotion (one of 7 classes), voice emotion, cadence band, transcript-match boolean. If `coerced: true` for any approver, the entire txn flips to the red `tier2` accent and shows BLOCKED in mono caption.

Multi-party: 2–4 approvers (configurable; demo uses 3) must each complete this flow within a 30-minute window. Any single coerced flag blocks even with sufficient other approvals.

Latency target: under 90 seconds per approver.

---

## 6. Dashboard

The Django + HTMX dashboard at `/d/` is a control room, not a CRM. Layout:

- **Top strip:** today's Tier 0 counter (large serif), Tier 1 in-flight, Tier 2 in-flight. The Tier 0 number is the proof that the agent is doing real work — it is the live stat we point at on stage.
- **Centre:** SSE-driven receipt feed. Each row is a single line — timestamp (mono), tier dot, vendor (mono), amount (serif `amountList`), one-click reverse-link for Tier 0 within the 60-minute window.
- **Right rail:** approver attention queue and the 30-minute Tier 2 multi-party countdown.
- **Bottom:** threshold config, audit log of every signed threshold change.

The dashboard uses the same colour system as mobile but biased toward the dark-on-light card surfaces — it is meant to be a daylight tool, used at a desk, by an operator.

---

## 7. The 90-second demo, viewed as a design arc

The demo is paced as three tonal beats: **silence → swipe → vouch**, then a fourth beat that re-runs the third under duress and breaks it on purpose.

| Beat | Tonal register | Design moment |
|---|---|---|
| 0–10s — silence | Monochrome dashboard, ticking Tier 0 counter | Negative space proves the agent works. No UI is the UI. |
| 10–25s — swipe | Warm amber card on bloom, single right-swipe | Shows trust calibrated *down* — this could have been Tier 0, but the new vendor pushed it up one notch. |
| 25–70s — vouch | Pulsing red Dynamic Island, Face ID, challenge phrase, 3 approvers | The full ritual. This is the section that earns the Track 01 + 02 hybrid claim — the intelligence is what made this a Tier 2, not a £62k threshold alone. |
| 70–90s — duress | Same screen, same amount, same Face ID pass | The coerced flag fires red. Identical surface, opposite outcome. The design holds because the tier accent flips and nothing else has to. |

The duress beat works as a design payoff because the prior 70 seconds have trained the judge's eye to read tier colour first. When red appears in the post-attestation result panel, the meaning is preloaded.

---

## 8. What's deferred

These are designed but not yet built; called out so judges and contributors know what is mock vs real:

- **Native modules.** Face ID prompt, vision-camera capture, and the ActivityKit Live Activity binary are wired in at Expo prebuild time, not in the current Expo Go JS-only build. Demo phones run the prebuilt binary.
- **Coercion classifier service.** The Celery task contract (`{face_emotion, voice_emotion, transcript, transcript_match, cadence, coerced}`) is fixed; the model wiring (`opencv/facial_expression_recognition` + `FunAudioLLM/SenseVoiceSmall`) lands in Hour 4 of the build plan.
- **Specter mini-card.** Token slots and layout exist (`cardSpecterInset`); the live API hits ride on the Hour 3 integration, with three demo recipients pre-cached as a fallback.
- **Dashboard SSE feed.** HTMX scaffolding is in place; the live receipt stream is the Hour 3 deliverable on Member A's track.

---

## 9. Source of truth

All design tokens live in `mobile/src/tokens/`:

```
mobile/src/tokens/colors.ts        — bloom, card, ink, tier accents
mobile/src/tokens/typography.ts    — serif/mono pair, named scales
mobile/src/tokens/motion.ts        — pulse, springs, swipe thresholds
```

Components in `mobile/src/components/` (`BloomGradient`, `DynamicIslandBanner`, `LogoAvatar`, `PulseDot`, `TinderCard`, `TxnRow`) consume tokens directly — no hard-coded hex, no inline durations. The Django dashboard mirrors the same token names in its Tailwind config so colour and type stay in lockstep across mobile and web.

If you change a token, you change the product. That is the contract.
