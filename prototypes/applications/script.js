(() => {
  const app = document.getElementById("app");
  const pages = {
    home: document.getElementById("page-home"),
    applications: document.getElementById("page-applications"),
    detail: document.getElementById("page-detail"),
    tailor: document.getElementById("page-tailor"),
  };

  const stateEmpty = document.getElementById("state-empty");
  const stateLoading = document.getElementById("state-loading");
  const stateList = document.getElementById("state-list");
  const listMeta = document.getElementById("list-meta");
  const appsError = document.getElementById("apps-error");

  const sheet = document.getElementById("draft-sheet");
  const backdrop = document.getElementById("sheet-backdrop");
  const toast = document.getElementById("toast");

  const detailTitle = document.getElementById("detail-title");
  const detailVersion = document.getElementById("detail-version");
  const detailMeta = document.getElementById("detail-meta");
  const detailJd = document.getElementById("detail-jd");
  const actApplied = document.getElementById("act-applied");

  const APPS = {
    "stripe-v2": {
      title: "Stripe · Product Designer",
      version: "Version 2 · Draft",
      meta: "Created 20 Oct 2026",
      jd: "We’re hiring a product designer to own Checkout growth surfaces and partner closely with research…",
      applied: false,
    },
    "stripe-v1": {
      title: "Stripe · Product Designer",
      version: "Version 1 · Applied",
      meta: "Applied 18 Oct 2026",
      jd: "Lead product design for Checkout — systems thinking, rapid prototyping, and clear narrative for merchants…",
      applied: true,
    },
    "notion-v1": {
      title:
        "Notion · Senior Software Engineer, Infrastructure Platforms that Power Collaborative Editing at Global Scale",
      version: "Version 1 · Draft",
      meta: "Created 22 Oct 2026",
      jd: "Build systems that power real-time collaboration. Strong distributed systems background preferred…",
      applied: false,
    },
    "linear-v1": {
      title: "Linear · Design Engineer",
      version: "Version 1 · Applied",
      meta: "Applied 10 Oct 2026",
      jd: "Ship UI with taste and precision. React, motion, and a love for craft over process theater…",
      applied: true,
    },
  };

  let toastTimer = null;

  function setNav(dest) {
    document.querySelectorAll(".nav-link").forEach((btn) => {
      const on = btn.dataset.dest === dest;
      btn.classList.toggle("is-active", on);
      if (on) btn.setAttribute("aria-current", "page");
      else btn.removeAttribute("aria-current");
    });
  }

  function showPage(name) {
    Object.entries(pages).forEach(([key, el]) => {
      if (!el) return;
      el.hidden = key !== name;
    });
    app.dataset.view = name;
    if (name === "detail") setNav("applications");
    else if (name === "home" || name === "applications" || name === "tailor") {
      setNav(name);
    }
  }

  function setListState(state) {
    // state: empty | list | loading | error
    app.dataset.state = state;
    const showEmpty = state === "empty";
    const showLoading = state === "loading";
    const showList = state === "list" || state === "error";
    stateEmpty.hidden = !showEmpty;
    stateLoading.hidden = !showLoading;
    stateList.hidden = !showList;
    // Subtle count only when there are rows — no tab-name page title
    if (listMeta) {
      listMeta.hidden = !(state === "list" || state === "error");
    }
    appsError.dataset.visible = state === "error" ? "true" : "false";
  }

  function openDetail(id) {
    const data = APPS[id] || APPS["stripe-v2"];
    detailTitle.textContent = data.title;
    detailVersion.textContent = data.version;
    detailMeta.textContent = data.meta;
    detailJd.textContent = data.jd;
    actApplied.textContent = data.applied ? "Applied" : "Mark as applied";
    actApplied.disabled = data.applied;
    showPage("detail");
    closeSheet();
  }

  function openSheet() {
    sheet.hidden = false;
    backdrop.hidden = false;
    // force reflow for transition
    void sheet.offsetWidth;
    sheet.dataset.open = "true";
    backdrop.dataset.open = "true";
  }

  function closeSheet() {
    sheet.dataset.open = "false";
    backdrop.dataset.open = "false";
    window.setTimeout(() => {
      if (sheet.dataset.open === "false") {
        sheet.hidden = true;
        backdrop.hidden = true;
      }
    }, 220);
  }

  function showToast(message) {
    toast.textContent = message;
    toast.hidden = false;
    if (toastTimer) window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      toast.hidden = true;
    }, 2200);
  }

  function goApplicationsList() {
    showPage("applications");
    setListState("list");
    closeSheet();
  }

  // Nav
  document.querySelectorAll("[data-dest]").forEach((el) => {
    el.addEventListener("click", () => {
      const dest = el.dataset.dest;
      if (dest === "applications") {
        showPage("applications");
        if (app.dataset.state === "empty" || app.dataset.state === "loading") {
          /* keep */
        } else {
          setListState(app.dataset.state === "error" ? "error" : "list");
        }
        closeSheet();
      } else if (dest === "home" || dest === "tailor") {
        showPage(dest);
        closeSheet();
      }
    });
  });

  // List rows
  stateList.querySelectorAll(".row[data-app]").forEach((row) => {
    const open = () => openDetail(row.dataset.app);
    row.addEventListener("click", open);
    row.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        open();
      }
    });
  });

  document.getElementById("detail-back").addEventListener("click", () => {
    goApplicationsList();
  });

  document.getElementById("act-download").addEventListener("click", () => {
    showToast("Download started (prototype)");
  });

  actApplied.addEventListener("click", () => {
    if (actApplied.disabled) return;
    actApplied.textContent = "Applied";
    actApplied.disabled = true;
    detailVersion.textContent = detailVersion.textContent.replace(
      "Draft",
      "Applied",
    );
    detailMeta.textContent = "Applied today";
    showToast("Marked as applied");
  });

  document.getElementById("act-retailor").addEventListener("click", () => {
    showPage("tailor");
  });

  document.getElementById("fake-tailor").addEventListener("click", () => {
    showPage("applications");
    setListState("list");
    openSheet();
  });

  document.getElementById("sheet-view").addEventListener("click", () => {
    goApplicationsList();
    openDetail("stripe-v2");
  });

  document.getElementById("sheet-dismiss").addEventListener("click", closeSheet);
  backdrop.addEventListener("click", closeSheet);

  document.getElementById("retry-load").addEventListener("click", () => {
    setListState("loading");
    window.setTimeout(() => setListState("list"), 700);
  });

  document.getElementById("open-master")?.addEventListener("click", () => {
    showToast("Master preview (prototype)");
  });

  // Demo dock
  document.querySelectorAll(".demo-dock [data-demo]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".demo-dock [data-demo]")
        .forEach((b) => b.classList.remove("is-on"));
      btn.classList.add("is-on");

      const demo = btn.dataset.demo;
      closeSheet();

      if (demo === "empty") {
        showPage("applications");
        setListState("empty");
      } else if (demo === "list") {
        showPage("applications");
        setListState("list");
      } else if (demo === "detail") {
        showPage("applications");
        setListState("list");
        openDetail("stripe-v2");
      } else if (demo === "draft") {
        showPage("applications");
        setListState("list");
        openSheet();
      } else if (demo === "loading") {
        showPage("applications");
        setListState("loading");
      } else if (demo === "error") {
        showPage("applications");
        setListState("error");
      }
    });
  });

  // Initial
  showPage("applications");
  setListState("list");
})();
