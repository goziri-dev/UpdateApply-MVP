(function () {
  var form = document.getElementById("waitlist");
  var emailInput = document.getElementById("email");
  var submitBtn = document.getElementById("submit");
  var label = submitBtn.querySelector(".btn-label");
  var spinner = submitBtn.querySelector(".spinner");
  var fields = document.getElementById("form-fields");
  var alertBox = document.getElementById("form-alert");
  var confirmBox = document.getElementById("form-confirm");
  var confirmTitle = document.getElementById("confirm-title");
  var confirmEmail = document.getElementById("confirm-email");
  var confirmExtra = document.getElementById("confirm-extra");
  var resetBtn = document.getElementById("reset");
  var seen = Object.create(null);
  var loadingTimer = null;

  var LONG_EMAIL =
    "a.very.long.address.that.should.truncate.inside.the.confirmation@example.com";

  function clearTimer() {
    if (loadingTimer) {
      window.clearTimeout(loadingTimer);
      loadingTimer = null;
    }
  }

  function setLoading(on) {
    submitBtn.disabled = on;
    emailInput.disabled = on;
    submitBtn.setAttribute("aria-busy", on ? "true" : "false");
    label.textContent = on ? "Joining…" : "Join the waitlist";
    spinner.hidden = !on;
  }

  function showAlert(message) {
    confirmBox.hidden = true;
    fields.hidden = false;
    alertBox.hidden = false;
    alertBox.textContent = message;
    emailInput.setAttribute("aria-invalid", "true");
  }

  function clearAlert() {
    alertBox.hidden = true;
    alertBox.textContent = "";
    emailInput.removeAttribute("aria-invalid");
  }

  function showForm() {
    clearTimer();
    setLoading(false);
    clearAlert();
    confirmBox.hidden = true;
    fields.hidden = false;
    emailInput.disabled = false;
  }

  function showConfirm(kind, email) {
    clearTimer();
    setLoading(false);
    clearAlert();
    fields.hidden = true;
    confirmBox.hidden = false;
    confirmEmail.textContent = email;
    confirmEmail.title = email;
    if (kind === "duplicate") {
      confirmTitle.textContent = "You’re already on the list.";
      confirmExtra.textContent =
        "This still doesn’t open the app.";
    } else {
      confirmTitle.textContent = "You’re on the list.";
      confirmExtra.textContent = "This does not open the app.";
    }
  }

  function remember(email) {
    seen[email] = true;
  }

  function submitEmail(raw) {
    var email = raw.trim().toLowerCase();
    clearAlert();

    if (!email) {
      showAlert("Enter your email to join the waitlist.");
      emailInput.focus();
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 254) {
      showAlert("That doesn’t look like an email we can save.");
      emailInput.focus();
      return;
    }

    setLoading(true);
    loadingTimer = window.setTimeout(function () {
      loadingTimer = null;
      setLoading(false);
      if (email.indexOf("fail@") === 0) {
        showAlert("We couldn’t save that just now. Try again in a moment.");
        emailInput.focus();
        return;
      }
      if (seen[email]) {
        showConfirm("duplicate", email);
        return;
      }
      remember(email);
      showConfirm("success", email);
    }, 700);
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (submitBtn.disabled) return;
    submitEmail(emailInput.value);
  });

  resetBtn.addEventListener("click", function () {
    emailInput.value = "";
    showForm();
    emailInput.focus();
  });

  document.querySelectorAll("[data-preview]").forEach(function (button) {
    button.addEventListener("click", function () {
      var mode = button.getAttribute("data-preview");
      if (mode === "idle") {
        emailInput.value = "";
        showForm();
        return;
      }
      if (mode === "invalid") {
        emailInput.value = "not-an-email";
        showForm();
        showAlert("That doesn’t look like an email we can save.");
        return;
      }
      if (mode === "loading") {
        emailInput.value = "you@example.com";
        showForm();
        setLoading(true);
        return;
      }
      if (mode === "error") {
        emailInput.value = "fail@updateapply.test";
        showForm();
        showAlert("We couldn’t save that just now. Try again in a moment.");
        return;
      }
      if (mode === "success") {
        showConfirm("success", "you@example.com");
        return;
      }
      if (mode === "duplicate") {
        showConfirm("duplicate", "you@example.com");
        return;
      }
      if (mode === "long") {
        showConfirm("success", LONG_EMAIL);
      }
    });
  });

  document.querySelectorAll('a[href="#waitlist"]').forEach(function (link) {
    link.addEventListener("click", function () {
      window.setTimeout(function () {
        if (!fields.hidden) emailInput.focus();
      }, 280);
    });
  });
})();
