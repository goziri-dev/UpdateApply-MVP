/**
 * UpdateApply onboarding prototype — interactive multi-step flow.
 * Mock data only; no network. Hard gate (no skip).
 */

const STEPS = ["upload", "parsing", "interview", "review", "ready"];
const STEP_LABEL = {
  upload: "1 / 5",
  parsing: "2 / 5",
  interview: "3 / 5",
  review: "4 / 5",
  ready: "5 / 5",
};

const ILLUS_CAPTION = {
  upload: "Your profile takes shape as you go",
  parsing: "Reading your resume…",
  interview: "Voice fills in what the PDF missed",
  review: "Check anything that looks off",
  ready: "Ready to tailor to a job description",
};

const MOCK_PROFILE = {
  name: "Favour Akubuo",
  email: "favour@updateapply.dev",
  location: "Lagos, Nigeria",
  links: "linkedin.com/in/favour · github.com/favour",
  experiences: [
    {
      id: "exp-1",
      title: "Software Engineer",
      company: "Northwind Labs",
      dates: "2022 — Present",
      summary:
        "Built product features across API and Flutter clients; owned resume-tailoring experiments.",
    },
  ],
  projects: [
    {
      id: "proj-1",
      title: "UpdateApply",
      dates: "2025 — Present",
      summary:
        "Personal product: persist a career profile, then tailor resumes to job descriptions.",
    },
  ],
  skills: ["Flutter", "Dart", "Python", "FastAPI", "PostgreSQL", "Product design"],
};

const INTERVIEW_SCRIPT = {
  "exp-1": {
    label: "Software Engineer · Northwind Labs",
    kind: "role",
    coverage: ["Scope", "Stack", "Impact", "Collaboration"],
    questions: [
      "Walk me through what you owned day to day in this role — products, systems, or teams.",
      "You mentioned fullstack work. Besides the UI, what did you touch on the backend or data side?",
      "What outcome are you most proud of here — a metric, a launch, or a hard problem you unblocked?",
      "Anything else about this role I should capture before we move on?",
    ],
    mockTranscripts: [
      "I owned the tailor flow end-to-end — FastAPI endpoints, Postgres profile storage, and the Flutter client screens.",
      "I designed the profile schema, wrote Alembic migrations, and wired auth so only completed profiles can tailor.",
      "We cut time-to-first-tailored-resume from a blank page to under ten minutes for new users in dogfood.",
      "That's all for this role.",
    ],
  },
  "proj-1": {
    label: "UpdateApply (project)",
    kind: "project",
    coverage: ["Problem", "Approach", "Stack", "Status"],
    questions: [
      "What problem does UpdateApply solve for you, and who is it for?",
      "How does the career profile become a tailored resume — what's the core loop?",
      "What did you build yourself versus what you're still mocking in this prototype?",
      "Anything else about this project before we wrap interviews?",
    ],
    mockTranscripts: [
      "Job seekers who rewrite resumes from scratch for every JD. I wanted one persisted profile as the source of truth.",
      "Upload or interview into a structured profile, then tailor against a job description from that SSOT.",
      "Auth and onboarding prototypes are in HTML; Flutter auth ships; tailor and parse APIs are next.",
      "That's all.",
    ],
  },
};

const state = {
  step: "upload",
  file: null,
  error: null,
  info: null,
  parseTick: 0,
  parseTimer: null,
  forceParseError: false,
  micDenied: false,
  recording: false,
  interviewQueue: ["exp-1", "proj-1"],
  interviewIndex: 0,
  questionIndex: 0,
  coverageHits: {},
  transcript: "",
  profile: clone(MOCK_PROFILE),
};

const pane = () => document.getElementById("pane-left");
const indicator = () => document.getElementById("step-indicator");
const backBtn = () => document.getElementById("back-btn");
const illus = () => document.getElementById("illus");
const illusCaption = () => document.getElementById("illus-caption");

function clone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

