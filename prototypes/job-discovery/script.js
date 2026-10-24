(() => {
  const app = document.getElementById("app");
  const pages = {
    home: document.getElementById("page-home"),
    jobs: document.getElementById("page-jobs"),
    applications: document.getElementById("page-applications"),
    settings: document.getElementById("page-settings"),
    "match-prefs": document.getElementById("page-match-prefs"),
    tailor: document.getElementById("page-tailor"),
  };

  const jobList = document.getElementById("job-list");
  const searchInput = document.getElementById("job-search");
  const locationFilter = document.getElementById("location-filter");
  const searchEmpty = document.getElementById("state-search-empty");
  const stateList = document.getElementById("state-list");
  const stateLoading = document.getElementById("state-loading");
  const stateNoPrefs = document.getElementById("state-no-prefs");
  const stateNoMatches = document.getElementById("state-no-matches");
  const jobsError = document.getElementById("jobs-error");
  const resultsMeta = document.getElementById("results-meta");
  const resultsTitle = document.getElementById("results-title");
  const toast = document.getElementById("toast");
  const titleList = document.getElementById("title-list");
  const settingsBtn = document.querySelector(".shell-settings");

  const JOBS = [
    {
      id: "stripe-pd",
      title: "Product Designer, Checkout",
      company: "Stripe",
      target: "Product Designer",
      locationKeys: ["remote", "uk", "ie"],
      office: "Dublin · London",
      remote: "Ireland · UK",
      reason:
        "Matched “Product Designer” · hybrid for UK/IE · closest to Checkout growth work on your profile",
      jd: "We’re hiring a product designer to own Checkout growth surfaces. Partner with research, ship experiments, and raise the bar on merchant-facing flows. 5+ years product design, strong systems thinking, and comfort with ambiguous growth metrics.",
    },
    {
      id: "notion-pd",
      title: "Product Designer",
      company: "Notion",
      target: "Product Designer",
      locationKeys: ["remote", "us"],
      office: "San Francisco",
      remote: "United States",
      reason:
        "Matched “Product Designer” · remote · closest to collaborative editor craft on your profile",
      jd: "Design end-to-end product experiences for Notion’s core editor. You’ll work with research and engineering on information architecture, interaction design, and visual systems that scale across platforms.",
    },
    {
      id: "linear-de",
      title: "Design Engineer",
      company: "Linear",
      target: "Design Engineer",
      locationKeys: ["remote", "uk", "ie"],
      office: "—",
      remote: "Europe",
      reason:
        "Matched “Design Engineer” · hybrid · closest to React + motion craft on your profile",
      jd: "Ship UI with taste and precision. React, motion, and a love for craft over process theater. You’ll own polished product surfaces from prototype to production CSS.",
    },
    {
      id: "figma-pd",
      title: "Senior Product Designer, Design Systems",
      company: "Figma",
      target: "Product Designer",
      locationKeys: ["uk"],
      office: "London",
      remote: "UK hybrid",
      reason:
        "Matched “Product Designer” · UK · closest to design-systems leadership on your profile",
      jd: "Lead product design for Figma’s design systems practice. Partner with engineers on tokens, components, and documentation that thousands of teams rely on daily.",
    },
    {
      id: "vercel-de",
      title: "Design Engineer, Dashboard",
      company: "Vercel",
      target: "Design Engineer",
      locationKeys: ["remote", "us"],
      office: "—",
      remote: "United States",
      reason:
        "Matched “Design Engineer” · remote · closest to developer-tooling UI on your profile",
      jd: "Build and refine the Vercel dashboard experience. Strong front-end skills, typography instincts, and comfort working in a high-velocity product org.",
    },
    {
      id: "intercom-lead",
      title: "Product Design Lead, Messenger",
      company: "Intercom",
      target: "Product Design Lead",
      locationKeys: ["ie", "remote"],
      office: "Dublin",
      remote: "Ireland",
      reason:
        "Matched “Product Design Lead” · IE · closest to messaging product leadership on your profile",
      jd: "Lead the product design practice for Messenger. Set direction, coach designers, and ship customer communication experiences used by thousands of support teams.",
    },
  ];

  let activeTarget = "all";
  let toastTimer = null;
  let demoMode = "list";
  let tailorFromJobs = true;

  function primaryTab(dest) {
    if (dest === "jobs" || dest === "tailor") return "jobs";
    if (dest === "applications") return "applications";
    if (dest === "home") return "home";
    return null; // settings / match-prefs — no primary tab
  }

  function setNav(dest) {
    const tab = primaryTab(dest);
    document.querySelectorAll(".nav-link").forEach((btn) => {
      const on = tab != null && btn.dataset.dest === tab;
      btn.classList.toggle("is-active", on);
      if (on) btn.setAttribute("aria-current", "page");
      else btn.removeAttribute("aria-current");
    });
    if (settingsBtn) {
      const settingsOn = dest === "settings" || dest === "match-prefs";
      settingsBtn.classList.toggle("is-active", settingsOn);
    }
  }

  function showPage(name) {
    Object.entries(pages).forEach(([key, el]) => {
      if (!el) return;
      el.hidden = key !== name;
    });
    app.dataset.view = name;
    setNav(name);
    if (name === "jobs" && demoMode === "list") {
      renderJobs();
    }
  }

  function filteredJobs() {
    const q = (searchInput.value || "").trim().toLowerCase();
    const loc = locationFilter.value;

    return JOBS.filter((job) => {
      if (activeTarget !== "all" && job.target !== activeTarget) return false;
      if (loc !== "all" && !job.locationKeys.includes(loc)) return false;
      if (!q) return true;
      const hay = `${job.title} ${job.company} ${job.target}`.toLowerCase();
      return hay.includes(q);
    });
  }

  function iconOffice() {
    return `<svg class="meta-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 20V6a2 2 0 0 1 2-2h5v16H4Zm9 0V10h5a2 2 0 0 1 2 2v8h-7Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>`;
  }

  function iconRemote() {
    return `<svg class="meta-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.6"/><path d="M4 12h16M12 4c2.5 2.8 2.5 13.2 0 16M12 4c-2.5 2.8-2.5 13.2 0 16" stroke="currentColor" stroke-width="1.4"/></svg>`;
  }

  function renderJobs() {
    const jobs = filteredJobs();
    const total = JOBS.length;
    resultsMeta.textContent =
      jobs.length === total
        ? `${jobs.length} showing · default cap`
        : `${jobs.length} of ${total} · filtered`;
    resultsTitle.textContent =
      activeTarget === "all" ? "Top matches" : activeTarget;

    document.getElementById("count-all").textContent = String(total);

    if (jobs.length === 0) {
      jobList.hidden = true;
      searchEmpty.hidden = false;
      return;
    }

    searchEmpty.hidden = true;
    jobList.hidden = false;
    jobList.innerHTML = jobs
      .map(
        (job) => `
      <article class="job-card" tabindex="0" role="button" data-job="${job.id}">
        <h3 class="job-title">${escapeHtml(job.title)}</h3>
        <p class="job-company">${escapeHtml(job.company)}</p>
        <div class="job-meta">
          <div class="meta-row">${iconOffice()}<span>${escapeHtml(job.office)}</span></div>
          <div class="meta-row">${iconRemote()}<span>${escapeHtml(job.remote)}</span></div>
        </div>
        <p class="job-reason">${escapeHtml(job.reason)}</p>
        <p class="job-cta">Open to tailor →</p>
      </article>`
      )
      .join("");
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function setJobsState(state) {
    demoMode = state;
    app.dataset.jobs = state;

    document.querySelectorAll(".demo-btn").forEach((btn) => {
      btn.classList.toggle("is-on", btn.dataset.demo === state);
    });

    stateLoading.hidden = state !== "loading";
    stateNoPrefs.hidden = state !== "no-prefs";
    stateNoMatches.hidden = state !== "no-matches";
    jobsError.dataset.visible = state === "error" ? "true" : "false";

    const showList = state === "list" || state === "search-empty";
    stateList.hidden = !showList;
    if (state === "loading") stateList.hidden = true;

    const toolbar = document.querySelector("#page-jobs .toolbar");
    const hero = document.querySelector("#page-jobs .hero");
    const hideChrome = state === "no-prefs" || state === "no-matches";
    if (toolbar) toolbar.hidden = hideChrome;
    if (hero) hero.hidden = hideChrome;

    if (state === "list") {
      searchInput.value = "";
      locationFilter.value = "all";
      activeTarget = "all";
      document.querySelectorAll(".side-item").forEach((btn) => {
        const on = btn.dataset.target === "all";
        btn.classList.toggle("is-on", on);
        btn.setAttribute("aria-pressed", on ? "true" : "false");
      });
      renderJobs();
    }

    if (state === "search-empty") {
      showPage("jobs");
      searchInput.value = "zzzz-no-hit";
      renderJobs();
      return;
    }

    showPage("jobs");
  }

  function openTailor(jobId) {
    const job = JOBS.find((j) => j.id === jobId);
    if (!job) return;
    tailorFromJobs = true;
    document.getElementById("tailor-heading").textContent =
      `${job.company} · ${job.title}`;
    document.getElementById("tailor-sub").textContent =
      "Stored description prefilled. Generate when you’re ready — this does not apply for you.";
    document.getElementById("tailor-company").value = job.company;
    document.getElementById("tailor-role").value = job.title;
    document.getElementById("tailor-jd").value = job.jd;
    document.getElementById("tailor-company").readOnly = true;
    document.getElementById("tailor-role").readOnly = true;
    document.getElementById("tailor-jd").readOnly = true;
    document.getElementById("tailor-back").innerHTML =
      '<span class="back-arrow" aria-hidden="true">←</span> Jobs For You';
    showPage("tailor");
  }

  function openBlankTailor() {
    tailorFromJobs = false;
    document.getElementById("tailor-heading").textContent = "Tailor resume";
    document.getElementById("tailor-sub").textContent =
      "Paste a job description. Generate when you’re ready.";
    document.getElementById("tailor-company").value = "";
    document.getElementById("tailor-role").value = "";
    document.getElementById("tailor-jd").value = "";
    document.getElementById("tailor-company").readOnly = false;
    document.getElementById("tailor-role").readOnly = false;
    document.getElementById("tailor-jd").readOnly = false;
    document.getElementById("tailor-back").innerHTML =
      '<span class="back-arrow" aria-hidden="true">←</span> Home';
    showPage("tailor");
  }

  function showToast(message) {
    toast.textContent = message;
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.hidden = true;
    }, 2800);
  }

  function goJobs() {
    if (demoMode === "search-empty") demoMode = "list";
    const keep =
      demoMode === "no-prefs" ||
      demoMode === "no-matches" ||
      demoMode === "error" ||
      demoMode === "loading";
    setJobsState(keep ? demoMode : "list");
  }

  // Navigation
  document.querySelectorAll("[data-dest]").forEach((el) => {
    el.addEventListener("click", () => {
      const dest = el.dataset.dest;
      if (dest === "jobs") {
        goJobs();
        return;
      }
      if (dest === "tailor-blank") {
        openBlankTailor();
        return;
      }
      showPage(dest);
    });
  });

  document.querySelectorAll(".side-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeTarget = btn.dataset.target;
      document.querySelectorAll(".side-item").forEach((b) => {
        const on = b === btn;
        b.classList.toggle("is-on", on);
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
      renderJobs();
    });
  });

  searchInput.addEventListener("input", () => {
    if (demoMode !== "list" && demoMode !== "search-empty") return;
    demoMode = "list";
    renderJobs();
  });

  locationFilter.addEventListener("change", () => {
    if (demoMode !== "list" && demoMode !== "search-empty") return;
    demoMode = "list";
    renderJobs();
  });

  document.getElementById("clear-filters").addEventListener("click", () => {
    searchInput.value = "";
    locationFilter.value = "all";
    activeTarget = "all";
    document.querySelectorAll(".side-item").forEach((btn) => {
      const on = btn.dataset.target === "all";
      btn.classList.toggle("is-on", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    demoMode = "list";
    renderJobs();
  });

  jobList.addEventListener("click", (e) => {
    const card = e.target.closest("[data-job]");
    if (!card) return;
    openTailor(card.dataset.job);
  });

  jobList.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const card = e.target.closest("[data-job]");
    if (!card) return;
    e.preventDefault();
    openTailor(card.dataset.job);
  });

  function leaveTailor() {
    if (tailorFromJobs) setJobsState("list");
    else showPage("home");
  }

  document.getElementById("tailor-back").addEventListener("click", leaveTailor);
  document.getElementById("tailor-cancel").addEventListener("click", leaveTailor);
  document.getElementById("run-tailor").addEventListener("click", () => {
    showToast("Prototype: would call POST /api/v1/tailor and open Applications.");
  });

  document.getElementById("retry-jobs").addEventListener("click", () => {
    setJobsState("loading");
    setTimeout(() => setJobsState("list"), 900);
  });

  document.querySelectorAll(".seg-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".seg-btn").forEach((b) => {
        b.classList.toggle("is-on", b === btn);
        b.setAttribute("aria-pressed", b === btn ? "true" : "false");
      });
    });
  });

  document.querySelectorAll("#seniority-row .filter-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.classList.toggle("is-on");
      btn.setAttribute(
        "aria-pressed",
        btn.classList.contains("is-on") ? "true" : "false"
      );
    });
  });

  titleList.addEventListener("click", (e) => {
    const remove = e.target.closest(".chip-remove");
    if (!remove) return;
    remove.closest(".title-chip")?.remove();
  });

  document.getElementById("add-title").addEventListener("click", () => {
    const li = document.createElement("li");
    li.className = "title-chip";
    li.innerHTML = `
      <input type="text" value="" placeholder="e.g. Staff Product Designer" aria-label="Preferred title" />
      <button type="button" class="chip-remove" aria-label="Remove title">×</button>`;
    titleList.appendChild(li);
    li.querySelector("input").focus();
  });

  document.getElementById("prefs-save").addEventListener("click", () => {
    const seniorityOn = document.querySelectorAll(
      "#seniority-row .filter-chip.is-on"
    ).length;
    const titles = [...titleList.querySelectorAll("input")].filter(
      (i) => i.value.trim()
    );
    if (!titles.length || !seniorityOn) {
      showToast("Add at least one title and pick a seniority band.");
      return;
    }
    showToast("Job preferences saved — Jobs For You will use this set.");
    setTimeout(() => setJobsState("list"), 400);
  });

  document.querySelectorAll(".demo-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      setJobsState(btn.dataset.demo);
    });
  });

  renderJobs();
  document.querySelector('.demo-btn[data-demo="list"]').classList.add("is-on");
})();
