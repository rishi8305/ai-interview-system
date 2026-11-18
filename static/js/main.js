/**
 * Main application scripts
 */

document.addEventListener("DOMContentLoaded", function () {
  // Initialize Bootstrap Tooltips
  const tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Auto-dismiss alert banners after 5 seconds
  const alerts = document.querySelectorAll(".alert-dismissible");
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = new bootstrap.Alert(alert);
      try {
        bsAlert.close();
      } catch (e) {}
    }, 5000);
  });

  // Dark/Light Mode Theme Toggle
  const themeToggle = document.getElementById("themeToggle");
  const currentTheme = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-bs-theme", currentTheme);

  if (themeToggle) {
    updateThemeIcon(themeToggle, currentTheme);
    themeToggle.addEventListener("click", function () {
      const activeTheme = document.documentElement.getAttribute("data-bs-theme");
      const newTheme = activeTheme === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-bs-theme", newTheme);
      localStorage.setItem("theme", newTheme);
      updateThemeIcon(themeToggle, newTheme);
    });
  }

  function updateThemeIcon(btn, theme) {
    const icon = btn.querySelector("i");
    if (icon) {
      if (theme === "dark") {
        icon.className = "bi bi-sun-fill text-warning";
      } else {
        icon.className = "bi bi-moon-stars-fill text-secondary";
      }
    }
  }
});