function setStep(step) {
  state.step = step;
  state.error = null;
  state.info = null;
  state.recording = false;
  indicator().textContent = STEP_LABEL[step];
  illus().dataset.phase = step;
  illusCaption().textContent = ILLUS_CAPTION[step];
  backBtn().disabled = step === "upload" || step === "ready";
  render();
}

function showError(msg) {
  state.error = msg;
  state.info = null;
  render();
}

function showInfo(msg) {
  state.info = msg;
  state.error = null;
  render();
}

function alertHtml() {
  if (state.error) {
    return `<div class="alert" role="alert" data-visible="true">${escapeHtml(state.error)}</div>`;
  }
  if (state.info) {
    return `<div class="alert alert-info" role="status" data-visible="true">${escapeHtml(state.info)}</div>`;
  }
  return `<div class="alert" data-visible="false"></div>`;
}

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

/* —— Renderers —— */

function renderUpload() {
  const hasFile = Boolean(state.file);
  const dropInner = hasFile
    ? `
      <div class="file-chip">
        <div class="file-chip-icon">PDF</div>
        <div class="file-chip-meta">
          <p class="file-chip-name">${escapeHtml(state.file.name)}</p>
          <p class="file-chip-size">${formatBytes(state.file.size)} · ready to upload</p>
        </div>
        <button type="button" class="file-chip-remove" id="remove-file">Remove</button>
      </div>`
    : `
      <div class="dropzone-icon" aria-hidden="true">+</div>
      <p class="dropzone-title">Choose a PDF or drag and drop it here</p>
      <p class="dropzone-hint">PDF only · max 10MB · LinkedIn export recommended</p>
      <button type="button" class="browse-btn" id="browse-btn">Browse File</button>`;

  pane().innerHTML = `
    <h1 class="headline">Let's build your profile</h1>
    <p class="helper">Upload any existing resume. We'll extract your basics, history, and projects — then interview each role and project so your profile has real evidence.</p>
    ${alertHtml()}
    <div class="dropzone" id="dropzone" data-has-file="${hasFile}" tabindex="0" role="button" aria-label="Upload resume PDF">
      <input class="hidden-input" id="file-input" type="file" accept="application/pdf,.pdf" />
      ${dropInner}
    </div>
    <div class="actions">
      <button type="button" class="btn btn-primary" id="upload-cta" ${hasFile ? "" : "disabled"}>
        <span class="label-idle">Upload resume</span>
        <span class="spinner" aria-hidden="true"></span>
      </button>
    </div>`;

  bindUpload();
}

function bindUpload() {
  const dropzone = document.getElementById("dropzone");
  const input = document.getElementById("file-input");
  const browse = document.getElementById("browse-btn");
  const remove = document.getElementById("remove-file");
  const cta = document.getElementById("upload-cta");

  const openPicker = (e) => {
    e?.preventDefault?.();
    e?.stopPropagation?.();
    input.click();
  };

  dropzone.addEventListener("click", (e) => {
    if (e.target.closest("#remove-file") || e.target.closest(".file-chip-remove")) return;
    if (!state.file) openPicker(e);
  });
  dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") openPicker(e);
  });
  browse?.addEventListener("click", openPicker);
  input.addEventListener("change", () => {
    if (input.files?.[0]) acceptFile(input.files[0]);
  });

  ["dragenter", "dragover"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.dataset.active = "true";
    });
  });
  ["dragleave", "drop"].forEach((evt) => {
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.dataset.active = "false";
    });
  });
  dropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer?.files?.[0];
    if (file) acceptFile(file);
  });

  remove?.addEventListener("click", (e) => {
    e.stopPropagation();
    state.file = null;
    state.error = null;
    render();
  });

  cta.addEventListener("click", () => {
    if (!state.file) {
      showError("Choose a PDF resume to continue. Onboarding can’t be skipped.");
      return;
    }
    cta.classList.add("is-loading");
    cta.disabled = true;
    window.setTimeout(() => startParsing(), 450);
  });
}

