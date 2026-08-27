# Clients

Two React + TypeScript apps scaffolded with Vite.

| App       | Dev port | Preview port | Folder    |
| --------- | -------- | ------------ | --------- |
| `planner` | 5173     | 4173         | `planner` |
| `chat`    | 5174     | 4174         | `chat`    |

Ports are pinned with `strictPort`, so both apps can run side by side and a
port clash fails loudly instead of silently shifting.

Both use the same setup: Vite 8, React 19, TypeScript, oxlint, Vitest (jsdom +
Testing Library) for unit tests, and Playwright for end-to-end tests.

## Getting started

```bash
cd planner   # or: cd chat
npm install
npm run dev
```

First time only, install the Playwright browsers:

```bash
npx playwright install
```

## Scripts

| Command                 | What it does                                |
| ----------------------- | ------------------------------------------- |
| `npm run dev`           | Start the dev server                        |
| `npm run build`         | Typecheck and build for production          |
| `npm run preview`       | Serve the production build                  |
| `npm run lint`          | Run oxlint                                  |
| `npm run typecheck`     | Run `tsc -b`                                |
| `npm test`              | Run unit tests once (Vitest)                |
| `npm run test:watch`    | Run unit tests in watch mode                |
| `npm run test:coverage` | Unit tests with a v8 coverage report        |
| `npm run test:e2e`      | Run Playwright tests (starts the dev server)|
| `npm run test:e2e:ui`   | Playwright in UI mode                       |

## Layout

- `tests/unit/` — unit tests (Vitest + Testing Library)
- `tests/setup.ts` — Testing Library setup (jest-dom matchers, auto cleanup)
- `tests/e2e/` — Playwright specs, run against the dev server on the app's port
