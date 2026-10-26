# UpdateApply landing (`landing/`)

SEO marketing site for `updateapply.com`: brand + waitlist capture. Does **not**
create sessions or grant app access.

Approved design source: `design/prototypes/seo-landing/`.

## Run locally

```bash
cd landing
bun install
bun run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Scripts

| Script | Purpose |
| --- | --- |
| `bun run dev` | Next.js dev server |
| `bun run lint` | ESLint |
| `bun run typecheck` | `tsc --noEmit` |
| `bun run build` | Production build |
| `bun run start` | Serve production build |

## Waitlist API

The form posts to **`POST /api/waitlist`** on this Next app.

| Env | Role |
| --- | --- |
| `WAITLIST_API_URL` | If set, proxies to FastAPI `POST /api/v1/waitlist`. |
| `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` | Durable fallback: server-side insert into `waitlist_signup` (never `NEXT_PUBLIC_`). |
| *(neither)* | In-memory stub (local UI only; emails lost on restart). |
| `NEXT_PUBLIC_SITE_URL` | Canonical / OG base URL (`https://updateapply.com` in prod). |
| `NEXT_PUBLIC_APP_URL` | Footer “Open the app” link (`https://app.updateapply.com`). |

Priority: `WAITLIST_API_URL` → Supabase service role → stub.

Contract:

- Body: `{ "email": string, "source"?: "landing" }`
- `201` `{ status: "ok", email, duplicate: false }`
- `200` `{ status: "ok", email, duplicate: true }`
- `400` / `429` / `5xx` with `{ error, message }`

Local UI force-fail: `fail@…` (stub only).

## Deploy

See `scripts/deploy-landing-waitlist.sh` (Fly API + Vercel landing + domain cutover notes).

## Related

- Waitlist FastAPI + table → **TSK-50**
- Domain cutover (apex landing, `app.` Flutter) → **TSK-52**
- Jobs marketing section (`optional-jobs.jpg` exists; not in approved prototype)