function acceptFile(file) {
  const name = file.name || "resume.pdf";
  const isPdf =
    file.type === "application/pdf" ||
    name.toLowerCase().endsWith(".pdf") ||
    file.__forcePdf;

  if (!isPdf && !file.__forcePdf) {
    state.file = null;
    showError("That file isn’t a PDF. Upload a PDF resume (LinkedIn export works).");
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    state.file = null;
    showError("This file is over 10MB. Export a leaner PDF and try again.");
    return;
  }
  state.file = { name, size: file.size || 245760 };
  state.error = null;
  render();
}

function startParsing() {
  state.forceParseError = false;
  state.parseTick = 0;
  setStep("parsing");
  clearInterval(state.parseTimer);
  state.parseTimer = window.setInterval(() => {
    state.parseTick += 1;
    if (state.forceParseError) {
      clearInterval(state.parseTimer);
      state.parseTimer = null;
      render();
      return;
    }
    if (state.parseTick >= 4) {
      clearInterval(state.parseTimer);
      state.parseTimer = null;
      state.interviewIndex = 0;
      state.questionIndex = 0;
      state.coverageHits = {};
      state.transcript = "";
      window.setTimeout(() => setStep("interview"), 400);
      return;
    }
    render();
  }, 700);
}

function renderParsing() {
  if (state.forceParseError) {
    pane().innerHTML = `
      <h1 class="headline">We couldn’t read that resume</h1>
      <p class="helper">The PDF uploaded, but parsing failed. Try another export, or re-upload a text-based PDF (not a scan).</p>
      <div class="alert" role="alert" data-visible="true">Parsing error: no extractable text found in this PDF.</div>
      <div class="actions">
        <button type="button" class="btn btn-primary" id="retry-upload">Try another PDF</button>
      </div>`;
    document.getElementById("retry-upload").addEventListener("click", () => {
      state.file = null;
      state.forceParseError = false;
      setStep("upload");
    });
    return;
  }

  const items = [
    "Basics (name, email, location, links)",
    "Education & certifications",
    "Work history",
    "Projects & skills",
  ];
  const active = Math.min(state.parseTick, items.length - 1);

  pane().innerHTML = `
    <h1 class="headline">Reading your resume</h1>
    <p class="helper">We’re extracting a structured profile. Interviews start once your experience list is ready — this usually takes a few seconds.</p>
    <div class="parse-card">
      <div class="parse-status">
        <div class="parse-spinner" aria-hidden="true"></div>
        <div>
          <p class="parse-title">${escapeHtml(state.file?.name || "resume.pdf")}</p>
          <p class="parse-sub">Parsing PDF · please keep this tab open</p>
        </div>
      </div>
      <ul class="parse-list">
        ${items
          .map((label, i) => {
            const done = i < state.parseTick;
            const isActive = i === active && state.parseTick < items.length;
            return `<li data-done="${done}" data-active="${isActive}">
              <span class="check">${done ? "✓" : ""}</span>
              <span>${label}</span>
            </li>`;
          })
          .join("")}
      </ul>
    </div>`;
}

function currentInterview() {
  const id = state.interviewQueue[state.interviewIndex];
  return { id, script: INTERVIEW_SCRIPT[id] };
}

