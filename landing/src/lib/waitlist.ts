/** Shared waitlist capture contract (landing ↔ FastAPI). */

export const EMAIL_MAX = 254;
export const NAME_MAX = 120;
export const CHALLENGES_MAX = 1000;
export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Stable values stored in DB / sheet; labels are UI-only. */
export const CAREER_STAGES = [
  { value: "student", label: "Student / recent grad" },
  { value: "early_career", label: "Early career (0–2 years)" },
  { value: "mid_career", label: "Mid career (3–7 years)" },
  { value: "senior", label: "Senior (8+ years)" },
  { value: "career_changer", label: "Career changer" },
  { value: "other", label: "Other" },
] as const;

export type CareerStage = (typeof CAREER_STAGES)[number]["value"];

export const CAREER_STAGE_VALUES = CAREER_STAGES.map((s) => s.value);

export type WaitlistSuccess = {
  status: "ok";
  email: string;
  duplicate: boolean;
};

export type WaitlistErrorBody = {
  error:
    | "invalid_email"
    | "invalid_name"
    | "invalid_career_stage"
    | "rate_limited"
    | "save_failed";
  message: string;
};

export type WaitlistPayload = {
  name: string;
  email: string;
  career_stage: CareerStage;
  job_search_challenges?: string;
  source: "landing";
};

export function normalizeEmail(raw: string): string {
  return raw.trim().toLowerCase();
}

export function normalizeName(raw: string): string {
  return raw.trim().replace(/\s+/g, " ");
}

export function validateEmail(email: string): string | null {
  if (!email) return "Enter your email to join the waitlist.";
  if (!EMAIL_RE.test(email) || email.length > EMAIL_MAX) {
    return "That doesn’t look like an email we can save.";
  }
  return null;
}

export function validateName(name: string): string | null {
  if (!name) return "Enter your name.";
  if (name.length > NAME_MAX) return "That name is a bit long — shorten it.";
  return null;
}

export function validateCareerStage(stage: string): string | null {
  if (!stage) return "Choose your career stage.";
  if (!(CAREER_STAGE_VALUES as readonly string[]).includes(stage)) {
    return "Choose a career stage from the list.";
  }
  return null;
}

export function validateChallenges(raw: string): string | null {
  if (raw.length > CHALLENGES_MAX) {
    return "Keep that answer under 1000 characters.";
  }
  return null;
}
