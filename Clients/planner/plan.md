# NoShow Planner — Implementation Plan

The original task brief is preserved in `brief.md`.

**Decisions locked in for this revision:** FullCalendar is the calendar engine ·
Mantine v9.5.2 carries as much of the UI as possible · the API is fixed on port
**8080** · the API gains CORS and a `PUT /calendar-items/{id}` endpoint · the
UMC palette from §3.1 stands as sampled · the waitlist is ordered by
**`priority` ascending, i.e. highest priority first** (§5.3), superseding the
brief's "sorted by datetime" · `@tabler/icons-react` is the icon library
(§4.6) · `patient_id` has landed on `WaitListItem`.

---

## 1. Where we stand today

### Backend (`src/hackathon_agentic_ai/api/`)

`app.py` exposes a FastAPI app with `VERSION = "0.0.1"` and a single router at
`/api/v1`. Every handler returns hard-coded placeholder data — there is no
store, no persistence, no filtering. `run/api.py` now serves on a fixed
`0.0.0.0:8080`.

| Method | Path | Returns | Notes |
| --- | --- | --- | --- |
| GET | `/` | `{status, version}` | health check, **not** under `/api/v1` |
| GET | `/api/v1/waitlist-items` | `list[WaitListItem]` | 2 stubs, no query params |
| POST | `/api/v1/waitlist-items` | `{"message": ...}` | body `WaitListItemInput` |
| DELETE | `/api/v1/waitlist-items/{id}` | `{"message": ...}` | |
| GET | `/api/v1/calendar-items` | `list[CalendarItem]` | 2 stubs, **no date range params** |
| POST | `/api/v1/calendar-items` | `{"message": ...}` | body `CalendarItemInput` |
| DELETE | `/api/v1/calendar-items/{id}` | `{"message": ...}` | message hints an agent job is created |
| GET | `/api/v1/messages/{patient_id}` | `list[Message]` | |
| GET | `/api/v1/recent-messages/{patient_id}/{message_id}` | `list[Message]` | added since the first draft; not needed by the planner |
| POST | `/api/v1/messages` | `{"message": ...}` | |
| GET/POST/DELETE | `/api/v1/agent-jobs[/{id}]` | `AgentJob` | not needed for v1 of the planner |

Models (`pydantic_models.py`) — the contract the client must honour:

```
AppointmentStatus  = "scheduled" | "canceled"
WaitListItem       { id: int, patient_name: str, patient_id: int, priority: int }
WaitListItemInput  { patient_name: str, patient_id: int }
CalendarItem       { id, title, patient_id, patient_name, start_time: datetime,
                     end_time: datetime, status: AppointmentStatus }
CalendarItemInput  { title, patient_id, start_time, end_time, status=scheduled }
MessageRole        = "system" | "user" | "assistant"
Message            { id, patient_id, role: MessageRole, content, timestamp }
MessageInput       { patient_id, role, content }
AgentJob           { id, job_type, status, created_at, updated_at }
```

### Frontend (`Clients/planner/`)

Vite 8 + React 19 + TypeScript 6 scaffold, still the stock Vite template
(`src/App.tsx` is the counter demo). Tooling already wired: oxlint, Vitest
(jsdom + Testing Library, `tests/unit/`), Playwright (`tests/e2e/`, chromium /
firefox / webkit, auto-starts the dev server). Dev port pinned to **5173**
(`strictPort: true`), preview **4173**. Only `react` + `react-dom` in
`dependencies` — everything in §4 is a net-new install.

`tsconfig.app.json` is strict in ways that will bite:

- `verbatimModuleSyntax` — type-only imports must be `import type { … }`.
- `erasableSyntaxOnly` — **no TS `enum`s**, no parameter properties. Model
  `AppointmentStatus` as `const APPOINTMENT_STATUS = {…} as const` plus a
  derived union type.
- `noUnusedLocals` / `noUnusedParameters` — unused FullCalendar callback args
  will fail the build; name them out or omit them.

---

## 2. API changes

Two are requested outright (CORS, `PUT`); the rest are what the brief needs and
the API doesn't yet provide.

### 2.1 CORS — `src/hackathon_agentic_ai/api/app.py`

```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="No Show Agent API", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`5173` is the planner dev server, `4173` its preview build. Add `5174`/`4174`
when the `chat` client starts calling the API. Keep the list explicit —
`allow_origins=["*"]` together with `allow_credentials=True` is rejected by the
browser, which is a confusing failure to debug mid-hackathon.

### 2.2 `PUT /api/v1/calendar-items/{item_id}`

A full replace taking the existing `CalendarItemInput`, returning the updated
`CalendarItem`. This is the single endpoint that unblocks both drag-to-move and
the Edit-modal reschedule.

```python
@router.put("/calendar-items/{item_id}")
async def update_calendar_item(item_id: int, item: CalendarItemInput) -> CalendarItem:
    """
    Endpoint to update an existing calendar item.
    Replaces the calendar item identified by item_id with the supplied data
    and returns the updated item.
    """
    # Placeholder for actual implementation
    return CalendarItem(
        id=item_id,
        title=item.title,
        patient_id=item.patient_id,
        patient_name="John Doe",
        start_time=item.start_time,
        end_time=item.end_time,
        status=item.status,
    )
