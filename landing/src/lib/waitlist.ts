/** Shared waitlist capture contract (landing stub ↔ planned FastAPI TSK-50). */

export const EMAIL_MAX = 254;
export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export type WaitlistSuccess = {
  status: "ok";
  email: string;
  duplicate: boolean;
};

export type WaitlistErrorBody = {
  error: "invalid_email" | "rate_limited" | "save_failed";
  message: string;
};

export function normalizeEmail(raw: string): string {
  return raw.trim().toLowerCase();
}

export function validateEmail(email: string): string | null {
  if (!email) return "Enter your email to join the waitlist.";
  if (!EMAIL_RE.test(email) || email.length > EMAIL_MAX) {
    return "That doesn’t look like an email we can save.";
  }
  return null;
}
