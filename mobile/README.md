# Vouch — Mobile

React Native (Expo) app for Vouch's Tier 1 swipe approval and Tier 2 biometric vouch.

## Run

```bash
cd mobile
pnpm install
pnpm start          # Metro bundler
pnpm ios            # iOS simulator
```

The app currently runs as a JS-only Expo Go project against mock data
(`src/data/mockTransactions.ts`). Native modules (`react-native-biometrics`,
`react-native-vision-camera`, ActivityKit Live Activity) are wired in at
prebuild time once the demo path is signed off.

## Routes

- `/` — transaction ledger (list)
- `/approve?id=…` — Tier 1 Tinder swipe (right = approve, left = reject, up = escalate to Tier 2)
- `/vouch?id=…` — Tier 2 biometric vouch with Dynamic Island banner

## Design tokens

`src/tokens/{colors,typography,motion}.ts` — single source of truth.
Diagonal warm bloom gradient defined in `src/components/BloomGradient.tsx`.

## Demo killer

On `/vouch`, toggle the `duress` switch at the bottom before reaching the
result stage. Same Face ID pass, same recording — the coercion classifier
flags the cadence and blocks the txn. That is the 90-second pitch.
