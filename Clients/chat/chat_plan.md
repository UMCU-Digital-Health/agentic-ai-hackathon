# NoShow Chat — Implementation Plan

> **Status:** implemented (phases 0–8). 30 Vitest tests and 7 Playwright
> scenarios × 3 browsers pass; `npm run build` and `npm run lint` are clean.
> Deviations from the plan: none of substance — `document.fonts` and
> `ResizeObserver` are polyfilled in `tests/setup.ts` for Mantine under jsdom.

Companion to `Clients/planner/plan.md`. The chat client lives in `Clients/chat/`
(dev port **5174**, preview **4174**) and talks to the same FastAPI app on
port **8080**.

**Decisions locked in:** React 19 + TypeScript 6 + Vite 8 (already scaffolded) ·
Mantine **9.5.2** for all UI · `@tanstack/react-query` for fetching/polling ·
`openapi-fetch` + generated types, identical to the planner · MSW handlers
shared by Vitest and Playwright, identical to the planner · the selected
patient is carried in the `?patientId=` query parameter · polling hits
`GET /api/v1/recent-messages/{patient_id}/{message_id}` with `message_id = -1`
when nothing is on screen.

---

## 1. Where we stand today

### Backend (`src/hackathon_agentic_ai/api/`)

`app.py` now has CORS for 5173/5174/4173/4174 and an in-memory `store.py` that
backs calendar and waitlist items. **Messages are not in the store** — the three
message routes still return hard-coded stubs:

| Method | Path | Today | Problem for the chat |
| --- | --- | --- | --- |
| GET | `/api/v1/messages/{patient_id}` | 2 fixed messages (ids 1, 2) for any patient | Fine as an initial load, but not real |
| GET | `/api/v1/recent-messages/{patient_id}/{message_id}` | 2 fixed messages (ids 3, 4), filtered `id > message_id` | Works for the polling contract, but never returns anything new after the first poll |
| POST | `/api/v1/messages` | `{"message": "..."}` | Sent message is discarded; the client never learns its `id`, and it never shows up in a subsequent poll |

There is **no patient list endpoint**. Patients only exist as `(id, name)` pairs
inside `store._PATIENTS` / `store._WAITING` (exposed via `patient_name_for()`),
and indirectly through `calendar-items` / `waitlist-items`.

Contract the client must honour (`pydantic_models.py`):

```
MessageRole   = "system" | "user" | "assistant"
Message       { id: int, patient_id: int, role: MessageRole, content: str, timestamp: datetime }
MessageInput  { patient_id: int, role: MessageRole, content: str }
```

### Frontend (`Clients/chat/`)

Stock Vite template (`src/App.tsx` is the counter demo, with `App.css`,
`assets/`, `public/icons.svg`). Tooling already wired: oxlint, Vitest (jsdom +
Testing Library, `tests/unit/`, `tests/setup.ts`), Playwright (`tests/e2e/`,
chromium/firefox/webkit, `webServer: npm run dev`). Only `react`/`react-dom`
are dependencies. No `postcss.config.cjs`, no proxy in `vite.config.ts`.

`tsconfig.app.json` constraints (same as the planner):
`verbatimModuleSyntax` (use `import type`), `erasableSyntaxOnly` (**no TS
enums** — use `as const` objects), `noUnusedLocals`/`noUnusedParameters`.

---

## 2. API gaps and minimal changes

Principle: keep `app.py` route signatures and paths as they are; move message
state into `store.py`; add exactly **one** new route for the patient dropdown.

### 2.1 Persist messages in `store.py` (required)

Without this, polling can never surface anything new and a sent message
vanishes. Add to `store.py`:

```python
messages: list[Message] = _seed_messages()   # a short conversation per _PATIENTS entry
_message_ids = count(len(messages) + 1)

def messages_for(patient_id: int) -> list[Message]:
    return [m for m in messages if m.patient_id == patient_id]

def messages_after(patient_id: int, message_id: int) -> list[Message]:
    return [m for m in messages if m.patient_id == patient_id and m.id > message_id]

def add_message(item: MessageInput) -> Message:
    created = Message(id=next(_message_ids), timestamp=datetime.now(), **item.model_dump())
    messages.append(created)
    return created
```