```

Because `PUT` is a replace, the client must send **every** field, not just the
new times. `useMoveCalendarItem` therefore reads the cached item and spreads the
new `start_time`/`end_time` over it — see §6 Phase 7. Note the response includes
`patient_name`, which `CalendarItemInput` has no field for; the server derives
it from `patient_id`, and until persistence exists the client should trust its
own cached value over the stub's echo.

### 2.3 Remaining gaps, and how the client absorbs them

| # | Gap | Impact | Handling |
| --- | --- | --- | --- |
| G1 | `POST` returns `{"message": str}`, not the created resource | Client never learns the new `id`; can't reconcile an optimistic insert | **Tracked as O3** (§2.4, §10). Interim: invalidate and refetch the list after every mutation |
| ~~G2~~ | ~~`WaitListItem` has no `patient_id`~~ | — | **Resolved.** `WaitListItem` is now `{id, patient_name, patient_id, priority}` and `WaitListItemInput` is `{patient_name, patient_id}`, so Phase 7 builds a real `CalendarItemInput` from a dropped card with no placeholder. Note the field is `patient_name`, **not** `name`. Still worth requesting: `duration_minutes` (would replace Phase 7's hardcoded 30-minute block) and `created_at` ("waiting since" copy on the card) |
| G3 | `GET /calendar-items` takes no `from`/`to` | Can't range-query per view | Fetch all, filter client-side — fine at hackathon volumes. Keep the TanStack query key shaped as `['calendar-items', {start, end}]` so adding `?start=&end=` later is a one-line change |
| G4 | No "alternative slots" endpoint | The Edit modal must propose alternative datetimes | Compute client-side in `lib/slots.ts` from free gaps inside working hours. Future: `GET /calendar-items/{id}/alternatives` served by the agent |
| G5 | Stub items have `start_time == end_time` (`datetime.now()` twice), no timezone | Zero-height events; naive-vs-aware comparison bugs | Enforce a minimum rendered height; treat naive datetimes as local time in exactly one place (`api/dates.ts`) and nowhere else |
| G6 | `patient_name` exists but there's no patient endpoint | "Full info" in the modal is thin | Show `patient_name`, `patient_id`, status, times. Optionally lazy-load `GET /messages/{patient_id}` in the modal as patient context |
| G7 | Two placeholder appointments only | You cannot eyeball a week grid with two zero-length events | **Tracked as O4** (§2.5, §10). Highest-value 10 minutes of backend work in this plan |

### 2.4 `POST` endpoints should return the created model (O3)

Both create endpoints currently return `{"message": str}`, so the client never
learns the new `id` and can't reconcile an optimistic insert. Mirror what `PUT`
now does:

```python
@router.post("/calendar-items")
async def create_calendar_item(item: CalendarItemInput) -> CalendarItem:
    """
    Endpoint to create a new calendar item.
    Accepts a CalendarItemInput object in the request body and returns the
    created calendar item.
    """
    # Placeholder for actual implementation
    return CalendarItem(id=_next_id(), patient_name="John Doe", **item.model_dump())
```

Same shape for `POST /waitlist-items` → `WaitListItem`. This changes the
response schema, so re-run `npm run gen:api` afterwards; the generated types
will point at every call site that needs updating.

### 2.5 Seed data (O4)

Two appointments with `start_time == end_time` cannot exercise a week grid —
no overlap layout, no drag targets, no zero-height guard, nothing to look at in
a demo. Replace the stub list with ~30 appointments spread across the current
week:

```python
from datetime import datetime, timedelta

_TITLES = ["Intake", "Controle", "Nacontrole", "Telefonisch consult", "MRI-bespreking"]
_PATIENTS = [(1, "John Doe"), (2, "Jane Smith"), (3, "Pieter de Vries"),
             (4, "Fatima El Amrani"), (5, "Sanne Bakker")]


def _seed_calendar_items() -> list[CalendarItem]:
    """Build a week of demo appointments anchored on the current Monday."""
    monday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    monday -= timedelta(days=monday.weekday())
    items: list[CalendarItem] = []
    for day in range(5):  # Mon-Fri
        for slot in range(6):
            index = day * 6 + slot
            patient_id, patient_name = _PATIENTS[index % len(_PATIENTS)]
            start = monday + timedelta(days=day, hours=9 + slot, minutes=30 * (slot % 2))
            items.append(
                CalendarItem(
                    id=index + 1,
                    title=f"{_TITLES[index % len(_TITLES)]} - {patient_name}",
                    patient_id=patient_id,
                    patient_name=patient_name,
                    start_time=start,
                    end_time=start + timedelta(minutes=30 if index % 3 else 60),
                    status=AppointmentStatus.CANCELED
                    if index % 7 == 0
                    else AppointmentStatus.SCHEDULED,
                )
            )
    return items
