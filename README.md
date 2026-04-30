# Vouch

**An agent that moves money. With a face on it.**

*Cursor × Briefcase · Halkin Offices · London 2026*

---

Three tiers. One agent.

Small money moves itself.
Medium money asks for a swipe.
Big money asks for your face.

Coerced money never moves.

---

## The problem

Finance agents can move money. Companies will not let them.

The reason is not capability. It is trust. Hand the agent the keys and one bad invoice ends the company. Gate every payment with a human and the agent is theatre — slower than the bookkeeper it replaced.

The unsolved question is not *can the agent pay this*. It is *how big is too big to act alone*.

Today, every system answers that question the same way for a £40 SaaS bill and a £62,000 wire. We answer it three different ways.

---

## The solution

A guardrail layer between the agent and the rails. Every payment is scored, routed into a tier, and handled with a UI matched to its consequence.

The product is the ladder.

### Tier 1 — Silent

Known vendor. In-band amount. Healthy counterparty signal.

The agent pays. A receipt drops in the dashboard. One click reverses it for sixty minutes. No one looks at it.

*Latency: under two seconds.*

### Tier 2 — Swipe

A new vendor. A mid-band amount. A mild anomaly.

A card lands on the approver's phone. Vendor logo. Amount. One line on why it's being asked. Specter card with funding stage and recent news. Right swipe pays. Left rejects. Up escalates. Down asks again.

*Latency: five seconds of attention.*

### Tier 3 — Vouch

A wire to someone the agent has never seen. Or sixty thousand pounds.

The Dynamic Island pulses red. Tap it. Face ID runs. A challenge phrase appears, generated half a second ago, naming the amount and the recipient. The phone records you reading it. Three approvers do this. The video runs through a coercion classifier. Anything off — rushed cadence, fearful face, a phrase that doesn't match — blocks the payment. Forever. Even if Face ID passed. Even if the other approvers vouched cleanly.

*Latency: ninety seconds per approver.*

---

## How it works

Every transaction the agent intends to make goes through three steps.

**Score.** Claude Haiku 4.5 reads the transaction, the recipient's Specter profile, and the company's history. It returns a risk score, three reasons, and a recommended tier. Haiku because it runs on every payment. It has to be cheap.

**Route.** Deterministic rules first — amount bands, known counterparty, Specter grade. The LLM score is a tie-breaker on the boundaries. Every routing decision is logged with its reason.

**Handle.** Tier 1 hits Plaid. Tier 2 hits the approver's phone. Tier 3 hits everyone enrolled, in parallel, and waits.

A second model — Claude Opus 4.7 — is called only on Tier 2 and Tier 3. It writes the one-line "why this is being asked" and the post-hoc audit narrative. Two models, deliberately split. Haiku handles volume. Opus handles prose.

```
Txn intent ──▶ Risk scorer (Haiku 4.5) ──▶ Tier router ──┬──▶ Tier 1 ─▶ pay
                       ▲                                  ├──▶ Tier 2 ─▶ swipe
                  Specter API                             └──▶ Tier 3 ─▶ vouch
```

### Tier 3, in detail

This is the part that's new.

1. iOS Dynamic Island pulses red. *VOUCH REQUIRED · £62,000.*
2. Tap to expand.
3. Face ID. `expo-local-authentication` on native, WebAuthn on web. The biometric template never leaves the Secure Enclave.
4. A challenge phrase appears. Server-generated at the moment of capture: *"authorize sixty-two thousand to Acme on April thirty."* No pre-recorded video can match a phrase that's half a second old.
5. Five to eight seconds of video selfie reading the phrase aloud.
6. The clip runs through two models in parallel — `opencv/facial_expression_recognition` for face emotion at 4 fps, `FunAudioLLM/SenseVoiceSmall` for transcript and voice emotion in one pass.
7. Fusion: face + voice + cadence + transcript match. One coerced signal blocks the payment.

A coerced flag cannot be overridden. Not by the founder. Not by ten clean vouches. That is the contract.

---

## What it will not do

This is the guardrail on the guardrail.

- It will not move money without rails approval.
- It will not store the Face ID template off-device.
- It will not auto-pay an unknown counterparty over £5,000.
- It will not change a threshold without a signed audit event.
- It will not override a coerced flag.

These are hard rules. Not advisory.

---

## How we built it

