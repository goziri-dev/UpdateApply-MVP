const COPY = {
  signin: {
    headline: "Hello again",
    sub: "Sign in to continue",
    primary: "Sign in",
    primaryLoading: "Signing in…",
    switchPrefix: "Don’t have an account?",
    switchAction: "Sign up",
    passwordAutocomplete: "current-password",
    showReset: true,
  },
  signup: {
    headline: "Create your account",
    sub: "Sign up to start tailoring",
    primary: "Sign up",
    primaryLoading: "Creating account…",
    switchPrefix: "Already have an account?",
    switchAction: "Sign in",
    passwordAutocomplete: "new-password",
    showReset: false,
  },
};

let mode = "signin";
let loadingTarget = null;

function setMode(next) {
  mode = next;
  const c = COPY[mode];
  document.getElementById("headline").textContent = c.headline;
  document.getElementById("sub").textContent = c.sub;
  document.querySelector("#primary-cta .label-idle").textContent = c.primary;
  document.querySelector("#primary-cta .label-loading").textContent = c.primaryLoading;
  document.getElementById("password").autocomplete = c.passwordAutocomplete;
  document.getElementById("mode-switch").innerHTML =
    `${c.switchPrefix} <button type="button" class="text-link" id="toggle-mode">${c.switchAction}</button>`;
  document.getElementById("toggle-mode").addEventListener("click", () => {
    setMode(mode === "signin" ? "signup" : "signin");
  });
  document
    .querySelector(".field-password")
    .setAttribute("data-signup", String(!c.showReset));
  showError(false);
  clearLoading();
}

function setLoading(btn, loading) {
  if (loading) {
    clearLoading();
    loadingTarget = btn;
    btn.classList.add("is-loading");
    btn.disabled = true;
    const idle = btn.querySelector(".label-idle");
    const loadingEl = btn.querySelector(".label-loading");
    if (idle) idle.hidden = true;
    if (loadingEl) loadingEl.hidden = false;
  } else {
    clearLoading();
  }
}

function clearLoading() {
  document.querySelectorAll(".btn").forEach((btn) => {
    btn.classList.remove("is-loading");
    btn.disabled = false;
    const idle = btn.querySelector(".label-idle");
    const loadingEl = btn.querySelector(".label-loading");
    if (idle) idle.hidden = false;
    if (loadingEl) loadingEl.hidden = true;
  });
  loadingTarget = null;
}

function showError(visible) {
  document.getElementById("auth-error").dataset.visible = String(visible);
}

function simulateAction(btn) {
  setLoading(btn, true);
  window.setTimeout(() => {
    clearLoading();
    showError(true);
  }, 1100);
}

document.getElementById("auth-form").addEventListener("submit", (e) => {
  e.preventDefault();
  simulateAction(document.getElementById("primary-cta"));
});

document.querySelectorAll(".btn-oauth").forEach((btn) => {
  btn.addEventListener("click", () => simulateAction(btn));
});

document.getElementById("reset-link").addEventListener("click", (e) => {
  e.preventDefault();
});

document.querySelector("[data-demo='error']").addEventListener("click", () => {
  const el = document.getElementById("auth-error");
  showError(el.dataset.visible !== "true");
});

document.querySelector("[data-demo='loading']").addEventListener("click", () => {
  const primary = document.getElementById("primary-cta");
  if (primary.classList.contains("is-loading") || loadingTarget) {
    clearLoading();
  } else {
    setLoading(primary, true);
  }
});

document.getElementById("toggle-mode").addEventListener("click", () => {
  setMode(mode === "signin" ? "signup" : "signin");
});