```

Deliberately includes varied durations, a few canceled items, and two
appointments per hour so the overlap layout gets exercised.

### 2.6 Vite proxy

With the API fixed on 8080, proxy in dev so the client only ever calls relative
paths and CORS never enters the picture locally (the middleware above is still
needed for preview builds and any non-proxied access):

```ts
// vite.config.ts — inside defineConfig({ server: { … } })
proxy: {
  '/api': { target: 'http://localhost:8080', changeOrigin: true },
},
```

`api/client.ts` then uses `import.meta.env.VITE_API_BASE_URL ?? '/api/v1'`.

---

## 3. Design system

### 3.1 Palette (sampled from `examples/umc_utrecht_color_palette.png` — unchanged)

| Token | Hex | Used for |
| --- | --- | --- |
| `--umc-blue` | `#298FF5` | header bar, primary buttons, today marker, selected date |
| `--umc-blue-light` | `#C3E3FD` | appointment blocks, card backgrounds, hover fills |
| `--umc-indigo` | `#2B20D0` | links, section headings, icon accents |
| `--umc-orange` | `#FB6944` | accent / alerts — canceled appointments, high-priority waitlist |
| `--umc-ink` | `#011020` | primary text |
| `--umc-white` | `#FFFFFF` | surfaces |

### 3.2 Feeding the palette to Mantine

Mantine wants 10-shade tuples and generates its CSS variables from them, so the
palette is declared **once** in the theme and everything downstream — Mantine
components, our CSS Modules, and the FullCalendar overrides — reads
`var(--mantine-color-*)`. No component references a hex.

```ts
// src/styles/theme.ts
import { createTheme } from '@mantine/core'

export const theme = createTheme({
  primaryColor: 'umcBlue',
  primaryShade: 6,
  fontFamily: 'system-ui, "Segoe UI", Roboto, sans-serif',
  defaultRadius: 'md',
  radius: { sm: '6px', md: '10px', lg: '16px' },
  colors: {
    // index 6 is the sampled brand colour; verify the ramp with
    // https://mantine.dev/colors-generator/ before committing
    umcBlue: ['#eef7ff','#d9ecfe','#b0d7fd','#84c1fc','#5faefa',
              '#3d9df7','#298ff5','#1a7ade','#0d6bc6','#005aae'],
    umcOrange: ['#fff0ec','#ffe0d8','#ffc0b0','#ff9e84','#fe8160',
                '#fd6f4a','#fb6944','#e05635','#c8492b','#ae3b20'],
    umcIndigo: ['#ecebfd','#d5d3fa','#a9a4f4','#7c74ee','#5a50e9',
                '#443ae6','#3a2fe5','#2f24cb','#2b20d0','#221a9f'],
  },
})
```

Semantic aliases layer on top in `src/styles/tokens.css`, so appointment
styling is nameable rather than shade-numbered:

```css
:root {
  --color-event-bg: var(--mantine-color-umcBlue-1);        /* ≈ #C3E3FD */
  --color-event-border: var(--mantine-color-umcBlue-6);    /* #298FF5 */
  --color-event-canceled-bg: var(--mantine-color-umcOrange-0);
  --color-event-canceled-border: var(--mantine-color-umcOrange-6);
  --color-grid-line: var(--mantine-color-gray-3);
}
```

Light mode only — set `forceColorScheme="light"` on `MantineProvider` and delete
the stock `prefers-color-scheme: dark` block in `index.css`. A half-themed dark
mode is worse than none.

### 3.3 Layout (from `examples/outlook_with_sidebar.png`)

```
┌──────────────────────────────────────────────────────────────────────┐
│ AppShell.Header  [☰] NoShow Planner   (blue #298FF5, 56px)     [☰]   │
├────────────┬──────────────────────────────────────┬──────────────────┤
│ AppShell   │ AppShell.Main                        │ AppShell         │
│ .Navbar    │ ┌──────────────────────────────────┐ │ .Aside           │
│ (280px)    │ │ Toolbar                          │ │ (320px)          │
│            │ │ [Today] [‹][›] 24–30 August 2026 │ │                  │
│ [Today]    │ │                        [Week ▾]  │ │ Waitlist         │
│ ┌────────┐ │ ├──────────────────────────────────┤ │ ─────────        │
│ │DatePick│ │ │                                  │ │ ▸ patient card   │
│ │ er     │ │ │  CalendarView  or  ListView      │ │ ▸ patient card   │
│ └────────┘ │ │  (scrollable, drop target)       │ │   (draggable)    │
│ collapsible│ └──────────────────────────────────┘ │ collapsible      │
└────────────┴──────────────────────────────────────┴──────────────────┘
```

Mantine's `AppShell` is a near-exact match for the mockup and removes the need
for a hand-rolled CSS Grid shell:

```tsx
<AppShell
  header={{ height: 56 }}
  navbar={{ width: 280, breakpoint: 'md', collapsed: { desktop: !leftOpen, mobile: !leftOpen } }}
  aside={{ width: 320, breakpoint: 'lg', collapsed: { desktop: !rightOpen, mobile: !rightOpen } }}
  padding={0}
>
```

`leftOpen` / `rightOpen` come from `useDisclosure`, persisted with
`useLocalStorage` (both from `@mantine/hooks`). AppShell handles the collapse
transition and the `Main` offset itself.

### 3.4 Component inventory

