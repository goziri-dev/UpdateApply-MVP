# UpdateApply app

Flutter client for UpdateApply (auth + onboarding → resume reveal → dashboard / tailor).

## Run

```bash
cd app
flutter run -d chrome --dart-define-from-file=.env
```

Required `--dart-define` keys (see `.env.example` if present): `API_BASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`. Optional: `SUPABASE_AUTH_REDIRECT_URL`.

## Onboarding tone

The role/project chat is a **calm consultant conversation**, not a hiring interview. Copy and generated prompts invite honest detail (gaps, shared credit, underselling) without grilling.

## Parse timeouts (Flutter web)

On web, Dio’s `connectTimeout` is time until response **headers**. Resume `/parse` is a sync LLM call, so the client uses a raised per-request timeout in `OnboardingService.parse()`. Prefer a running API on `:8000` and a healthy OpenRouter key; timeouts surface as timeout copy, not “unreadable PDF.”

## Resume preview + PDF download

After Review, the flow opens **`/onboarding/reveal`** (`ResumeRevealScreen`; legacy `/onboarding/ready` is the same screen): full HTML preview of the remade master, **Download PDF**, then **Go to dashboard** (`complete` + gate refresh → `/`).

On the home dashboard, a **mini** letter-aspect preview (`ResumePreview` mini mode) taps into a modal with a larger preview + Download. Both surfaces use `ResumeService` → `GET/POST /api/v1/resume/html` (same server Jinja template as PDF). Default `template_id` is `classic`.

Download calls `POST /api/v1/resume/export`, then on **web** triggers a browser save via blob URL (`resume_download_web.dart`). Non-web builds stub and throw. Filename is derived from basics name when possible.

### Flutter web iframe caveat

Preview uses `HtmlElementView` + a registered `HTMLIFrameElement` (`srcdoc`) scaled to letter size. Platform view factories are keyed by `viewType` and reused across rebuilds/hot reload. If the preview goes blank, duplicates, or stops updating after code changes to the iframe layer, do a **full hot restart** (not just hot reload) so factories re-register cleanly. Mini mode sets `pointer-events: none` so the parent `InkWell` owns taps.