Ids are global and monotonically increasing, which is exactly what the
"highest id on screen" polling contract needs. Seed: 2–4 messages for each
patient in `_PATIENTS` so every dropdown entry has a conversation; leave the
`_WAITING` patients empty so the "no messages yet → send -1" path is exercised
by real data.

Then in `app.py` replace the three stub bodies (signatures unchanged):

- `get_messages` → `return store.messages_for(patient_id)`
- `get_recent_messages` → `return store.messages_after(patient_id, message_id)`
- `create_message` → return type becomes `Message`, body
  `return store.add_message(message)`. Returning the created resource (instead
  of `{"message": str}`) is the one contract change; it is the same fix the
  planner requested for calendar items (its gap G1) and lets the client
  reconcile the sent message with the next poll by `id`.

### 2.2 `GET /api/v1/patients` (required, one new route)

The dropdown needs "name + id" for every patient. Deriving it client-side from
`calendar-items` ∪ `waitlist-items` would work today but couples the chat to
scheduling data and misses any patient that only has messages. One small route:

```python
class Patient(BaseModel):
    id: int
    name: str

@router.get("/patients")
async def get_patients() -> list[Patient]:
    return store.patients()      # sorted by id, from store._patient_names
```

`store.patients()` is a one-liner over the existing `_patient_names` dict.

### 2.3 Deliberately not changed

- Polling semantics: the client sends `-1` when empty; the server's
  `id > message_id` filter already returns everything for `-1`. No change.
- No `?since=` timestamp variant, no websockets/SSE — polling was specified.
- `GET /messages/{patient_id}` is kept but the client does **not** need it:
  the first poll with `-1` returns the full history. Using only
  `recent-messages` keeps a single code path. (Keep the route for other
  consumers.)
- The agent that will eventually reply as `assistant` is out of scope; until
  it exists the demo shows only what users/seed data produce.

### 2.4 Regenerating client types

After the API edits: `npm run gen:api` (added to the chat `package.json`, same
command as the planner) with the API running on 8080 → `src/api/schema.d.ts`.

---

## 3. Client architecture

### 3.1 Dependencies to add

```
@mantine/core @mantine/hooks @mantine/notifications   (9.5.2)
@tanstack/react-query  openapi-fetch  dayjs  @tabler/icons-react
dev: msw  openapi-typescript  postcss  postcss-preset-mantine  postcss-simple-vars
```

Copy `postcss.config.cjs` from the planner verbatim. Add the `"msw":
{"workerDirectory": ["public"]}` block and run `npx msw init public/`.

### 3.2 Config changes

- `vite.config.ts`: add `server.proxy['/api'] → http://localhost:8080` (copy of
  planner) and `optimizeDeps.include: ['@tabler/icons-react']`; add
  `src/api/schema.d.ts` to coverage excludes.
- `package.json` scripts: `gen:api`, `dev:mock` (`VITE_ENABLE_MSW=true vite`).
- `playwright.config.ts`: `webServer.command` → `npm run dev:mock` so e2e is
  deterministic and independent of the Python API.
- Remove the template: `App.css`, `assets/*`, `public/icons.svg`, the counter
  tests.

### 3.3 File layout