| Region | Built from |
| --- | --- |
| Header | `AppShell.Header` + `Group`, `Burger` ×2, `Title` — "NoShow Planner" |
| Left sidebar | `AppShell.Navbar`, `Button` (pill "Today"), `DatePicker` from `@mantine/dates` |
| Toolbar | `Group`, `Button`, `ActionIcon` (‹ ›), `Text` for the range label, view `Menu` |
| View dropdown | `Menu` — see §5.1 |
| Calendar view | FullCalendar, chrome from Mantine, chips styled with our tokens |
| List view | `Stack` + `Paper` rows, sticky day headers, `Badge` for status |
| Appointment popover | `Popover` (calendar) / `Modal` (list) with `Button` + `Divider` |
| Edit flow | `Modal` + `Radio.Group` of proposed slots |
| Right sidebar | `AppShell.Aside`, `ScrollArea`, `Card` per waitlist entry, `Badge` for priority |
| Feedback | `@mantine/notifications` for drag failures and mutation errors |

The two custom-styled surfaces are the FullCalendar grid and the appointment
chips. Everything else is stock Mantine with theme tokens.

---

## 4. Dependencies

Versions verified against npm on 27 August 2026.

```bash
npm i @mantine/core@9.5.2 @mantine/hooks@9.5.2 @mantine/dates@9.5.2 \
      @mantine/notifications@9.5.2 dayjs @tabler/icons-react@^3.46.0 \
      @fullcalendar/core@6.1.21 @fullcalendar/react@6.1.21 \
      @fullcalendar/daygrid@6.1.21 @fullcalendar/timegrid@6.1.21 \
      @fullcalendar/interaction@6.1.21 \
      @tanstack/react-query openapi-fetch

npm i -D openapi-typescript msw postcss-preset-mantine postcss-simple-vars
```

### 4.1 Pin FullCalendar to 6.1.21 — this one matters

npm's `latest` tags are **inconsistent across the FullCalendar packages right
now**: `@fullcalendar/react` and `@fullcalendar/core` are on `7.0.2`, while
`daygrid`, `timegrid`, and `interaction` are still on `6.1.21` (v7 exists for
them only under the `rc` tag). An unpinned `npm i @fullcalendar/react
@fullcalendar/daygrid …` therefore installs **core@7 alongside plugins@6**,
which fails the plugins' own `"@fullcalendar/core": "~6.1.21"` peer constraint
and breaks at runtime.

Pin all five to `6.1.21`. It is the stable line, its React peer range includes
`^19`, and it needs no `temporal-polyfill` (a new v7 peer dependency). Revisit
v7 when the plugins ship a stable release.

### 4.2 What Mantine replaces

Choosing Mantine collapses several decisions from the previous revision:

| Need | Now | Instead of |
| --- | --- | --- |
| App shell / collapsible sidebars | `AppShell` | hand-rolled CSS Grid |
| Dropdown, modal, popover | `Menu`, `Modal`, `Popover` | Radix UI |
| Mini month picker | `DatePicker` (`@mantine/dates`) | react-day-picker |
| Icons | `@tabler/icons-react` (§4.6) | lucide-react |
| Collapse / persisted UI state | `useDisclosure`, `useLocalStorage` | zustand |
| Toasts | `@mantine/notifications` | — |

### 4.3 dayjs, not date-fns

`@mantine/dates` declares `dayjs` as a peer dependency, so dayjs is coming in
regardless. Use it as the *only* date library rather than carrying date-fns
alongside it. Register the ISO-week plugin once, in `main.tsx`, for Monday-first
weeks:

```ts
import dayjs from 'dayjs'
import isoWeek from 'dayjs/plugin/isoWeek'
dayjs.extend(isoWeek)
```

FullCalendar takes plain `Date` objects, so `lib/ranges.ts` computes with dayjs
and hands `.toDate()` across the boundary.

### 4.4 Remaining choices, briefly

- **TanStack Query v5** for server state — the `onMutate` optimistic-update /
  rollback cycle is exactly what drag-to-reschedule needs, especially while G1
  keeps POST responses opaque.
- **openapi-typescript + openapi-fetch** so the Pydantic models *are* the client
  contract: `npx openapi-typescript http://localhost:8080/openapi.json -o
  src/api/schema.d.ts`, wired as an `npm run gen:api` script. A hand-written
  `types/api.ts` is a legitimate fallback, but it drifts the moment the backend
  moves.
- **MSW v2** so the client can be built and tested before the backend catches
  up, with one handler set shared by Vitest and Playwright.

### 4.5 Mantine setup steps that are easy to miss

