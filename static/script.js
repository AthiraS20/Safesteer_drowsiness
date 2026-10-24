// static/script.js
document.addEventListener("DOMContentLoaded", () => {
  const fetchOpts = (method, body) => {
    const o = {
      method,
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin"
    };
    if (body) o.body = JSON.stringify(body);
    return o;
  };

  // LOGIN
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        email: document.getElementById("email").value.trim(),
        password: document.getElementById("password").value.trim()
      };

      try {
        const res = await fetch("/login", fetchOpts("POST", payload));
        const data = await res.json();
        if (data && data.success) {
          alert("✅ Login successful!");
          const redirect = data.redirect || (data.role === "admin" ? "/admin" : "/dashboard");
          window.location.href = redirect;
        } else {
          alert("❌ " + (data.message || "Login failed"));
        }
      } catch (err) {
        console.error(err);
        alert("⚠️ Server error during login");
      }
    });
  }

  // SIGNUP
  const signupForm = document.getElementById("signupForm");
  if (signupForm) {
    signupForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const password = document.getElementById("signupPassword").value.trim();
      const confirmPassword = document.getElementById("confirmPassword").value.trim();

      if (password !== confirmPassword) {
        alert("❌ Passwords do not match!");
        return;
      }

      const payload = {
        username: document.getElementById("name").value.trim(),
        email: document.getElementById("signupEmail").value.trim(),
        phone: document.getElementById("phone").value.trim(),
        vehicle_no: document.getElementById("vehicleNumber").value.trim(),
        password: password
      };

      if (!payload.username || !payload.email || !payload.phone || !payload.vehicle_no || !payload.password) {
        return alert("⚠️ Please fill all required fields.");
      }

      try {
        const res = await fetch("/signup", fetchOpts("POST", payload));
        const data = await res.json();
        if (data && data.success) {
          alert("✅ Account created successfully!");
          window.location.href = "/";
        } else {
          alert("❌ " + (data.message || "Signup failed"));
        }
      } catch (err) {
        console.error(err);
        alert("⚠️ Server error during signup");
      }
    });
  }

  // LOGOUT
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      await fetch("/logout", fetchOpts("POST", {}));
      alert("👋 You have been logged out.");
      window.location.href = "/";
    });
  }

  // MOBILE NAVIGATION TOGGLE
  const navToggle = document.getElementById("navToggle");
  const navLinks = document.getElementById("navLinks");
  if (navToggle && navLinks) {
    navToggle.addEventListener("click", (e) => {
      e.stopPropagation();
      const isOpen = navLinks.classList.toggle("open");
      navToggle.setAttribute("aria-expanded", isOpen);
      const icon = navToggle.querySelector("i");
      if (icon) {
        if (isOpen) {
          icon.className = "bx bx-x";
        } else {
          icon.className = "bx bx-menu";
        }
      }
    });

    // Close when clicking nav links
    navLinks.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        if (navLinks.classList.contains("open")) {
          navLinks.classList.remove("open");
          const icon = navToggle.querySelector("i");
          if (icon) icon.className = "bx bx-menu";
        }
      });
    });

    // Close when tapping outside
    document.addEventListener("click", (e) => {
      if (
        navLinks.classList.contains("open") &&
        !navLinks.contains(e.target) &&
        !navToggle.contains(e.target)
      ) {
        navLinks.classList.remove("open");
        const icon = navToggle.querySelector("i");
        if (icon) icon.className = "bx bx-menu";
      }
    });
  }
});
