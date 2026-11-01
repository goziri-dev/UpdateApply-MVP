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

type Phase = "email" | "details" | "confirm";
type ConfirmKind = "success" | "duplicate";

export function WaitlistForm() {
  const nameId = useId();
  const emailId = useId();
  const stageId = useId();
  const challengesId = useId();
  const privacyId = useId();
  const dialogTitleId = useId();
  const dialogDescriptionId = useId();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const nameRef = useRef<HTMLInputElement>(null);
  const emailRef = useRef<HTMLInputElement>(null);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [careerStage, setCareerStage] = useState<CareerStage | "">("");
  const [challenges, setChallenges] = useState("");
  const [loading, setLoading] = useState(false);
  const [emailAlert, setEmailAlert] = useState<string | null>(null);
  const [detailsAlert, setDetailsAlert] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("email");
  const [confirmKind, setConfirmKind] = useState<ConfirmKind>("success");
  const [confirmEmail, setConfirmEmail] = useState("");

  const focusFirst = useCallback(() => {
    window.setTimeout(() => {
      if (phase === "email") emailRef.current?.focus();
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

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (phase === "details" && !dialog.open) {
      dialog.showModal();
      window.requestAnimationFrame(() => nameRef.current?.focus());
    } else if (phase !== "details" && dialog.open) {
      dialog.close();
    }
  }, [phase]);

  function showEmailForm() {
    setLoading(false);
    setEmailAlert(null);
    setDetailsAlert(null);
    setPhase("email");
  }

  function showConfirm(kind: ConfirmKind, value: string) {
    setLoading(false);
    setEmailAlert(null);
    setDetailsAlert(null);
    setConfirmKind(kind);
    setConfirmEmail(value);
    setPhase("confirm");
  }

  function openDetails(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedEmail = normalizeEmail(email);
    const emailError = validateEmail(normalizedEmail);

    setEmailAlert(emailError);
    if (emailError) {
      emailRef.current?.focus();
      return;
    }

    setEmail(normalizedEmail);
    setDetailsAlert(null);
    setPhase("details");
  }

  async function submitSignup() {
    const normalizedName = normalizeName(name);
    const normalizedEmail = normalizeEmail(email);
    const normalizedChallenges = challenges.trim();
    setDetailsAlert(null);

    const nameError = validateName(normalizedName);
    if (nameError) {
      setDetailsAlert(nameError);
      nameRef.current?.focus();
      return;
    }
    const emailError = validateEmail(normalizedEmail);
    if (emailError) {
      setDetailsAlert(emailError);
      setPhase("email");
      window.setTimeout(() => emailRef.current?.focus());
      return;
    }
    const stageError = validateCareerStage(careerStage);
    if (stageError) {
      setDetailsAlert(stageError);
      return;
    }
    const challengesError = validateChallenges(normalizedChallenges);
    if (challengesError) {
      setDetailsAlert(challengesError);
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
      setDetailsAlert(message);
      nameRef.current?.focus();
    } catch {
      setLoading(false);
      setDetailsAlert("We couldn’t save that just now. Try again in a moment.");
      nameRef.current?.focus();
    }
  }

  function onDetailsSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;
    void submitSignup();
  }

  function onReset() {
    setName("");
    setEmail("");
    setCareerStage("");
    setChallenges("");
    showEmailForm();
    window.setTimeout(() => emailRef.current?.focus());
  }

  return (
    <div className="waitlist waitlist-hero" id="waitlist">
      <form noValidate onSubmit={openDetails} hidden={phase !== "email"}>
        <div className="alert" role="alert" hidden={!emailAlert}>
          {emailAlert}
        </div>

        <div className="fields" id="form-fields">
          <label className="sr-only" htmlFor={emailId}>
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
            aria-invalid={emailAlert ? true : undefined}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button className="btn" type="submit">
            Join the waiting list
          </button>
        </div>
      </form>

      <dialog
        ref={dialogRef}
        className="waitlist-dialog"
        aria-labelledby={dialogTitleId}
        aria-describedby={dialogDescriptionId}
        onCancel={(event) => {
          if (loading) {
            event.preventDefault();
          } else {
            setPhase("email");
          }
        }}
        onClick={(event) => {
          if (event.currentTarget === event.target && !loading) {
            setPhase("email");
          }
        }}
      >
        <form
          className="details-form"
          noValidate
          onSubmit={onDetailsSubmit}
        >
          <div className="dialog-heading">
            <div>
              <p className="dialog-eyebrow">One last step</p>
              <h2 id={dialogTitleId}>Tell us a little about you.</h2>
            </div>
            <button
              className="dialog-close"
              type="button"
              aria-label="Close"
              disabled={loading}
              onClick={() => setPhase("email")}
            >
              ×
            </button>
          </div>
          <p className="dialog-description" id={dialogDescriptionId}>
            Complete these details to join the waitlist. It won’t create an
            account.
          </p>
          <p className="dialog-email">
            {email}{" "}
            <button type="button" onClick={() => setPhase("email")}>
              Change
            </button>
          </p>

          <div className="alert dialog-alert" role="alert" hidden={!detailsAlert}>
            {detailsAlert}
          </div>

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
              aria-invalid={detailsAlert ? true : undefined}
              value={name}
              disabled={loading}
              onChange={(event) => setName(event.target.value)}
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
              aria-invalid={detailsAlert ? true : undefined}
              onChange={(event) =>
                setCareerStage(event.target.value as CareerStage | "")
              }
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
              onChange={(event) => setChallenges(event.target.value)}
            />
          </div>

          <button
            className="btn btn-submit"
            type="submit"
            disabled={loading}
            aria-busy={loading}
          >
            <span className="btn-label">
              {loading ? "Joining…" : "Finish joining"}
            </span>
            <span className="spinner" hidden={!loading} aria-hidden="true" />
          </button>
        </form>
      </dialog>

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
        Start with your email. We’ll ask for a few details before adding you to
        the list. We don’t sell your information.
      </p>
    </div>
  );
}
