# Vouch

> *A tiered guardrail layer for an agent that moves money — auto-approving the boring, swiping the borderline, and biometrically vouching for the dangerous.*

**Cursor × Briefcase · Halkin Offices · London 2026**

---

## The problem

Finance agents that move money are now technically capable of running payroll, paying invoices, refunding customers, and sweeping cash between accounts. The blocker is no longer capability — it is **trust calibration**.

Today's choices for any company shipping a finance agent are binary, and both are bad:

1. **Give the agent authority.** It works for weeks, then one fraudulent invoice or one hallucinated routing number bankrupts the company.
2. **Make every transaction need a human.** Approvals pile up in Slack, the founder rubber-stamps £50k transfers between calls, and the agent is theatre — slower than the bookkeeper it replaced.

The unsolved question is not *"can the agent move money?"* It is **"how big is too big to act alone, what counts as suspicious, and who can the agent trust?"** That question is not the same on a £40 SaaS bill, a £4,200 invoice to a new vendor, and a £62,000 wire to a counterparty the agent has never seen.

Today, every system answers it the same way. Vouch answers it three different ways, depending on what the agent is about to do.

---

## The proposed solution

Vouch is a guardrail layer that sits between a finance agent and the money rails. Every transaction the agent wants to make is scored, routed into one of three tiers, and handled with a UX matched to its consequence.

The product *is* the escalation ladder:

| Tier | What happens | Example |
|---|---|---|
| **Tier 1 — Silent auto-approve** | Agent acts alone. A receipt drops in the dashboard and Slack with a one-click "this was wrong" reverse-link. Reversible by default for 60 minutes. | Recurring £40 AWS bill, paid in 2 seconds, no human looks at it. |
| **Tier 2 — Tinder swipe** | A card pops on the designated approver's phone. Vendor logo, amount, one-line LLM "why this is being asked", Specter mini-card. Right swipe approves, left rejects, up escalates, down asks for more info. | First-time £4,200 vendor with healthy Specter signal — 5 seconds of attention, done. |
| **Tier 3 — Biometric vouch** | iOS Dynamic Island pulses red. Tap launches Face ID. Approver reads a randomized challenge phrase containing the amount and recipient on camera. 2–4 approvers must each pass, within 30 minutes. Coercion classifier blocks duress. | £62,000 wire to a never-seen counterparty — a security ritual, not a tap. |

Three things make this different from a normal approval queue:

- **The tier is decided by the agent's read of the transaction**, not by a hardcoded amount threshold. A poor counterparty signal at £5k can become Tier 3; a strong one at £15k can stay Tier 1.
- **Tier 3 has a third axis beyond authentication.** Face ID proves *who*; the coercion classifier proves *under what conditions*. A coerced approval blocks the txn even with sufficient other vouches and even with Face ID passing.
- **The intelligence and the movement are the same product.** Track 02 (financial intelligence) is not a side feature — it is the gate that decides which Track 01 (money movement) tier any given transaction enters.

---

## How it works

### The agent loop

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
                  Tier 1      Tier 2      Tier 3
                  execute     swipe       biometric vouch
                      │          │           │
                      └──────────┴───────────┘
                                 │
                          Rails executor ──▶ ledger + receipt
