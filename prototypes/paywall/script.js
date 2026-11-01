(() => {
  const state = {
    view: "tailor",
    credits: 1,
    softDismissed: false,
    edge: "none",
    checkoutTimer: null,
  };

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  const softBanner = $("#soft-banner");
  const balanceChip = $("#balance-chip");
  const balanceValue = $("#balance-value");
  const paywall = $("#paywall");
  const paywallMain = $("#paywall-main");
  const checkoutFake = $("#checkout-fake");
  const toast = $("#toast");
  const pageTailor = $("#page-tailor");
  const pagePlans = $("#page-plans");
  const plansError = $("#plans-error");
  const plansSuccess = $("#plans-success");
  const plansEmpty = $("#plans-empty");
  const plansLoading = $("#plans-loading");
  const plansContent = $("#plans-content");

  function setReviewerActive(attr, value) {
    $$(`[data-${attr}]`).forEach((btn) => {
      btn.classList.toggle("is-active", btn.getAttribute(`data-${attr}`) === value);
    });
  }

  function syncNav() {
    $("#nav-tailor")?.classList.toggle("is-active", state.view === "tailor");
    $("#nav-plans")?.classList.toggle("is-active", state.view === "plans");
    $$(".reviewer [data-view]").forEach((btn) => {
      btn.classList.toggle("is-active", btn.dataset.view === state.view);
    });
  }

  function renderBalance() {
    if (state.edge === "loading" && state.view === "plans") {
      balanceChip.dataset.state = "loading";
      balanceValue.textContent = "";
      return;
    }

    if (state.credits <= 0) {
      balanceChip.dataset.state = "empty";
      balanceValue.textContent = "0 credits";
    } else {
      balanceChip.dataset.state = "ok";
      balanceValue.textContent =
        state.credits === 1 ? "1 credit" : `${state.credits} credits`;
    }
  }

  function renderSoftBanner() {
    const show =
      state.view === "tailor" &&
      state.credits === 1 &&
      !state.softDismissed &&
      state.edge !== "loading";
    softBanner.dataset.visible = show ? "true" : "false";
  }

  function renderView() {
    pageTailor.hidden = state.view !== "tailor";
    pagePlans.hidden = state.view !== "plans";
    syncNav();
  }

  function renderEdge() {
    const onPlans = state.view === "plans";
    const loading = onPlans && state.edge === "loading";
    const empty = onPlans && state.edge === "empty";
    const error = onPlans && state.edge === "error";
    const success = onPlans && state.edge === "success";

    plansLoading.dataset.visible = loading ? "true" : "false";
    plansEmpty.dataset.visible = empty ? "true" : "false";
    plansContent.hidden = loading || empty;
    plansError.dataset.visible = error ? "true" : "false";
    plansSuccess.dataset.visible = success ? "true" : "false";
  }

  function render() {
    renderView();
    renderBalance();
    renderSoftBanner();
    renderEdge();
  }

  function setView(view) {
    state.view = view;
    if (view === "plans" && state.edge === "none") {
      // keep edge
    }
    render();
  }

  function setCredits(n) {
    state.credits = n;
    state.softDismissed = false;
    if (n === 0) {
      openPaywall();
    } else {
      closePaywall();
    }
    render();
  }

  function setEdge(edge) {
    state.edge = edge;
    if (edge === "success") {
      state.credits = Math.max(state.credits, 1) + 9;
      setView("plans");
      showToast("Credits added. Ready to tailor.");
    } else if (edge === "empty" || edge === "loading" || edge === "error") {
      setView("plans");
    }
    setReviewerActive("edge", edge);
    render();
  }

  function openPaywall() {
    paywall.dataset.visible = "true";
    paywallMain.style.display = "";
    checkoutFake.dataset.visible = "false";
    document.body.style.overflow = "hidden";
  }

  function closePaywall() {
    paywall.dataset.visible = "false";
    document.body.style.overflow = "";
    if (state.checkoutTimer) {
      clearTimeout(state.checkoutTimer);
      state.checkoutTimer = null;
    }
  }

  function showToast(message) {
    toast.textContent = message;
    toast.dataset.visible = "true";
    window.clearTimeout(showToast._t);
    showToast._t = window.setTimeout(() => {
      toast.dataset.visible = "false";
    }, 3200);
  }

  function startCheckout(plan) {
    if (state.edge === "error") {
      setView("plans");
      plansError.dataset.visible = "true";
      closePaywall();
      return;
    }

    const fromPaywall = paywall.dataset.visible === "true";
    if (fromPaywall) {
      paywallMain.style.display = "none";
      checkoutFake.dataset.visible = "true";
    } else {
      showToast(`Opening Stripe Checkout (${plan})…`);
    }

    $$("[data-checkout]").forEach((btn) => {
      if (btn.dataset.checkout === plan) btn.classList.add("btn-busy");
      btn.disabled = true;
    });

    if (state.checkoutTimer) clearTimeout(state.checkoutTimer);
    state.checkoutTimer = window.setTimeout(() => {
      $$("[data-checkout]").forEach((btn) => {
        btn.classList.remove("btn-busy");
        btn.disabled = false;
      });

      const grant = plan === "payg" ? 1 : plan === "lite" ? 10 : 25;
      state.credits = grant;
      state.edge = "success";
      setReviewerActive("edge", "success");
      setReviewerActive("credits", String(state.credits === 1 ? 1 : state.credits === 0 ? 0 : 12));
      // sync credits toggles loosely
      $$(".reviewer [data-credits]").forEach((btn) => btn.classList.remove("is-active"));

      closePaywall();
      setView("plans");
      plansSuccess.dataset.visible = "true";
      plansError.dataset.visible = "false";
      showToast("Credits added. Ready to tailor.");
      render();
    }, 900);
  }

  function tryTailor() {
    if (state.credits <= 0) {
      openPaywall();
      return;
    }
    state.credits -= 1;
    state.softDismissed = false;
    if (state.credits === 1) {
      setReviewerActive("credits", "1");
    } else if (state.credits === 0) {
      setReviewerActive("credits", "0");
      openPaywall();
    }
    showToast(
      state.credits > 0
        ? `Tailored. ${state.credits} credit${state.credits === 1 ? "" : "s"} left.`
        : "Out of credits."
    );
    render();
  }

  // Events
  $$("[data-view]").forEach((el) => {
    el.addEventListener("click", () => setView(el.dataset.view));
  });

  $$(".reviewer [data-credits]").forEach((btn) => {
    btn.addEventListener("click", () => {
      setReviewerActive("credits", btn.dataset.credits);
      setCredits(Number(btn.dataset.credits));
    });
  });

  $$(".reviewer [data-edge]").forEach((btn) => {
    btn.addEventListener("click", () => setEdge(btn.dataset.edge));
  });

  $("#soft-cta")?.addEventListener("click", () => {
    setView("plans");
  });

  $("#soft-dismiss")?.addEventListener("click", () => {
    state.softDismissed = true;
    renderSoftBanner();
  });

  $("#btn-tailor")?.addEventListener("click", tryTailor);

  $("#paywall-close")?.addEventListener("click", closePaywall);
  $("#maybe-later")?.addEventListener("click", closePaywall);

  paywall.addEventListener("click", (e) => {
    if (e.target === paywall) closePaywall();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closePaywall();
  });

  $$("[data-checkout]").forEach((btn) => {
    btn.addEventListener("click", () => startCheckout(btn.dataset.checkout));
  });

  $$("[data-stay-free]").forEach((btn) => {
    btn.addEventListener("click", () => {
      setView("tailor");
      showToast("Staying on Free — browse anytime.");
    });
  });

  $("#retry-error")?.addEventListener("click", () => {
    state.edge = "none";
    setReviewerActive("edge", "none");
    plansError.dataset.visible = "false";
  });

  $("#btn-portal")?.addEventListener("click", () => {
    showToast("Opening Stripe Customer Portal… (fake)");
  });

  $("#empty-scroll")?.addEventListener("click", () => {
    state.edge = "none";
    setReviewerActive("edge", "none");
    render();
    $("#plan-rail")?.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  const rail = $("#plan-rail");
  $("#rail-prev")?.addEventListener("click", () => {
    rail?.scrollBy({ left: -280, behavior: "smooth" });
  });
  $("#rail-next")?.addEventListener("click", () => {
    rail?.scrollBy({ left: 280, behavior: "smooth" });
  });

  render();
})();