1. `postcss.config.cjs` with `postcss-preset-mantine` + `postcss-simple-vars`
   (required for Mantine's breakpoint mixins).
2. Import stylesheets in `main.tsx`, **in this order, before your own CSS**:
   `@mantine/core/styles.css`, `@mantine/dates/styles.css`,
   `@mantine/notifications/styles.css`.
3. Wrap the tree: `<MantineProvider theme={theme} forceColorScheme="light">` →
   `<DatesProvider settings={{ firstDayOfWeek: 1, locale: 'nl' }}>` →
   `<Notifications />` → `<QueryClientProvider>`.
4. Mantine's CSS resets the box model; import `tokens.css` *after* Mantine so
   our overrides win without `!important`.

### 4.6 Icons — `@tabler/icons-react`

Every icon in the app comes from `@tabler/icons-react` (pinned `^3.46.0`). It is
Mantine's own icon set, so sizing, stroke weight, and optical alignment match
Mantine's components without per-icon nudging, and it is what Mantine's docs
examples use — worth something when you are copying a `Menu` or `Modal` example
under time pressure.

**House style.** `size={16}` inside Mantine `Button` / `Menu.Item` sections,
`size={18}` for standalone `ActionIcon`s, `stroke={1.5}` throughout — Tabler's
default stroke of `2` reads heavy next to Mantine's typography. Icons here are
decorative, so the accessible name belongs on the interactive parent
(`aria-label` on the `ActionIcon`), not on the SVG.

**Icon map** — every name verified against 3.46.0:

| Where | Icon |
| --- | --- |
| Header sidebar toggles | Mantine `Burger` (not an icon) |
| Toolbar prev / next | `IconChevronLeft` / `IconChevronRight` |
| Toolbar today | `IconCalendarEvent` |
| Dropdown trigger | `IconChevronDown` |
| Dropdown — Day | `IconColumns1` |
| Dropdown — Three Day | `IconColumns3` |
| Dropdown — Working Week | `IconColumns` |
| Dropdown — Week | `IconCalendarWeek` |
| Dropdown — Month | `IconCalendarMonth` |
| Dropdown — List | `IconList` |
| Appointment popover — time row | `IconClock` |
| Appointment popover — patient row | `IconUser` |
| Popover actions | `IconPencil` / `IconTrash` |
| Waitlist card drag affordance | `IconGripVertical` |
| Edit modal — proposed slot | `IconCalendarTime` |
| Error `Alert` | `IconAlertCircle` |

`IconColumns1` / `IconColumns3` / `IconColumns` give Day / Three Day / Working
Week a consistent visual family, which is what the Outlook dropdown does.

**Vite caveat.** The barrel import (`import { IconClock } from
'@tabler/icons-react'`) pulls a very large module graph and can make the dev
server crawl on first load. If you feel it, add the package to
`optimizeDeps.include` in `vite.config.ts` so esbuild pre-bundles it once:

```ts
optimizeDeps: { include: ['@tabler/icons-react'] },
```

Production builds tree-shake correctly either way, so this is a dev-experience
fix, not a bundle-size one. Keep the barrel import — deep per-icon paths are an
unnecessary readability tax.

---

## 5. Two details worth specifying up front

### 5.1 The view dropdown

`Menu` in Mantine 9 has `Menu.RadioGroup` / `Menu.RadioItem` and
`Menu.CheckboxItem`, which map onto `examples/outlook_filter_dropdown.png`
exactly — including the mockup's key subtlety: **`Week` and `List` are ticked at
the same time**, because range and view mode are orthogonal state.

```tsx
<Menu closeOnItemClick={false} position="bottom-end">
  <Menu.Target>
    <Button variant="subtle" rightSection={<IconChevronDown size={16} />}>
      {RANGE_LABELS[range]}
    </Button>
  </Menu.Target>
  <Menu.Dropdown>
    <Menu.RadioGroup value={range} onChange={(v) => setRange(v as Range)}>
      <Menu.RadioItem value="day"      leftSection={<IconColumns1 size={16} />}>Day</Menu.RadioItem>
      <Menu.RadioItem value="threeDay" leftSection={<IconColumns3 size={16} />}>Three Day</Menu.RadioItem>
      <Menu.RadioItem value="workWeek" leftSection={<IconColumns size={16} />}>Working Week</Menu.RadioItem>
      <Menu.RadioItem value="week"     leftSection={<IconCalendarWeek size={16} />}>Week</Menu.RadioItem>
      <Menu.RadioItem value="month"    leftSection={<IconCalendarMonth size={16} />}>Month</Menu.RadioItem>
    </Menu.RadioGroup>
    <Menu.Divider />
    <Menu.CheckboxItem
      checked={mode === 'list'}
      onChange={(c) => setMode(c ? 'list' : 'calendar')}
      leftSection={<IconList size={16} />}
    >
      List
    </Menu.CheckboxItem>
  </Menu.Dropdown>
</Menu>
```

State: `range: 'day'|'threeDay'|'workWeek'|'week'|'month'` defaulting to
`'week'`, and `mode: 'calendar'|'list'` defaulting to `'calendar'`.

### 5.2 FullCalendar view mapping

```ts
export const FC_CONFIG = {
  day:      { view: 'timeGridDay' },
  threeDay: { view: 'timeGridThreeDay',
              views: { timeGridThreeDay: { type: 'timeGrid', duration: { days: 3 } } } },
  workWeek: { view: 'timeGridWeek', hiddenDays: [0, 6] },
  week:     { view: 'timeGridWeek' },
  month:    { view: 'dayGridMonth' },
} as const
```

Shared options: `firstDay: 1`, `slotMinTime: '07:00'`, `slotMaxTime: '19:00'`,
`allDaySlot: false`, `headerToolbar: false` (our Mantine toolbar drives it via a
ref → `getApi().changeView()` / `gotoDate()`), `nowIndicator: true`,
`height: '100%'`, `expandRows: true`, `slotDuration: '00:30'`,
`snapDuration: '00:15'`, `locale: 'nl'`, plus `eventContent` for the custom chip
and `eventClassNames` for canceled styling.

### 5.3 Waitlist ordering

The right sidebar sorts by `priority` **ascending** — `priority` is a *rank*,
so `1` is the most urgent patient and lower numbers come first. This supersedes
the brief's "sorted by datetime", which the current model can't support anyway.

```ts
// src/lib/waitlist.ts
import type { WaitListItem } from '../api/schema'

/**
 * Highest priority first. `priority` is a rank, not a magnitude: 1 is the most
 * urgent patient, so the numeric sort is ascending. The function name states
 * the intent because the mechanics read backwards at a glance.
 */
export const byHighestPriorityFirst = (a: WaitListItem, b: WaitListItem) =>
  a.priority - b.priority || a.id - b.id

export const sortWaitlist = (items: readonly WaitListItem[]) =>
  [...items].sort(byHighestPriorityFirst)
```

Three things this pins down:

- **Rank semantics, named as such.** "Ascending numeric" and "highest priority
  first" mean the same thing here but sound like opposites, which is exactly how
  a sort gets silently inverted during a later refactor. The comparator is named
  for the intent, the docstring states the rule once, and nothing else in the
  codebase re-derives it.
- **Ties break by `id` ascending**, so equal priorities fall back to insertion
  order and the list never reshuffles between renders. `Array.prototype.sort` is
  stable in every engine we target, but an explicit tie-breaker documents the
  intent and survives a switch to a virtualised list.
- **Sorting is a pure function over the fetched array, not a query concern.**
  `useWaitlist` returns the raw list and `RightSidebar` applies `sortWaitlist`,
  so it stays trivially unit-testable and moves server-side for free if the API
  later grows an `?order_by=` parameter.

Surface the ordering in the UI: a "By priority" label in the `Aside` header, and
a priority `Badge` on each `Card` — `umcOrange` for `priority === 1`, `gray`
above that — so the order visibly matches the data rather than looking
arbitrary. Label the badge `P1` / `P2` rather than a bare number, so it reads as
a rank instead of a score.

---

## 6. Target file layout

```
Clients/planner/
  postcss.config.cjs             # postcss-preset-mantine
  src/
    main.tsx                     # Mantine + Dates + Notifications + Query providers
    app/
      App.tsx                    # AppShell composition
    styles/
      theme.ts                   # Mantine theme — the palette lives here
      tokens.css                 # semantic aliases over --mantine-color-*
      fullcalendar-overrides.css # vendor CSS pinned to those tokens
    api/
      schema.d.ts                # GENERATED — do not edit
      client.ts                  # openapi-fetch instance
      dates.ts                   # parseApiDate / toApiDate — the ONLY tz boundary
      calendarItems.ts           # useCalendarItems / useMoveCalendarItem /
                                 #   useUpdateCalendarItem / useDeleteCalendarItem
      waitlist.ts                # useWaitlist / useScheduleWaitlistItem
    state/
      useViewState.ts            # range | mode | anchorDate (context, not zustand)
    lib/
      ranges.ts                  # range -> {start, end, label, fcView}; pure dayjs
      slots.ts                   # alternative-slot suggestion (G4)
      waitlist.ts                # byHighestPriorityFirst comparator (§5.3)
    components/
      header/AppHeader.tsx
      sidebar-left/{LeftSidebar,TodayButton,MiniMonth}.tsx
      sidebar-right/{RightSidebar,WaitlistCard}.tsx
      toolbar/{Toolbar,RangeNav,ViewMenu}.tsx
      calendar/{CalendarView,EventChip}.tsx
      list/{ListView,ListDayGroup,ListRow}.tsx
      appointment/{AppointmentPopover,EditAppointmentModal,SlotOption}.tsx
  tests/
    unit/…  e2e/…  msw/handlers.ts
```

Rules of thumb: `lib/ranges.ts` and `lib/slots.ts` are pure functions over dates
with no React import, so they're cheap to unit-test exhaustively; colour is only
ever read through tokens; `api/dates.ts` is the single place that decides what a
naive backend datetime means.

---

## 7. Build phases

Each phase is independently demoable — which matters if the hackathon clock runs out.

### Phase 0 — Backend (~40 min)

The four open items from §11, in the order they unblock client work. All four
live in `src/hackathon_agentic_ai/api/app.py`.

1. **O4 — seed data** (§2.5). Do this *first*: it costs ten minutes and every
   later phase is easier to eyeball with a full week on screen.
2. **O1 — `CORSMiddleware`** (§2.1).
3. **O2 — `PUT /calendar-items/{item_id}`** (§2.2).
4. **O3 — `POST` returns the created model** (§2.4).

Verify each one before moving on:

```bash
uv run python run/api.py &                                   # port 8080

curl -s localhost:8080/openapi.json | jq '.paths | keys'     # O2: put path present?
curl -s localhost:8080/api/v1/calendar-items | jq 'length'   # O4: ~30, not 2
curl -s localhost:8080/api/v1/calendar-items \
  | jq '.[0] | .start_time != .end_time'                     # O4: true

curl -si -X OPTIONS localhost:8080/api/v1/calendar-items \
  -H 'Origin: http://localhost:5173' \
  -H 'Access-Control-Request-Method: PUT' \
  | grep -i access-control-allow                             # O1: headers present

curl -s -X PUT localhost:8080/api/v1/calendar-items/1 \
  -H 'Content-Type: application/json' \
  -d '{"title":"t","patient_id":1,"start_time":"2026-08-27T09:00:00","end_time":"2026-08-27T09:30:00","status":"scheduled"}' \
  | jq '.id'                                                 # O2: returns the item, not a message
```

Then regenerate the client types — `npm run gen:api` — since O2 and O3 both
change the OpenAPI document.

**If Phase 0 slips, don't wait.** Point the client at MSW (§4.4) with handlers
matching the *target* shapes above and keep building. The handoff is a base-URL
change, and the MSW handlers are worth writing regardless because the tests need
them.

### Phase 1 — Shell and theme
Delete the Vite demo (`App.tsx`, `App.css`, `src/assets/*`, and the two scaffold
tests that assert on it). Install deps, add PostCSS config, wire the providers,
write `theme.ts` + `tokens.css`. Build the `AppShell`: header with the "NoShow
Planner" title and two `Burger`s, `Navbar` with the Today button and
`DatePicker`, `Aside` placeholder, collapse state persisted via
`useLocalStorage`. Static, no data.
**Done when** the screenshot layout is recognisable and both sidebars collapse.

### Phase 2 — Data layer
*Needs O1 (or the Vite proxy) and O4.* `npm run gen:api` → `schema.d.ts`. Write `client.ts`, `dates.ts`, the query
hooks, and the `QueryClient` (`staleTime: 30_000`). Render the waitlist as
`Card`s in the `Aside`, ordered with `sortWaitlist` from §5.3 (`priority`
ascending — rank 1 first — with `id` ascending as tie-breaker), headed
"By priority".
**Done when** real API data appears and a failed request shows an inline `Alert`,
not a blank pane.

### Phase 3 — Ranges, toolbar, dropdown
`lib/ranges.ts`: `getRange(range, anchor) → {start, end, label, fcView}` and
`step(range, anchor, ±1)`, both pure dayjs. Build the toolbar and the §5.1 menu.
Unit-test `ranges.ts` hard — Monday-first weeks, month boundaries, DST
transitions, and the three-day window's anchoring.

### Phase 4 — List view
Group the filtered items by day; sticky `Paper` day headers; rows matching
`examples/outlook_list.png` (date chip · colour bar · title · time range ·
patient); canceled items muted with the orange token; empty state. List view
comes **before** the calendar deliberately — it validates the range logic with
zero vendor complexity in the way.

### Phase 5 — Calendar view
Mount FullCalendar with §5.2, driven by `range` through a ref. Then the CSS
override pass: FullCalendar exposes `--fc-*` custom properties — map those to
our tokens in `fullcalendar-overrides.css` rather than fighting selector
specificity. Custom `eventContent` renders the chip (title, time, patient).

### Phase 6 — Popover, delete, edit
*Needs O2 for the reschedule; the popover and delete work without it.*
Clicking an event (calendar **or** list row) opens the
`examples/outlook_edit_appointment.png` layout — `Popover` anchored to the chip
in calendar view, `Modal` in list view. Content: colour dot, title, clock icon +
full date + `09:00 to 16:20`, `patient_name` / `patient_id`, status `Badge`,
`Divider`, then filled `Edit Event` and outline `Delete Event`.
`Delete` → confirm → `DELETE` + optimistic removal. `Edit` → `Modal` with a
`Radio.Group` of alternatives from `lib/slots.ts` (same duration, working hours,
no overlap, nearest-first) → `PUT` on confirm.

### Phase 7 — Drag and drop
*Needs O2 for appointment moves and O3 to reconcile a dropped waitlist card
without a full refetch.*
1. **Move an appointment:** `editable: true`, `eventStartEditable: true`,
   **`eventDurationEditable: false`** (this is the "position, not size"
   requirement), `snapDuration: '00:15'`. `eventDrop` calls
   `useMoveCalendarItem`, which — because `PUT` is a full replace — spreads the
   new times over the cached item:

   ```ts
   mutationFn: ({ item, start, end }) => PUT('/calendar-items/{item_id}', {
     params: { path: { item_id: item.id } },
     body: {
       title: item.title, patient_id: item.patient_id, status: item.status,
       start_time: toApiDate(start), end_time: toApiDate(end),
     },
   })
   ```

   with an optimistic cache write in `onMutate` and `info.revert()` plus a
   notification in `onError`.
2. **Waitlist → calendar:** `new Draggable(asideRef.current, { itemSelector:
   '[data-waitlist-item]', eventData: el => ({ title: el.dataset.patientName,
   duration: '00:30' }) })` from `@fullcalendar/interaction` — the field is
   `patient_name`, not `name` — with `droppable: true` on the
   calendar. `eventReceive` → `POST /calendar-items`, then `DELETE
   /waitlist-items/{id}`, invalidating both queries. Guard the drop against
   overlapping an existing appointment — the brief says "open sections of the
   calendar" — and `revert()` with a notification on collision.

### Phase 8 — Polish
`Skeleton` loaders, empty states, `aria-label`s on every `ActionIcon`, keyboard
paths through the menu and modals, responsive collapse at the AppShell
breakpoints, an error boundary, README notes.

---

## 8. Testing

**Unit (Vitest + Testing Library).** `ranges.ts` across all five ranges plus
month/year boundaries and DST; `slots.ts` (never overlaps, respects working
hours, preserves duration); `dates.ts` round-trip; the view menu (defaults to
Week + Calendar; choosing List keeps the range ticked); list-view day grouping;
waitlist ordering — `byHighestPriorityFirst` puts `priority: 1` above
`priority: 2`, breaks ties by ascending `id`, doesn't mutate its input, and
handles the empty and single-item cases.

Mantine components need the provider in tests — add a `renderWithProviders`
helper in `tests/setup.ts` wrapping `MantineProvider` + `QueryClientProvider`,
and register the `window.matchMedia` and `ResizeObserver` stubs Mantine expects
under jsdom. Doing this once in Phase 1 avoids a wave of confusing failures later.

**Component (Vitest + MSW).** Calendar and list render fetched items; clicking
an item opens the popover; delete calls the endpoint and removes the row; a
failing request renders the error state.

**E2E (Playwright).** The five flows worth protecting:
1. Load → week calendar shows this week's appointments.
2. Each dropdown range changes the visible span; `Today` returns to now.
3. `List` switches the view and preserves the selected range.
4. Click appointment → popover → delete → it disappears.
5. Drag a waitlist card onto a free slot → it appears on the calendar and leaves
   the waitlist. Use manual mouse steps rather than `page.dragAndDrop`;
   HTML5-drag emulation is flaky. If it stays flaky, keep the assertion at
   component level on the mutation hook rather than dropping the coverage.

---

## 9. Risks

| Risk | Mitigation |
| --- | --- |
| FullCalendar package versions drift apart again (§4.1) | Pin exact versions; add a `postinstall` sanity check or just re-read the lockfile after any FullCalendar bump |
| FullCalendar's default CSS fights the UMC look | Dedicated override pass in Phase 5, driven through `--fc-*` variables mapped to Mantine tokens |
| Mantine + FullCalendar are two styling systems in one app | Confine FullCalendar's CSS to `fullcalendar-overrides.css`; everything else is Mantine + `tokens.css`. Watch z-index: Mantine `Popover`/`Modal` must render above the calendar grid — set `zIndex` on the Popover if the chip overlaps |
| Naive backend datetimes vs. browser timezone | One conversion boundary in `api/dates.ts`, unit-tested; never call `new Date(str)` anywhere else |
| `PUT` is a full replace — a partial body silently blanks fields | `useMoveCalendarItem` always spreads over the cached item (§7 Phase 7); consider a Zod-free assertion in the mutation fn that all required fields are present |
| Mantine breaks under jsdom without matchMedia/ResizeObserver stubs | Set them up in `tests/setup.ts` during Phase 1, not when tests start failing |
| Scope: month view + drag + edit-alternatives is a lot | Phases 1–6 are the demoable core; Phase 7 is the "wow"; Phase 8 is optional |

---

## 10. Open items

Four backend changes are still outstanding. All are specified in §2 and
scheduled in Phase 0 — this table is the tracker to work down during the build.

| # | Item | Where | Blocks | Done when |
| --- | --- | --- | --- | --- |
| **O1** | Add `CORSMiddleware` | §2.1 | Preview builds and any non-proxied access. Dev is covered by the Vite proxy (§2.6), so this is not urgent — but it fails *silently until deploy*, which is the worst time to find it | `OPTIONS` preflight returns `access-control-allow-*` headers for origin `localhost:5173` |
| **O2** | Add `PUT /calendar-items/{item_id}` | §2.2 | **The real blocker.** Phase 6's reschedule and Phase 7's drag-to-move both dead-end without it | `PUT` appears in `/openapi.json` and returns the updated `CalendarItem` |
| **O3** | `POST` endpoints return the created model | §2.4 | Optimistic inserts in Phase 7; without it every create needs a full refetch | `POST /calendar-items` responds with a `CalendarItem`, not `{"message": …}` |
| **O4** | Seed ~30 realistic appointments | §2.5 | Nothing strictly — but it makes Phases 4–7 far easier to build and is the difference between a demo and two invisible zero-length events | `GET /calendar-items` returns ~30 items spanning the current week with non-zero durations |

Two nice-to-haves worth raising with whoever owns the model, neither blocking:
`duration_minutes` on `WaitListItem` (would replace Phase 7's hardcoded
30-minute drop block) and `created_at` ("waiting since" copy on the card).

**Resolved during planning:** `patient_id` on `WaitListItem` (now
`{id, patient_name, patient_id, priority}`); the API port fixed at 8080; the
`priority` rank-vs-magnitude question (rank — see §5.3).

---

## 11. Definition of done

- Header reads **NoShow Planner** on the UMC blue bar.
- Left sidebar: `Today` + Monday-first `DatePicker`, collapsible, state persisted.
- Right sidebar: waitlist with patient info, ordered by `priority` ascending
  (rank 1 = highest, first in the list), collapsible, draggable.
- Dropdown: Day / Three Day / Working Week / Week / Month, divider, `List`
  toggle; defaults to **Calendar + Week**; drives both views.
- Calendar renders API `CalendarItem`s in all five ranges; list view mirrors it.
- Clicking an appointment in either view opens the info popover with full
  details, Edit, and Delete; delete removes it; edit reschedules it via `PUT`.
- Appointments drag to a new position and never resize; waitlist items drag onto
  free calendar space and become appointments.
- `npm run lint`, `npm run typecheck`, `npm test`, and `npm run test:e2e` pass.
- All four open items in §10 are closed, and `npm run gen:api` has been re-run
  against the final OpenAPI document with no leftover MSW-only assumptions in
  `src/api/`.