```

Every transaction the agent wants to make goes through the same three steps:

**1. Score.** Claude Haiku 4.5 reads the transaction JSON, the recipient's Specter profile (funding stage, headcount trend, recent news, signals matrix), and the company's payment history. It outputs a 0–100 risk score, the top three reasons, and a recommended tier. Haiku is chosen because it runs on every txn — it has to be cheap and fast.

**2. Route.** The tier router is deterministic rules first (amount bands, known-counterparty checks, Specter quality grade), with the LLM score as a tie-breaker on the boundary cases. The output is *which tier* and *why*. The "why" is stored — every threshold decision is auditable after the fact.

**3. Handle.** Tier 1 hits the Plaid sandbox executor immediately and writes a receipt. Tier 2 emits a push notification to the designated approver's phone with the swipe card. Tier 3 emits a Live Activity to all enrolled approvers' Dynamic Islands and waits for the multi-party biometric attestations.

A second LLM (**Claude Opus 4.7**) is called only on Tier 2 and Tier 3, to write the human-facing explainer ("recurring AWS bill, in band, first-of-month") and the post-hoc audit narrative. The two-model split is deliberate: Haiku handles cost-sensitive volume, Opus handles the small number of cases where prose quality matters.

### Tier 3 in detail (the part that actually breaks new ground)

When a transaction routes to Tier 3, this is the flow on the approver's phone:

1. The iOS **Dynamic Island** displays a compact red pill — `VOUCH REQUIRED · £62,000` — pulsing on a 1.4-second cycle.
2. Tapping expands the Live Activity into the Vouch app. The approver sees the amount, recipient, Specter grade, and approver position (`approver 1 of 3`).
3. **Face ID** runs via `expo-local-authentication` on native and `navigator.credentials.create({ userVerification: 'required' })` on the web (WebAuthn → platform authenticator: Touch ID on macOS, Windows Hello, Face ID in iOS Safari). The biometric template never leaves the device's secure enclave.
4. A **randomized challenge phrase** appears, containing the amount, recipient, and date — e.g. *"authorize sixty-two thousand to Acme on April thirty"*. The phrase is generated server-side at the moment of capture, which is the anti-replay primitive: no pre-recorded video can match a phrase that was generated 0.5 seconds ago.
5. A **5–8 second video selfie** is recorded via `react-native-vision-camera`, with the approver reading the phrase aloud.
6. The clip uploads to a Django Celery task that runs two models in parallel:
   - `opencv/facial_expression_recognition` — sampled at 4 fps, returns one of seven facial emotion classes (angry, disgust, fear, happy, neutral, sad, surprise).
   - `FunAudioLLM/SenseVoiceSmall` — single forward pass returns transcript, voice emotion, and acoustic event tags.
7. A **distress fusion heuristic** combines face emotion, voice emotion, speech cadence, and transcript-match against the challenge phrase. Any single high-confidence coerced signal flips the result to `coerced: true`.
8. The result panel renders on the approver's phone — green ✓ VOUCHED with method (Face ID / Touch ID / Passkey) and emotion grid, or red ● COERCED · BLOCKED with the reason.

For the transaction to execute, **all** required approvers (configurable per company; default 3 for amounts above £25k) must each complete this flow within a 30-minute window with no coerced flag. A single coerced flag is a hard block that cannot be overridden, regardless of how many other approvers vouched cleanly.

### Where the data lives

| Layer | Stack | Notes |
|---|---|---|
| Money rails | Plaid sandbox (transactions + auth) | Real bank linkage, sandbox txns for the demo |
| Agent + risk scoring | Django + Celery, Anthropic SDK, Specter API | Existing Django base; agent app added |
| Coercion classifier | Python (`transformers` + `torch`) as a Celery task | Takes the uploaded clip, returns the fused JSON result |
| Mobile (Tier 2 + Tier 3 + Dynamic Island) | React Native via Expo Router, `expo-local-authentication`, ActivityKit Live Activity | One binary handles both swipe and vouch screens |
| Dashboard | Django + HTMX + SSE | Live receipt feed, threshold config, signed audit log |

Mobile talks to Django over signed REST. Push goes via Expo Notifications with SMS fallback. The Face ID template never leaves the device; the challenge-phrase video and audio are uploaded to the server with a hard 24-hour retention TTL.

---

## Run it locally

You need Docker Desktop, Node.js with pnpm, and (for the mobile side) an iPhone with Expo Go or Xcode for the simulator.

### 1. Backend (Django + Postgres + Redis + Celery)

```bash
# from repo root
cp .env.example .env

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

Authentication is `django-allauth` with a Google social provider already wired (`/a/`). Email + password works out of the box. To enable Google sign-in, add a `SocialApp` row in the admin under *Social Accounts → Social applications* with your Google OAuth client ID/secret.

### 2. Mobile app (Expo / React Native)