```
src/
  main.tsx                     MantineProvider + Notifications + QueryClientProvider, MSW bootstrap
  app/App.tsx                  AppShell: header with PatientSelect, ChatScreen body
  api/
    client.ts                  openapi-fetch client + queryKeys (copy from planner)
    schema.d.ts                generated
    types.ts                   Message, MessageInput, Patient, MESSAGE_ROLE as const
    patients.ts                usePatients()
    messages.ts                useMessages(patientId) — polling hook; useSendMessage()
  lib/
    messages.ts                pure helpers: mergeMessages(existing, incoming), highestId(messages), patientLabel(p)
    patientParam.ts            read/write ?patientId= (parse → number | null)
  state/
    usePatientId.ts            hook over URL search param (useSyncExternalStore on popstate + history.pushState wrapper)
  components/
    header/AppHeader.tsx       title + PatientSelect
    patient/PatientSelect.tsx  Mantine <Select searchable> — data = patients.map(p => ({value: String(p.id), label: `${p.name} (#${p.id})`}))
    chat/ChatScreen.tsx        empty state when no patient selected; otherwise MessageList + Composer
    chat/MessageList.tsx       ScrollArea, auto-scroll to bottom on new messages
    chat/MessageBubble.tsx     Paper aligned left (assistant/system) or right (user), timestamp via dayjs
    chat/Composer.tsx          Textarea + send Button (Enter sends, Shift+Enter newline)
    common/QueryError.tsx      Alert for failed queries (copy from planner)
  mocks/
    fixtures.ts                makePatients(), makeMessages()
    handlers.ts                GET patients, GET recent-messages (id > message_id filter), POST messages (appends, returns Message); resetMockData()
    browser.ts                 setupWorker
  styles/theme.ts              copy of the planner's UMC theme
```

### 3.4 Polling design (`api/messages.ts`)

```ts
export const useMessages = (patientId: number | null) => {
  const queryClient = useQueryClient()
  const key = queryKeys.messages(patientId)
  return useQuery({
    queryKey: key,
    enabled: patientId !== null,
    refetchInterval: POLL_INTERVAL_MS,        // 2000
    refetchIntervalInBackground: false,
    queryFn: async () => {
      const existing = queryClient.getQueryData<Message[]>(key) ?? []
      const since = highestId(existing)       // -1 when empty
      const incoming = unwrap(await api.GET('/api/v1/recent-messages/{patient_id}/{message_id}',
        { params: { path: { patient_id: patientId!, message_id: since } } }))
      return mergeMessages(existing, incoming)  // dedupe by id, sort by id
    },
  })
}
```

Key points:

- "Highest message id on screen" == highest id in the query cache for that
  patient; the cache **is** what is rendered. Reading it inside `queryFn`
  keeps the hook the single owner of the cursor — no separate state to drift.
- Switching patient changes the key → new cache entry, empty → first poll
  sends `-1` and fetches history. Old patient's cache is retained (`gcTime`
  default) so switching back is instant and continues from its cursor.
- `mergeMessages` dedupes by `id` so an optimistic/echoed sent message and
  the same message arriving via poll never double-render.
- `staleTime: 0` for this query so a remount re-polls immediately.

`useSendMessage`: `POST /api/v1/messages` with `{patient_id, role: 'user',
content}`; on success, `setQueryData(key, prev => mergeMessages(prev, [created]))`
so the message appears instantly with its real id, then the next poll
naturally continues from that id. On error: Mantine notification, keep the
draft text in the composer.

### 3.5 Patient selection & URL

- `usePatientId()` reads `?patientId=`; invalid/missing → `null`.
- `PatientSelect` `onChange` → `pushState` with the new param (no reload). Back
  button works via the `popstate` subscription.
- On load with a missing `patientId`, and once `usePatients()` resolves,
  **do not** auto-select — show an empty state "Select a patient to view the
  conversation" so the URL stays the source of truth. (If the team prefers
  auto-selecting the first patient, do it via `replaceState` in `ChatScreen`;
  one-line change.)
- If `patientId` isn't in the patient list, the Select shows it as a raw
  `#id` and the chat still polls — the API does not 404 on unknown patients.

### 3.6 UI (Mantine 9.5.2)

- `AppShell` with `header` (h=56): `Title order={3}` "NoShow Chat" + the
  `Select` (`w={320}`, `searchable`, `placeholder="Select patient"`,
  `data-testid="patient-select"`).
- Body: `Stack h="100%"`: `ScrollArea` (flex 1) of `MessageBubble`s, then
  `Composer` pinned at the bottom. Bubbles: `Paper radius="lg" p="sm"`,
  user = `umcBlue.6` bg / white text right-aligned, assistant = `gray.1`
  left-aligned, system = centred `Text c="dimmed" fs="italic"`.
- Timestamps `dayjs(ts).format('HH:mm')`; day separators are a nice-to-have.
- Loading: `Loader` centred on first fetch; `QueryError` `Alert` on failure
  (polling errors after first success are shown as a small dismissible
  banner, not a full replacement of the list).

---

## 4. Testing

### 4.1 Unit (Vitest + Testing Library + MSW node)

`tests/unit/helpers/renderWithProviders.tsx` (MantineProvider `env="test"`,
QueryClient `retry: false`) and `helpers/server.ts` mirror the planner. Use
`vi.useFakeTimers({ shouldAdvanceTime: true })` where polling matters.

| File | Covers |
| --- | --- |
| `lib/messages.test.ts` | `highestId([]) === -1`; highest across unsorted input; `mergeMessages` dedupes by id and sorts |
| `lib/patientParam.test.ts` | parse `?patientId=3` → 3, `?patientId=abc` → null, absent → null; serialise |
| `PatientSelect.test.tsx` | renders `Name (#id)` options from `/patients`; selecting updates the URL |
| `useMessages.test.tsx` | first request path is `/recent-messages/3/-1`; after messages load, next poll uses `/recent-messages/3/<maxId>` (assert via an MSW request spy); patient switch resets cursor to `-1` |
| `ChatScreen.test.tsx` | empty state with no `patientId`; renders bubbles by role alignment; send → POST body `{patient_id, role: 'user', content}` and message appears once (no duplicate after next poll) |
| `App.test.tsx` | shell renders; header + select present |

### 4.2 E2E (Playwright against `dev:mock`)

`tests/e2e/chat.spec.ts`:

1. `/` shows heading and the patient select with the empty state.
2. Select "Jane Smith (#2)" → URL contains `patientId=2`, seeded messages
   visible.
3. `/?patientId=1` deep link loads John Doe's conversation directly.
4. Send a message → appears as a user bubble; `page.waitForRequest` proves the
   subsequent poll used the new message's id in the path.
5. Switch patient via the dropdown → list replaced; browser Back returns to
   the previous patient.
6. Polling surfaces server-side messages: the MSW handler exposes a test hook
   (`window.__pushMessage`, only when `VITE_ENABLE_MSW`) that appends an
   assistant message; assert it appears without user action within ~3 s.

Keep chromium/firefox/webkit projects as scaffolded.

---

## 5. Implementation order

| Phase | Work | Done when |
| --- | --- | --- |
| 0 | API: `store.py` messages + `patients()`, `app.py` bodies + `/patients` route, `Patient` model | `curl localhost:8080/api/v1/recent-messages/1/-1` returns seeded messages; POST returns a `Message` with a new id, visible on next GET |
| 1 | Client deps, postcss, proxy, msw init, `gen:api`, strip template | `npm run typecheck` green on empty `App` |
| 2 | `api/client.ts`, `types.ts`, `lib/*` + their unit tests | `npm test` green |
| 3 | `usePatients`, `PatientSelect`, `usePatientId`, `AppHeader` | dropdown drives the URL |
| 4 | `useMessages` polling + `MessageList`/`MessageBubble` | live conversation against the real API |
| 5 | `Composer` + `useSendMessage` | round-trip send → poll |
| 6 | MSW handlers/fixtures, `renderWithProviders`, remaining unit tests | `npm test` green |
| 7 | Playwright spec, `dev:mock` wiring | `npm run test:e2e` green |
| 8 | README update (`Clients/README.md` scripts table already applies; add `dev:mock`/`gen:api` note) | |

---

## 6. Open questions (non-blocking; defaults chosen)

| # | Question | Default taken |
| --- | --- | --- |
| O1 | Auto-select first patient when `patientId` is absent? | No — empty state; see §3.5 |
| O2 | Poll interval | 2 s; constant in `api/messages.ts` |
| O3 | Should sending as the clinician use role `user` or `assistant`? The API's roles are chat-model-centric; the *patient* is the `user` in the agent's conversation | `user` for now; make it a single constant `SENT_ROLE` so it is a one-line flip |
| O4 | Pause polling when the tab is hidden | Yes (`refetchIntervalInBackground: false`) |
