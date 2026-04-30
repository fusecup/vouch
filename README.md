# Vouch

> *A tiered guardrail layer for an agent that moves money — auto-approving the boring, swiping the borderline, and biometrically vouching for the dangerous.*

**Cursor × Briefcase · Halkin Offices · London 2026**
**Tracks:** Hybrid — primary **Track 01 (Money Movement)**, with **Track 02 (Financial Intelligence)** as the gating mechanism.

---

## Why this exists

Finance agents that move money are now technically capable of running payroll, paying invoices, and sweeping cash. The blocker is no longer capability — it is **trust calibration**. Today's options are binary: either the agent has authority and one fraud incident bankrupts you, or every transaction needs a human and the agent is theatre.

Vouch makes the trust gradient explicit. The agent acts alone where it should, asks lightly where it should ask lightly, and demands a wall of human attestation where the money is large enough to matter.

The intelligence (categorisation, fraud signal, counterparty quality) is not a side feature — it is the **gate** that decides which tier any given transaction enters.

---

## The three-tier guardrail

| Tier | Trigger | UI | Latency | Failure mode |
|---|---|---|---|---|
| **0 — Silent auto-approve** | Known counterparty, in-band amount, healthy Specter score, no anomaly | None — receipt drops in dashboard + Slack with reverse-link | < 2s | Reversible-by-default for 60 min |
| **1 — Tinder swipe** | Mid-band amount, mild anomaly, first-time vendor with acceptable Specter | Mobile card stack with vendor logo, amount, 1-line LLM "why", Specter mini-card | < 5s of approver attention | Approval fatigue → cap 20/day, auto-escalate |
| **2 — Biometric vouch** | High-band, strong anomaly, poor Specter, or unknown recipient over £25k | iOS Dynamic Island Live Activity → Face ID → 5–8s video selfie reading randomized challenge phrase → multi-party (2–4 approvers within 30 min) | < 90s per approver | Coercion classifier blocks duress approvals |