```bash
cd mobile
pnpm install
pnpm start          # Metro bundler — scan the QR code with Expo Go on iPhone
pnpm ios            # or boot the iOS simulator directly
```

The app runs as a JS-only Expo Go project against mock data in `src/data/mockTransactions.ts`. Native biometrics use `expo-local-authentication` (real Face ID / Touch ID on device), with WebAuthn as the web fallback. The fully-prebuilt binary with `react-native-vision-camera` and the ActivityKit Live Activity binary is what the demo phones run.

**Routes:**
- `/` — transaction ledger (list)
- `/approve?id=…` — Tier 2 Tinder swipe (right = approve, left = reject, up = escalate)
- `/vouch?id=…` — Tier 3 biometric vouch with Dynamic Island banner

**The demo killer.** On `/vouch`, toggle the `duress` switch at the bottom before reaching the result stage. Same Face ID pass, same recording — the coercion classifier flags the cadence and blocks the txn. That is the 90-second pitch in one beat.

### 3. Required secrets in `.env`

The committed `.env.example` covers infra. For the demo path, also set:

```bash
ANTHROPIC_API_KEY=...           # Haiku 4.5 scorer + Opus 4.7 explainer
SPECTER_API_KEY=...             # counterparty quality oracle
PLAID_CLIENT_ID=...             # sandbox is fine
PLAID_SECRET=...
GOOGLE_OAUTH_CLIENT_ID=...      # optional, for /a/ Google sign-in
GOOGLE_OAUTH_CLIENT_SECRET=...
```

---

## The 90-second demo

| t | What the judge sees |
|---|---|
| 0–10s | Dashboard live: 12 invoices arrived in the last hour. 9 already auto-paid (Tier 1). Receipts streaming. |
| 10–25s | A £4,200 invoice to a new vendor pops on the presenter's phone as a Tinder card. Specter mini-card shows the vendor is a real seed-stage co. Swipe right. Paid. |
| 25–45s | A £62,000 transfer triggers. Tier 3 escalation fires to **the actual judges' phones** (pre-enrolled). Face ID prompt → randomized challenge phrase ("authorize sixty-two thousand to Acme on April thirty"). Voice + face captured. |
| 45–70s | On-device emotion panel renders: neutral / cadence ok. Three approvers complete. Money moves. |
| 70–90s | Re-run the same £62k txn, but the presenter reads the phrase under fake duress (rushed cadence). Coerced flag fires red, txn blocks. *That* is the moment. |

---

## What Vouch will not do

The guardrail on the guardrail. These are deliberately hard, not advisory:

- **Will not move money without rails approval.** Tier 3 multi-party block is a hard stop.
- **Will not store the Face ID template off-device.** It stays in the Secure Enclave. Challenge-phrase video/audio is sent to the server for emotion analysis with a 24h retention TTL.
- **Will not auto-pay an unknown counterparty over £5k**, regardless of risk score.
- **Will not adapt thresholds without an audit trail** — every threshold change is a signed config event.
- **Will not silently override a coerced flag** — a coerced attestation always blocks, even with sufficient other approvals.

---

## Repo layout

```
vouch/
├── PRD.md                      # Long-form product spec
├── design.md                   # Visual language, tokens, motion, tier-by-tier UX
├── docker-compose.yaml         # Postgres, Redis, Django, Celery, Flower, Kanchi, MailCatcher, Tailwind
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
└── mobile/                     # Expo Router RN app — Tier 2 swipe + Tier 3 vouch
    ├── app/
    │   ├── index.tsx           # ledger
    │   ├── approve.tsx         # Tier 2 swipe
    │   └── vouch.tsx           # Tier 3 biometric (with duress toggle)
    └── src/
        ├── components/
        ├── data/mockTransactions.ts
        ├── services/biometric.ts   # WebAuthn + expo-local-authentication
        └── tokens/                 # design tokens — single source of truth
```

For the visual language and design rationale, see [design.md](./design.md). For the long-form spec, see [PRD.md](./PRD.md).

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

---

*Built in Cursor. Moves money on Plaid. Reads Specter. Asks for a vouch.*
