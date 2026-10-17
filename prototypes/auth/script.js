const PROVIDERS = [
  {
    id: "google",
    label: "Continue with Google",
    className: "provider-google",
    icon: `<svg class="icon" viewBox="0 0 18 18" aria-hidden="true"><path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z"/><path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z"/><path fill="#FBBC05" d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z"/><path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z"/></svg>`,
  },
  {
    id: "github",
    label: "Continue with GitHub",
    className: "provider-github",
    icon: `<svg class="icon" viewBox="0 0 16 16" aria-hidden="true" fill="currentColor"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8Z"/></svg>`,
  },
  {
    id: "notion",
    label: "Continue with Notion",
    className: "provider-notion",
    icon: `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.98-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.373.466zm.793 3.22v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.167V6.354c0-.606-.233-.933-.748-.887l-15.177.887c-.56.046-.747.327-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952l1.45.327s0 .84-1.168.84l-3.22.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.14c-.093-.514.28-.887.747-.933zM1.936 1.035l13.31-.98c1.634-.14 2.055-.047 3.082.7l4.249 2.986c.7.513.934.747.934 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.047-1.448-.093-1.962-.747l-3.129-4.06c-.56-.747-.793-1.306-.793-1.96V2.667c0-.839.374-1.54 1.447-1.632z"/></svg>`,
  },
];

function providerButton(provider) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = `provider ${provider.className}`;
  btn.dataset.provider = provider.id;
  btn.innerHTML = `${provider.icon}<span class="label-idle">${provider.label}</span><span class="spinner" aria-hidden="true"></span><span class="label-loading" hidden>Connecting…</span>`;
  btn.addEventListener("click", () => startOAuth(btn));
  return btn;
}

function mountProviders() {
  document.querySelectorAll(".providers").forEach((root) => {
    root.replaceChildren(...PROVIDERS.map(providerButton));
  });
}

function setTab(mode) {
  const signin = mode === "signin";
  document.getElementById("tab-signin").setAttribute("aria-selected", String(signin));
  document.getElementById("tab-signup").setAttribute("aria-selected", String(!signin));
  document.getElementById("panel-signin").dataset.active = String(signin);
  document.getElementById("panel-signup").dataset.active = String(!signin);
}

function startOAuth(btn) {
  clearLoading();
  btn.classList.add("is-loading");
  btn.disabled = true;
  const idle = btn.querySelector(".label-idle");
  const loading = btn.querySelector(".label-loading");
  idle.hidden = true;
  loading.hidden = false;
  window.setTimeout(() => {
    clearLoading();
    showError(true);
  }, 1100);
}

function clearLoading() {
  document.querySelectorAll(".provider").forEach((btn) => {
    btn.classList.remove("is-loading");
    btn.disabled = false;
    const idle = btn.querySelector(".label-idle");
    const loading = btn.querySelector(".label-loading");
    if (idle) idle.hidden = false;
    if (loading) loading.hidden = true;
  });
}

function showError(visible) {
  const el = document.getElementById("auth-error");
  el.dataset.visible = String(visible);
}

document.getElementById("tab-signin").addEventListener("click", () => setTab("signin"));
document.getElementById("tab-signup").addEventListener("click", () => setTab("signup"));

document.querySelector("[data-demo='error']").addEventListener("click", () => {
  const el = document.getElementById("auth-error");
  showError(el.dataset.visible !== "true");
});

document.querySelector("[data-demo='loading']").addEventListener("click", () => {
  const first = document.querySelector("#panel-signin .provider");
  if (first.classList.contains("is-loading")) {
    clearLoading();
  } else {
    startOAuth(first);
  }
});

document.querySelector("[data-demo='session']").addEventListener("click", () => {
  const empty = document.getElementById("linked-empty");
  const email = document.getElementById("email-sample");
  const showEmail = email.hidden;
  email.hidden = !showEmail;
  empty.hidden = showEmail;
});

mountProviders();