**Tier 2 in detail.** Face ID via `react-native-biometrics` (template stays in Apple's Secure Enclave — never leaves device). Video recorded with `react-native-vision-camera`. The clip goes to a Django Celery task running:

- `opencv/facial_expression_recognition` — 7-class facial emotion at 4 fps
- `FunAudioLLM/SenseVoiceSmall` — single forward pass returns transcript + voice emotion + acoustic event tags
- Distress fusion: face emotion + voice emotion + cadence + transcript-match against the challenge phrase. Any single high-confidence coerced signal blocks the txn — even if Face ID passed and other approvers cleared.

---

## Architecture

```
                    ┌─────────────────────────┐
   Txn intent ─────▶│  Risk scorer (Haiku 4.5  │
   (Plaid webhook)  │  + Specter + history)   │
                    └────────────┬────────────┘
                                 │ score + reasons
                    ┌────────────▼────────────┐
                    │   Tier router            │
                    │   (deterministic rules   │
                    │    + LLM tie-breaker)    │
                    └─┬──────────┬───────────┬─┘
                      │          │           │
                  Tier 0      Tier 1      Tier 2
                  execute     swipe       biometric vouch
                      │          │           │
                      └──────────┴───────────┘
                                 │
                          Rails executor ──▶ ledger + receipt
```

| Layer | Stack |
|---|---|
| Money rails | Plaid sandbox (transactions + auth) |
| Agent + risk scoring | Django + Celery, Anthropic SDK (Haiku 4.5 scorer / Opus 4.7 explainer), Specter API |
| Coercion classifier | Python (`transformers` + `torch`), exposed as a Celery task |
| Mobile (Tier 1 + Tier 2 + Dynamic Island) | React Native via Expo Router + dev client; Expo Notifications + SMS fallback |
| Dashboard / activity log | Django + HTMX with SSE for live txn stream |

**Two LLM roles, deliberately split.** Haiku 4.5 is the cheap, fast scorer that runs on every txn. Opus 4.7 is only called on Tier 1+ for the human-facing explanation and post-hoc audit narrative.

---

## Quick start

You need Docker Desktop, Node.js with pnpm, and (for the mobile side) an iPhone with Expo Go or Xcode for the simulator.

### 1. Backend (Django + Postgres + Redis + Celery)

```bash
# from repo root
cp .env.example .env

# build & boot the full stack (db, redis, backend, celery, flower, kanchi, mail, tailwind)
docker compose build backend
docker compose up -d

# migrate & seed
docker exec -it vouch-backend-1 python manage.py migrate
docker exec -it vouch-backend-1 python manage.py loaddata vouch/fixtures/allauth.json
docker exec -it vouch-backend-1 python manage.py createsuperuser
```

Once up:

| Service | URL |
|---|---|
| Dashboard | http://127.0.0.1:8000 |
| Admin | http://127.0.0.1:8000/admin/ |
| Auth (login/signup) | http://127.0.0.1:8000/a/login/ |
| Celery Flower | http://127.0.0.1:8765 |
| Kanchi (Celery UI) | http://127.0.0.1:3000 |
| MailCatcher | http://127.0.0.1:1080 |

Authentication is `django-allauth` with a Google social provider already wired (`/a/`). To enable Google sign-in, add a `SocialApp` row in the admin under *Social Accounts → Social applications* with your Google OAuth client ID/secret. Email + password works out of the box.

### 2. Mobile app (Expo / React Native)

```bash
cd mobile
pnpm install
pnpm start          # Metro bundler — scan QR with Expo Go on iPhone
pnpm ios            # or boot the iOS simulator directly
```

The app currently runs as a JS-only Expo Go project against mock data in `src/data/mockTransactions.ts`. Native modules (`react-native-biometrics`, `react-native-vision-camera`, ActivityKit Live Activity) are wired in at prebuild time once the demo path is signed off — judges will see the fully-prebuilt binary on the demo phones.

**Routes:**
- `/` — transaction ledger (list)
- `/approve?id=…` — Tier 1 Tinder swipe (right = approve, left = reject, up = escalate)
- `/vouch?id=…` — Tier 2 biometric vouch with Dynamic Island banner

**Demo killer.** On `/vouch`, toggle the `duress` switch at the bottom before reaching the result stage. Same Face ID pass, same recording — the coercion classifier flags the cadence and blocks the txn. That is the 90-second pitch.

### 3. Required secrets in `.env`

The `.env.example` covers infra. For the demo path, also set:

```bash
ANTHROPIC_API_KEY=...    # Haiku 4.5 scorer + Opus 4.7 explainer
SPECTER_API_KEY=...      # counterparty quality oracle
PLAID_CLIENT_ID=...      # sandbox is fine
PLAID_SECRET=...
GOOGLE_OAUTH_CLIENT_ID=...     # optional, for /a/ Google sign-in
GOOGLE_OAUTH_CLIENT_SECRET=...
```

---

## The 90-second demo

| t | What the judge sees |
|---|---|
| 0–10s | Dashboard live: 12 invoices arrived in the last hour. 9 already auto-paid (Tier 0). Receipts streaming. |
| 10–25s | A £4,200 invoice to a new vendor pops on the presenter's phone as a Tinder card. Specter mini-card shows the vendor is a real seed-stage co. Swipe right. Paid. |
| 25–45s | A £62,000 transfer triggers. Tier 2 escalation fires to **the actual judges' phones** (pre-enrolled). Face ID prompt → randomized challenge phrase ("authorize sixty-two thousand to Acme on April thirty"). Voice + face captured. |
| 45–70s | On-device emotion panel renders live: neutral / confident. Three approvers complete. Money moves. |
| 70–90s | Re-run the same £62k txn, but this time the presenter reads the phrase under fake duress (rushed cadence). Coerced flag fires red, txn blocks. *That* is the moment. |

---

## How this maps to the rubric

| Criterion | Pts | How Vouch lands it |
|---|---|---|
| Concrete workflow value | 2 | Replaces the "everyone CC'd on every payment approval" Slack chaos with calibrated automation. The Tier 0 stat is live on stage. |
| Track fit (hybrid) | 2 | Tier 0/2 = money movement; Tier 0→1→2 routing = financial intelligence. Intelligence isn't a side feature — it is the gate. |
| Human-in-the-loop | 1 | Three tiers with explicit thresholds, confidence gates (Specter + LLM score), multi-party Tier 2, coercion as a *third* axis beyond authentication. |
| Technical execution | 1 | Real rails (Plaid), edge biometric capture (RN), Django agent with Specter + dual-model LLM. Three integrations that all work in the demo. |
| Demo clarity | 1 | The duress-replay moment in the last 20s is the entire pitch in one beat. |
| **Best use of Cursor** | +1 | Built end-to-end in Cursor IDE with Specter MCP wired in for live company-data exploration; Cursor agent runs the eval suite that calibrates risk thresholds against historical txns. |
| **Best use of Specter** | +1 | Counterparty quality score *changes the tier threshold* — Specter is load-bearing, not decorative. |
| **Best use of LLM models** | +1 | Two-model split: Haiku for per-txn scoring (cost), Opus for the human-facing explanation (quality). Coercion classifier is a separate small model. |

---

## What Vouch will not do (the guardrail on the guardrail)

- Will not move money without rails approval — Tier 2 multi-party block is hard, not advisory.
- Will not store the Face ID template off-device — it stays in the Secure Enclave. Challenge-phrase video/audio is sent to the server for emotion analysis with a hard 24h retention TTL.
- Will not auto-pay an unknown counterparty over £5k regardless of risk score.
- Will not adapt thresholds without an audit trail — every threshold change is a signed config event.
- Will not silently override a coerced flag — a coerced attestation always blocks, even with sufficient other approvals.

---

## Repo layout

```
vouch/
├── PRD.md                      # The product spec — read this for the long form
├── docker-compose.yaml         # Multi-service stack (Postgres, Redis, Django, Celery, Flower, Kanchi, MailCatcher, Tailwind)
├── Makefile                    # make up / make migrate / make shell / make zsh
├── src/
│   ├── manage.py
│   └── vouch/
│       ├── settings.py
│       ├── urls.py             # /a/ allauth, /admin/, /d/ dashboard
│       ├── celery.py
│       └── apps/
│           ├── accounts/       # custom User, allauth adapter
│           ├── common/         # admin_site
│           └── fc_uikit/       # design system + welcome view
└── mobile/                     # Expo Router RN app — Tier 1 swipe + Tier 2 vouch
    ├── app/
    │   ├── index.tsx           # ledger
    │   ├── approve.tsx         # Tier 1 swipe
    │   └── vouch.tsx           # Tier 2 biometric (with duress toggle)
    └── src/
        ├── components/
        ├── data/mockTransactions.ts
        └── tokens/             # design tokens (single source of truth)
```

---

## Operational reference

<details>
<summary><b>Docker cheatsheet</b></summary>

```bash
docker compose up                           # boot with logs
docker compose up -d                        # boot detached
docker compose down                         # stop
docker exec -it vouch-backend-1 zsh         # shell into backend
docker exec -it vouch-backend-1 shell       # Django shell_plus
docker exec -it vouch-db-1 psql -U vouch    # postgres shell
docker compose build --no-cache backend     # rebuild backend image
docker compose up -d --no-deps --build celery-flower celery-beat celery-worker backend
```

Compose profiles in `.env` (`COMPOSE_PROFILES`) control which services boot. Default boots everything: `postgres,redis,backend,celery,flower,kanchi,mail,tailwind,jupyter`. Drop profiles you do not need to save resources.

</details>

<details>
<summary><b>Make targets</b></summary>

```bash
make up                  # docker compose up
make migrate             # python manage.py migrate
make migrations          # python manage.py makemigrations
make shell               # Django shell_plus
make zsh                 # zsh into backend container
make ruff                # lint + format Python
make attach              # attach to backend container (for ipdb)
```

</details>

<details>
<summary><b>UV (Python deps) inside the backend container</b></summary>

```bash
uv sync                          # sync deps, update lock
uv sync --frozen                 # sync without touching lock
uv add -U <package>              # add a package
uv tree --outdated --depth=1     # list outdated
```

For IDE imports, you can also `cd src && uv sync --frozen --dev` on the host.

</details>

<details>
<summary><b>Tests</b></summary>

```bash
docker exec -it vouch-backend-1 ruff check
docker exec -it vouch-backend-1 basedpyright
docker exec -it vouch-backend-1 coverage run manage.py test
docker exec -it vouch-backend-1 coverage report --skip-covered --show-missing --omit="*/venv/*"
```

</details>

<details>
<summary><b>Spec-driven development (Spec-Kit)</b></summary>

This project uses [Spec-Kit](https://github.com/github/spec-kit). All commands available in Cursor via `/speckit.*`:

```bash
/speckit.specify <feature>    # create spec.md
/speckit.plan                 # generate plan.md, research.md, data-model.md, contracts/
/speckit.tasks                # break plan into ordered tasks.md
/speckit.analyze              # cross-artifact consistency check
/speckit.implement            # execute tasks.md in dependency order
/speckit.checklist            # quality checklists (UX, security, testing)
/speckit.constitution         # view/update project constitution
```

Spec artifacts live in `.specify/specs/<number>-<feature>/`. The constitution at `.specify/memory/constitution.md` is the source of truth all specs must align with.

</details>

<details>
<summary><b>Optional: GPG-signed commits</b></summary>

This repo expects signed commits in production. For hackathon work this is optional — see [GPG Tools](https://gpgtools.org/) and configure per-repo:

```ini
# .git/config
[user]
    name = <FULL NAME>
    email = <EMAIL>
    signingkey = <GPG KEY — last 16 digits>
```

</details>

---

*Built in Cursor. Moves money on Plaid. Reads Specter. Asks for a vouch.*