function renderInterview() {
  const { id, script } = currentInterview();
  if (!script) {
    setStep("review");
    return;
  }

  const q = script.questions[state.questionIndex];
  const turn = state.questionIndex + 1;
  const totalQ = script.questions.length;
  const hits = state.coverageHits[id] || [];

  const chips = state.interviewQueue
    .map((qid, i) => {
      const s = INTERVIEW_SCRIPT[qid];
      let st = "todo";
      if (i < state.interviewIndex) st = "done";
      if (i === state.interviewIndex) st = "active";
      return `<span class="chip" data-state="${st}"><span class="chip-dot"></span>${escapeHtml(s.label)}</span>`;
    })
    .join("");

  const micLabel = state.recording
    ? "Recording… tap to stop"
    : state.micDenied
      ? "Mic blocked — type your answer"
      : "Tap to record your answer";

  pane().innerHTML = `
    <h1 class="headline">${script.kind === "role" ? "Tell us about this role" : "Tell us about this project"}</h1>
    <p class="helper">Resume bullets are a checklist. Your voice is the evidence. Aim for a couple of minutes — say “that’s all” when you’re done.</p>
    <div class="checklist">${chips}</div>
    ${alertHtml()}
    <div class="interview-card">
      <div class="interview-meta">
        <p class="interview-item">${escapeHtml(script.label)}</p>
        <p class="interview-turn">Follow-up ${turn} of ~${totalQ}</p>
      </div>
      <div class="interview-body">
        <p class="ai-bubble"><span class="ai-label">UpdateApply</span>${escapeHtml(q)}</p>
        <div class="record-row">
          <button type="button" class="mic-btn" id="mic-btn" data-recording="${state.recording}" aria-pressed="${state.recording}" aria-label="${micLabel}">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11h-2Z"/></svg>
          </button>
          <div class="record-meta">
            <p class="record-title">${micLabel}</p>
            <p class="record-hint">Or type below. Coverage checklist helps us know when this item is done.</p>
          </div>
        </div>
        <label class="field" for="transcript">
          <span class="sr-only" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)">Your answer</span>
          <textarea class="transcript" id="transcript" placeholder="Your answer appears here…">${escapeHtml(state.transcript)}</textarea>
        </label>
        <ul class="coverage" aria-label="Coverage checklist">
          ${script.coverage
            .map((c) => `<li data-hit="${hits.includes(c)}">${escapeHtml(c)}</li>`)
            .join("")}
        </ul>
      </div>
    </div>
    <div class="actions btn-row">
      <button type="button" class="btn btn-secondary" id="done-item">Done with this ${script.kind === "role" ? "role" : "project"}</button>
      <button type="button" class="btn btn-primary" id="next-followup">${turn >= totalQ ? "Next item" : "Next follow-up"}</button>
    </div>`;

  document.getElementById("mic-btn").addEventListener("click", toggleMic);
  document.getElementById("transcript").addEventListener("input", (e) => {
    state.transcript = e.target.value;
  });
  document.getElementById("next-followup").addEventListener("click", () => advanceInterview(false));
  document.getElementById("done-item").addEventListener("click", () => advanceInterview(true));
}

function toggleMic() {
  if (state.micDenied) {
    showError(
      "Microphone permission was denied. Type your answer in the box — voice is preferred, but text works.",
    );
    return;
  }
  state.recording = !state.recording;
  state.error = null;
  if (!state.recording) {
    const { id, script } = currentInterview();
    const mock = script.mockTranscripts[state.questionIndex] || "That's all for now.";
    state.transcript = mock;
    const hits = new Set(state.coverageHits[id] || []);
    const idx = Math.min(state.questionIndex, script.coverage.length - 1);
    hits.add(script.coverage[idx]);
    if (state.questionIndex >= 1) hits.add(script.coverage[Math.min(1, script.coverage.length - 1)]);
    state.coverageHits[id] = [...hits];
  }
  render();
}

function advanceInterview(forceDone) {
  const { id, script } = currentInterview();
  if (!state.transcript.trim() && !forceDone) {
    showError("Add a short answer (record or type) before continuing.");
    return;
  }

  const hits = new Set(state.coverageHits[id] || []);
  if (state.transcript.trim()) {
    const idx = Math.min(state.questionIndex, script.coverage.length - 1);
    hits.add(script.coverage[idx]);
  }
  state.coverageHits[id] = [...hits];

  const lastQ = state.questionIndex >= script.questions.length - 1;
  if (forceDone || lastQ) {
    state.interviewIndex += 1;
    state.questionIndex = 0;
    state.transcript = "";
    state.recording = false;
    if (state.interviewIndex >= state.interviewQueue.length) {
      setStep("review");
      return;
    }
    setStep("interview");
    return;
  }

  state.questionIndex += 1;
  state.transcript = "";
  state.recording = false;
  state.error = null;
  render();
}