**In Cursor, end to end.** The agent app, the Django dashboard, the Expo mobile binary. One IDE.

**With Specter MCP wired in.** Live company data exploration during development. The same API hits production at runtime.

**With two Anthropic models.** Haiku 4.5 for per-transaction scoring. Opus 4.7 for explanation. A separate small model for coercion. Three jobs, three model classes — each chosen on cost and quality, not because they are there.

Specter is load-bearing. A strong counterparty drops a transaction one tier. An empty Specter profile over £5,000 jumps it to Tier 3 — regardless of amount. The intelligence is the gate.

---

## The 90-second demo

| Time | What you see |
|---|---|
| 0–10s | Dashboard live. Twelve invoices arrived this hour. Nine paid themselves. |
| 10–25s | A £4,200 card pops on the presenter's phone. Specter shows the vendor is real. Swipe right. Paid. |
| 25–45s | A £62,000 wire fires. Three judges' phones pulse red. Face ID. Challenge phrase. Voice and face captured. |
| 45–70s | Emotion panel renders. Neutral. Cadence ok. Three approvers complete. Money moves. |
| 70–90s | Same wire. Presenter reads the phrase under fake duress — rushed, hurried. Coerced flag fires. The payment blocks. |

That last twenty seconds is the pitch.

---

## Run it locally

You need Docker, Node with pnpm, and an iPhone or simulator.

### Backend

```bash
cp .env.example .env
docker compose build backend
docker compose up -d
docker exec -it vouch-backend-1 python manage.py migrate
docker exec -it vouch-backend-1 python manage.py loaddata vouch/fixtures/allauth.json
docker exec -it vouch-backend-1 python manage.py createsuperuser
```

| Service | URL |
|---|---|
| Dashboard | http://127.0.0.1:8000 |
| Auth | http://127.0.0.1:8000/a/login/ |
| Admin | http://127.0.0.1:8000/admin/ |
| Celery Flower | http://127.0.0.1:8765 |
| Kanchi | http://127.0.0.1:3000 |
| MailCatcher | http://127.0.0.1:1080 |

### Mobile

```bash
cd mobile
pnpm install
pnpm start          # scan QR with Expo Go
pnpm ios            # or boot the simulator
```

Routes:
- `/` — ledger
- `/approve?id=…` — Tier 2 swipe
- `/vouch?id=…` — Tier 3 vouch (toggle `duress` to see the block)

### Secrets

`.env.example` covers infra. The demo also needs:

```bash
ANTHROPIC_API_KEY=...
SPECTER_API_KEY=...
PLAID_CLIENT_ID=...
PLAID_SECRET=...
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
```

---

## Repo

```
vouch/
├── PRD.md            long-form spec
├── design.md         visual language, tokens, motion
├── docker-compose.yaml
├── src/              Django agent + dashboard
└── mobile/           Expo Router app — swipe + vouch
```

For the visual language, see [design.md](./design.md). For the long-form product spec, see [PRD.md](./PRD.md).

---

## Operational reference

<details>
<summary><b>Docker</b></summary>

```bash
docker compose up -d
docker compose down
docker exec -it vouch-backend-1 zsh
docker exec -it vouch-backend-1 shell
docker exec -it vouch-db-1 psql -U vouch
docker compose build --no-cache backend
```

`COMPOSE_PROFILES` in `.env` controls which services boot. Default boots everything.

</details>

<details>
<summary><b>Make</b></summary>

```bash
make up
make migrate
make migrations
make shell
make zsh
make ruff
```

</details>

<details>
<summary><b>UV (inside the backend container)</b></summary>

```bash
uv sync
uv sync --frozen
uv add -U <package>
uv tree --outdated --depth=1
```

</details>

<details>
<summary><b>Tests</b></summary>

```bash
docker exec -it vouch-backend-1 ruff check
docker exec -it vouch-backend-1 basedpyright
docker exec -it vouch-backend-1 coverage run manage.py test
```

</details>

<details>
<summary><b>Spec-Kit</b></summary>

In Cursor:

```
/speckit.specify <feature>
/speckit.plan
/speckit.tasks
/speckit.implement
```

Specs live in `.specify/specs/`. Constitution at `.specify/memory/constitution.md`.

</details>

---

*Built in Cursor. Moves money on Plaid. Reads Specter. Asks for a vouch.*
