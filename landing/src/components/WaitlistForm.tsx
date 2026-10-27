"use client";

import {
  FormEvent,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";

import {
  CAREER_STAGES,
  normalizeEmail,
  normalizeName,
  validateCareerStage,
  validateChallenges,
  validateEmail,
  validateName,
  type CareerStage,
  type WaitlistErrorBody,
  type WaitlistSuccess,
} from "@/lib/waitlist";

type Phase = "form" | "confirm";
type ConfirmKind = "success" | "duplicate";

export function WaitlistForm() {
  const nameId = useId();
  const emailId = useId();
  const stageId = useId();
  const challengesId = useId();
  const privacyId = useId();
  const nameRef = useRef<HTMLInputElement>(null);
  const emailRef = useRef<HTMLInputElement>(null);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [careerStage, setCareerStage] = useState<CareerStage | "">("");
  const [challenges, setChallenges] = useState("");
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("form");
  const [confirmKind, setConfirmKind] = useState<ConfirmKind>("success");
  const [confirmEmail, setConfirmEmail] = useState("");

  const focusFirst = useCallback(() => {
    window.setTimeout(() => {
      if (phase === "form") nameRef.current?.focus();
    }, 280);
  }, [phase]);

  useEffect(() => {
    const onHashFocus = (event: MouseEvent) => {
      const target = event.target as HTMLElement | null;
      const anchor = target?.closest?.('a[href="#waitlist"]');
      if (anchor) focusFirst();
    };
    document.addEventListener("click", onHashFocus);
    return () => document.removeEventListener("click", onHashFocus);
  }, [focusFirst]);

  function showForm() {
    setLoading(false);
    setAlert(null);
    setPhase("form");
  }

  function showConfirm(kind: ConfirmKind, value: string) {
    setLoading(false);
    setAlert(null);
    setConfirmKind(kind);
    setConfirmEmail(value);
    setPhase("confirm");
  }

  async function submitSignup() {
    const normalizedName = normalizeName(name);
    const normalizedEmail = normalizeEmail(email);
    const normalizedChallenges = challenges.trim();
    setAlert(null);

    const nameError = validateName(normalizedName);
    if (nameError) {
      setAlert(nameError);
      nameRef.current?.focus();
      return;
    }
    const emailError = validateEmail(normalizedEmail);
    if (emailError) {
      setAlert(emailError);
      emailRef.current?.focus();
      return;
    }
    const stageError = validateCareerStage(careerStage);
    if (stageError) {
      setAlert(stageError);
      return;
    }
    const challengesError = validateChallenges(normalizedChallenges);
    if (challengesError) {
      setAlert(challengesError);
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          name: normalizedName,
          email: normalizedEmail,
          career_stage: careerStage,
          job_search_challenges: normalizedChallenges || undefined,
          source: "landing",
        }),
      });

      const data = (await res.json().catch(() => null)) as
        | WaitlistSuccess
        | WaitlistErrorBody
        | null;

      if (res.ok && data && "status" in data && data.status === "ok") {
        showConfirm(data.duplicate ? "duplicate" : "success", data.email);
        return;
      }

      const message =
        data && "message" in data && typeof data.message === "string"
          ? data.message
          : "We couldn’t save that just now. Try again in a moment.";
      setLoading(false);
      setAlert(message);
      nameRef.current?.focus();
    } catch {
      setLoading(false);
      setAlert("We couldn’t save that just now. Try again in a moment.");
      nameRef.current?.focus();
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;
    void submitSignup();
  }

  function onReset() {
    setName("");
    setEmail("");
    setCareerStage("");
    setChallenges("");
    showForm();
    nameRef.current?.focus();
  }

  return (
    <form className="waitlist waitlist-hero" id="waitlist" noValidate onSubmit={onSubmit}>
      <div className="alert" role="alert" hidden={!alert}>
        {alert}
      </div>

      <div className="fields fields-stack" id="form-fields" hidden={phase !== "form"}>
        <div className="field">
          <label className="field-label" htmlFor={nameId}>
            Name
          </label>
          <input
            ref={nameRef}
            id={nameId}
            name="name"
            type="text"
            autoComplete="name"
            maxLength={120}
            placeholder="Your name"
            aria-invalid={alert ? true : undefined}
            value={name}
            disabled={loading}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div className="field">
          <label className="field-label" htmlFor={emailId}>
            Email
          </label>
          <input
            ref={emailRef}
            id={emailId}
            name="email"
            type="email"
            inputMode="email"
            autoComplete="email"
            maxLength={254}
            placeholder="you@example.com"
            aria-describedby={privacyId}
            aria-invalid={alert ? true : undefined}
            value={email}
            disabled={loading}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <div className="field">
          <label className="field-label" htmlFor={stageId}>
            Career stage
          </label>
          <select
            id={stageId}
            name="career_stage"
            value={careerStage}
            disabled={loading}
            aria-invalid={alert ? true : undefined}
            onChange={(e) => setCareerStage(e.target.value as CareerStage | "")}
          >
            <option value="" disabled>
              Select one
            </option>
            {CAREER_STAGES.map((stage) => (
              <option key={stage.value} value={stage.value}>
                {stage.label}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label className="field-label" htmlFor={challengesId}>
            What’s hardest about your job search?{" "}
            <span className="optional">(optional)</span>
          </label>
          <textarea
            id={challengesId}
            name="job_search_challenges"
            rows={3}
            maxLength={1000}
            placeholder="Tailoring resumes, finding roles, staying organized…"
            value={challenges}
            disabled={loading}
            onChange={(e) => setChallenges(e.target.value)}
          />
        </div>

        <button className="btn btn-submit" type="submit" disabled={loading} aria-busy={loading}>
          <span className="btn-label">
            {loading ? "Joining…" : "Join the waitlist"}
          </span>
          <span className="spinner" hidden={!loading} aria-hidden="true" />
        </button>
      </div>

      <div className="confirm" id="form-confirm" hidden={phase !== "confirm"}>
        <p className="confirm-title">
          {confirmKind === "duplicate"
            ? "You’re already on the list."
            : "You’re on the list."}
        </p>
        <p className="confirm-body">
          Check your inbox for a short welcome note. We’ll write again when a
          spot opens.
        </p>
        <p className="confirm-email" title={confirmEmail}>
          {confirmEmail}
        </p>
        <p className="confirm-extra">
          {confirmKind === "duplicate"
            ? "This still doesn’t open the app."
            : "This does not open the app."}
        </p>
        <button className="btn btn-quiet" type="button" onClick={onReset}>
          Use a different email
        </button>
      </div>

      <p className="privacy" id={privacyId}>
        We store your name, email, and career stage to run the waitlist — and
        any note you share about job-search challenges. We don’t sell it.
        Joining does not create an account or open the app.
      </p>
    </form>
  );
}