function renderReview() {
  const p = state.profile;
  pane().innerHTML = `
    <h1 class="headline">Review your profile</h1>
    <p class="helper">Correct anything we got wrong. Skills are stored from your resume — we don’t interview them.</p>
    ${alertHtml()}
    <section class="section">
      <div class="section-head"><h2 class="section-title">Basics</h2></div>
      <div class="field-grid two">
        <div class="field"><label for="name">Full name</label><input id="name" value="${escapeHtml(p.name)}" /></div>
        <div class="field"><label for="email">Email</label><input id="email" type="email" value="${escapeHtml(p.email)}" /></div>
        <div class="field"><label for="location">Location</label><input id="location" value="${escapeHtml(p.location)}" /></div>
        <div class="field"><label for="links">Links</label><input id="links" value="${escapeHtml(p.links)}" /></div>
      </div>
    </section>
    <section class="section">
      <div class="section-head"><h2 class="section-title">Experience</h2></div>
      <div class="card-list" id="exp-list">
        ${p.experiences
          .map(
            (e, i) => `
          <div class="edit-card" data-i="${i}">
            <p class="edit-card-title">${escapeHtml(e.title)} · ${escapeHtml(e.company)}</p>
            <p class="edit-card-sub">${escapeHtml(e.dates)}</p>
            <div class="field"><label for="exp-sum-${i}">Summary</label>
              <textarea id="exp-sum-${i}">${escapeHtml(e.summary)}</textarea>
            </div>
          </div>`,
          )
          .join("")}
      </div>
    </section>
    <section class="section">
      <div class="section-head"><h2 class="section-title">Projects</h2></div>
      <div class="card-list">
        ${p.projects
          .map(
            (e, i) => `
          <div class="edit-card">
            <p class="edit-card-title">${escapeHtml(e.title)}</p>
            <p class="edit-card-sub">${escapeHtml(e.dates)}</p>
            <div class="field"><label for="proj-sum-${i}">Summary</label>
              <textarea id="proj-sum-${i}">${escapeHtml(e.summary)}</textarea>
            </div>
          </div>`,
          )
          .join("")}
      </div>
    </section>
    <section class="section">
      <div class="section-head"><h2 class="section-title">Skills</h2></div>
      <div class="skill-wrap">
        ${p.skills.map((s) => `<span class="skill">${escapeHtml(s)}</span>`).join("")}
      </div>
      <p class="skill-note">Extracted from your resume · not interviewed</p>
    </section>
    <div class="actions">
      <button type="button" class="btn btn-primary" id="save-review">Looks good — continue</button>
    </div>`;

  document.getElementById("save-review").addEventListener("click", () => {
    state.profile.name = document.getElementById("name").value.trim() || state.profile.name;
    state.profile.email = document.getElementById("email").value.trim() || state.profile.email;
    state.profile.location = document.getElementById("location").value.trim();
    state.profile.links = document.getElementById("links").value.trim();
    state.profile.experiences.forEach((e, i) => {
      const el = document.getElementById(`exp-sum-${i}`);
      if (el) e.summary = el.value.trim();
    });
    state.profile.projects.forEach((e, i) => {
      const el = document.getElementById(`proj-sum-${i}`);
      if (el) e.summary = el.value.trim();
    });
    setStep("ready");
  });
}

