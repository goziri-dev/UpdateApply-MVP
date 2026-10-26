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
  normalizeEmail,
  validateEmail,
  type WaitlistErrorBody,
  type WaitlistSuccess,
} from "@/lib/waitlist";

type Phase = "form" | "confirm";
type ConfirmKind = "success" | "duplicate";

export function WaitlistForm() {
  const emailId = useId();
  const privacyId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("form");
  const [confirmKind, setConfirmKind] = useState<ConfirmKind>("success");
  const [confirmEmail, setConfirmEmail] = useState("");

  const focusEmail = useCallback(() => {
    window.setTimeout(() => {
      if (phase === "form") inputRef.current?.focus();
    }, 280);
  }, [phase]);

  useEffect(() => {
    const onHashFocus = (event: MouseEvent) => {
      const target = event.target as HTMLElement | null;
      const anchor = target?.closest?.('a[href="#waitlist"]');
      if (anchor) focusEmail();
    };
    document.addEventListener("click", onHashFocus);
    return () => document.removeEventListener("click", onHashFocus);
  }, [focusEmail]);

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

  async function submitEmail(raw: string) {
    const normalized = normalizeEmail(raw);
    setAlert(null);

    const clientError = validateEmail(normalized);
    if (clientError) {
      setAlert(clientError);
      inputRef.current?.focus();
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email: normalized, source: "landing" }),
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
      inputRef.current?.focus();
    } catch {
      setLoading(false);
      setAlert("We couldn’t save that just now. Try again in a moment.");
      inputRef.current?.focus();
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;
    void submitEmail(email);
  }

  function onReset() {
    setEmail("");
    showForm();
    inputRef.current?.focus();
  }

  return (
    <form className="waitlist waitlist-hero" id="waitlist" noValidate onSubmit={onSubmit}>
      <div className="alert" role="alert" hidden={!alert}>
        {alert}
      </div>

      <div className="fields" id="form-fields" hidden={phase !== "form"}>
        <label className="sr-only" htmlFor={emailId}>
          Email
        </label>
        <input
          ref={inputRef}
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
        <button className="btn" type="submit" disabled={loading} aria-busy={loading}>
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
          We’ll write to this address when a spot opens.
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
        We store your email only to tell you when a spot opens. We don’t sell
        it. Joining does not create an account or open the app.
      </p>
    </form>
  );
}
