# NoShow Planner

The scheduling client for the No Show Agent: a week calendar of clinic
appointments, a priority-ordered waitlist, and drag-and-drop rescheduling.

Built with React 19 + Vite, [Mantine](https://mantine.dev) for the UI shell,
[FullCalendar](https://fullcalendar.io) for the grid, TanStack Query for server
state, and `openapi-fetch` typed against the API's own OpenAPI document.

## Running it

The API lives in this repo and serves on port **8080**:

```bash
uv run python run/api.py          # from the repository root
npm install
npm run dev                       # http://localhost:5173
```

`vite.config.ts` proxies `/api` to port 8080, so the client only ever calls
relative paths and CORS never enters the picture in dev.

To run without the API at all — useful for UI work and what the e2e suite
uses — start it against the mock handlers instead:

```bash
npm run dev:mock
```

## Scripts

| Script | Does |
| --- | --- |
| `npm run dev` | Dev server on 5173, proxying `/api` to the real API |
| `npm run dev:mock` | Dev server backed by the MSW handlers in `src/mocks` |
| `npm run build` | Typecheck and production build |
| `npm run lint` | oxlint |
| `npm run typecheck` | `tsc -b` |
| `npm test` | Vitest unit and component tests |
| `npm run test:e2e` | Playwright, across chromium / firefox / webkit |
| `npm run gen:api` | Regenerate `src/api/schema.d.ts` from the running API |

Re-run `gen:api` whenever the Pydantic models change — the generated types then
point at every call site that needs updating.

## Layout

```
src/
  app/App.tsx        AppShell composition and all the cross-cutting handlers
  api/               generated schema, openapi-fetch client, query hooks
    dates.ts         the ONLY place a naive backend datetime becomes a Date
  lib/               pure functions: ranges, slot suggestions, waitlist order
  state/             range | mode | anchorDate, in context
  components/        header, sidebars, toolbar, calendar, list, appointment
  mocks/             MSW handlers, shared by Vitest and Playwright
  styles/            Mantine theme (the palette), tokens, FullCalendar overrides
```

Two conventions worth knowing before editing:

- **Colour is only ever read through tokens.** The UMC palette is declared once
  in `styles/theme.ts`; components reference `var(--mantine-color-*)` or the
  semantic aliases in `styles/tokens.css`, never a hex.
- **`api/dates.ts` owns the timezone boundary.** The API sends naive datetimes;
  they mean local clinic time. `new Date(someApiString)` appears nowhere else.

## Testing

`lib/` is pure functions over dates with no React import, so it is unit-tested
exhaustively — ranges across all five spans plus month, year and DST
boundaries; slot proposals for duration, working hours and overlaps; waitlist
ordering. Component tests render through `tests/unit/helpers/renderWithProviders`
against MSW. The Playwright suite covers loading, every range, the List toggle,
click-to-details, delete, reschedule, and both drag flows.

Mantine needs `matchMedia` and `ResizeObserver` stubs under jsdom, and
`env="test"` on its provider so transitions settle — both are handled in
`tests/setup.ts` and the render helper.
