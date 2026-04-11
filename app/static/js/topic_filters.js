// topic_filters.js
// Minimal progressive enhancement for filter controls.
// The filter bar works without JS via native form submission.
// This script only adds a small UX improvement: auto-submit on select change
// is already handled inline with onchange="this.form.submit()" in the template.
// This file is kept as a placeholder for any future lightweight enhancements.

document.addEventListener("DOMContentLoaded", () => {
  // Highlight active filter selections
  document.querySelectorAll(".filter-select").forEach((sel) => {
    if (sel.value && sel.value !== "") {
      sel.closest(".filter-group")?.classList.add("filter-active");
    }
  });
});
