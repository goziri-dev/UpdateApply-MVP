# UpdateApply app

Flutter client for UpdateApply (auth + onboarding → tailor).

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
