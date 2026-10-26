import { createClient } from "@supabase/supabase-js";
import { NextRequest, NextResponse } from "next/server";

import {
  normalizeEmail,
  validateEmail,
  type WaitlistErrorBody,
  type WaitlistSuccess,
} from "@/lib/waitlist";

/**
 * Waitlist capture (TSK-50):
 * 1. WAITLIST_API_URL → proxy to FastAPI `POST /api/v1/waitlist`
 * 2. SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY → server-side insert into
 *    `waitlist_signup` (service role only; never expose to the browser)
 * 3. Else → in-memory stub (local UI only)
 */
const stubEmails = new Set<string>();

/** Simple per-IP sliding window: 10 requests / minute. */
const RATE_LIMIT = 10;
const RATE_WINDOW_MS = 60_000;
const hits = new Map<string, number[]>();

function clientKey(req: NextRequest): string {
  return (
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    req.headers.get("x-real-ip") ||
    "local"
  );
}

function rateLimited(key: string): boolean {
  const now = Date.now();
  const window = (hits.get(key) ?? []).filter((t) => now - t < RATE_WINDOW_MS);
  if (window.length >= RATE_LIMIT) {
    hits.set(key, window);
    return true;
  }
  window.push(now);
  hits.set(key, window);
  return false;
}

function errorJson(
  status: number,
  body: WaitlistErrorBody,
): NextResponse<WaitlistErrorBody> {
  return NextResponse.json(body, { status });
}

function successJson(
  body: WaitlistSuccess,
  status: 200 | 201,
): NextResponse<WaitlistSuccess> {
  return NextResponse.json(body, { status });
}

function supabaseConfigured(): boolean {
  return Boolean(
    process.env.SUPABASE_URL?.trim() &&
      process.env.SUPABASE_SERVICE_ROLE_KEY?.trim(),
  );
}

async function captureInSupabase(
  email: string,
  req: NextRequest,
): Promise<NextResponse> {
  const url = process.env.SUPABASE_URL!.trim();
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY!.trim();
  const supabase = createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  const source = "landing";
  const ip = clientKey(req);
  const userAgent = req.headers.get("user-agent")?.slice(0, 512) ?? null;

  const { error } = await supabase.from("waitlist_signup").insert({
    email,
    source,
    ip: ip === "local" ? null : ip,
    user_agent: userAgent,
  });

  if (!error) {
    return successJson({ status: "ok", email, duplicate: false }, 201);
  }

  // Unique violation → already on the list (idempotent success).
  if (error.code === "23505") {
    return successJson({ status: "ok", email, duplicate: true }, 200);
  }

  console.error("waitlist supabase insert failed", error.code, error.message);
  return errorJson(502, {
    error: "save_failed",
    message: "We couldn’t save that just now. Try again in a moment.",
  });
}

async function proxyToFastApi(
  email: string,
  req: NextRequest,
): Promise<NextResponse> {
  const base = process.env.WAITLIST_API_URL!.replace(/\/$/, "");
  const upstream = await fetch(base, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "user-agent": req.headers.get("user-agent") ?? "updateapply-landing",
      "x-forwarded-for": clientKey(req),
    },
    body: JSON.stringify({ email, source: "landing" }),
  });

  const text = await upstream.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }

  if (upstream.status === 201 || upstream.status === 200) {
    const parsed = data as Partial<WaitlistSuccess> | null;
    const duplicate =
      upstream.status === 200 ||
      parsed?.duplicate === true ||
      (typeof parsed?.status === "string" &&
        parsed.status.toLowerCase().includes("duplicate"));
    return successJson(
      {
        status: "ok",
        email: typeof parsed?.email === "string" ? parsed.email : email,
        duplicate,
      },
      duplicate ? 200 : 201,
    );
  }

  if (upstream.status === 409) {
    return successJson({ status: "ok", email, duplicate: true }, 200);
  }

  if (upstream.status === 400) {
    return errorJson(400, {
      error: "invalid_email",
      message: "That doesn’t look like an email we can save.",
    });
  }

  if (upstream.status === 429) {
    return errorJson(429, {
      error: "rate_limited",
      message: "Too many tries. Wait a moment and try again.",
    });
  }

  return errorJson(502, {
    error: "save_failed",
    message: "We couldn’t save that just now. Try again in a moment.",
  });
}

function stubCapture(email: string): NextResponse {
  // Prototype-compatible force-fail for local UI checks.
  if (email.startsWith("fail@")) {
    return errorJson(500, {
      error: "save_failed",
      message: "We couldn’t save that just now. Try again in a moment.",
    });
  }

  if (stubEmails.has(email)) {
    return successJson({ status: "ok", email, duplicate: true }, 200);
  }

  stubEmails.add(email);
  return successJson({ status: "ok", email, duplicate: false }, 201);
}

export async function POST(req: NextRequest) {
  if (rateLimited(clientKey(req))) {
    return errorJson(429, {
      error: "rate_limited",
      message: "Too many tries. Wait a moment and try again.",
    });
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return errorJson(400, {
      error: "invalid_email",
      message: "Enter your email to join the waitlist.",
    });
  }

  const raw =
    body && typeof body === "object" && "email" in body
      ? String((body as { email: unknown }).email ?? "")
      : "";
  const email = normalizeEmail(raw);
  const invalid = validateEmail(email);
  if (invalid) {
    return errorJson(400, { error: "invalid_email", message: invalid });
  }

  if (process.env.WAITLIST_API_URL) {
    try {
      return await proxyToFastApi(email, req);
    } catch {
      return errorJson(502, {
        error: "save_failed",
        message: "We couldn’t save that just now. Try again in a moment.",
      });
    }
  }

  if (supabaseConfigured()) {
    try {
      return await captureInSupabase(email, req);
    } catch {
      return errorJson(502, {
        error: "save_failed",
        message: "We couldn’t save that just now. Try again in a moment.",
      });
    }
  }

  return stubCapture(email);
}