function renderReady() {
  pane().innerHTML = `
    <div class="ready-mark" aria-hidden="true"><span>u</span><span class="plus">+</span></div>
    <h1 class="headline">Here's your profile — ready to tailor</h1>
    <p class="helper">Onboarding is complete. Your career profile is the source of truth for every tailored resume from here on.</p>
    <div class="summary-strip">
      <div class="stat"><p class="stat-n">${state.profile.experiences.length}</p><p class="stat-l">Roles interviewed</p></div>
      <div class="stat"><p class="stat-n">${state.profile.projects.length}</p><p class="stat-l">Projects interviewed</p></div>
      <div class="stat"><p class="stat-n">${state.profile.skills.length}</p><p class="stat-l">Skills stored</p></div>
    </div>
    <div class="alert alert-success" role="status" data-visible="true">Hard gate cleared — you can enter Tailor.</div>
    <div class="actions">
      <button type="button" class="btn btn-primary" id="go-tailor">Start tailoring</button>
      <button type="button" class="btn btn-ghost" id="back-review">Edit profile again</button>
    </div>`;

  document.getElementById("go-tailor").addEventListener("click", () => {
    const existing = pane().querySelector(".actions");
    let banner = pane().querySelector(".proto-end");
    if (!banner) {
      banner = document.createElement("div");
      banner.className = "alert alert-info proto-end";
      banner.dataset.visible = "true";
      banner.setAttribute("role", "status");
      existing.before(banner);
    }
    banner.textContent =
      "Prototype end — Tailor screen would open here (not built in this HTML).";
  });
  document.getElementById("back-review").addEventListener("click", () => setStep("review"));
}

function render() {
  const el = pane();
  el.dataset.anim = "swap";
  void el.offsetWidth;
  switch (state.step) {
    case "upload":
      renderUpload();
      break;
    case "parsing":
      renderParsing();
      break;
    case "interview":
      renderInterview();
      break;
    case "review":
      renderReview();
      break;
    case "ready":
      renderReady();
      break;
    default:
      renderUpload();
  }
}

function goBack() {
  if (state.step === "upload" || state.step === "ready") return;
  if (state.step === "parsing") {
    clearInterval(state.parseTimer);
    state.parseTimer = null;
    setStep("upload");
    return;
  }
  if (state.step === "interview") {
    if (state.questionIndex > 0) {
      state.questionIndex -= 1;
      state.transcript = "";
      render();
      return;
    }
    if (state.interviewIndex > 0) {
      state.interviewIndex -= 1;
      const prev = INTERVIEW_SCRIPT[state.interviewQueue[state.interviewIndex]];
      state.questionIndex = prev.questions.length - 1;
      state.transcript = "";
      render();
      return;
    }
    setStep("upload");
    return;
  }
  if (state.step === "review") {
    state.interviewIndex = state.interviewQueue.length - 1;
    const last = INTERVIEW_SCRIPT[state.interviewQueue[state.interviewIndex]];
    state.questionIndex = last.questions.length - 1;
    setStep("interview");
    return;
  }
}

function resetFlow() {
  clearInterval(state.parseTimer);
  Object.assign(state, {
    step: "upload",
    file: null,
    error: null,
    info: null,
    parseTick: 0,
    parseTimer: null,
    forceParseError: false,
    micDenied: false,
    recording: false,
    interviewIndex: 0,
    questionIndex: 0,
    coverageHits: {},
    transcript: "",
    profile: clone(MOCK_PROFILE),
  });
  setStep("upload");
}

function bindDemo() {
  document.querySelectorAll("[data-demo]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const demo = btn.dataset.demo;
      if (demo === "reset") {
        resetFlow();
        return;
      }
      if (demo === "wrong-type") {
        setStep("upload");
        acceptFile({ name: "resume.docx", size: 120000, type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
        return;
      }
      if (demo === "oversize") {
        setStep("upload");
        acceptFile({ name: "huge-resume.pdf", size: 12 * 1024 * 1024, type: "application/pdf", __forcePdf: true });
        return;
      }
      if (demo === "parse-error") {
        state.file = { name: "scanned-resume.pdf", size: 800000 };
        state.forceParseError = true;
        state.parseTick = 1;
        clearInterval(state.parseTimer);
        setStep("parsing");
        return;
      }
      if (demo === "mic-denied") {
        if (state.step !== "interview") {
          state.file = { name: "favour-resume.pdf", size: 245760 };
          state.interviewIndex = 0;
          state.questionIndex = 0;
          state.transcript = "";
          setStep("interview");
        }
        state.micDenied = true;
        state.recording = false;
        showError(
          "Microphone permission was denied. Type your answer in the box — voice is preferred, but text works.",
        );
      }
    });
  });
}

backBtn().addEventListener("click", goBack);
bindDemo();
setStep("upload");
