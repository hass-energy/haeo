/**
 * Guide slideshow component for HAEO documentation.
 *
 * Provides prev/next navigation through guide screenshots,
 * with automatic light/dark theme switching based on the
 * Material for MkDocs color scheme toggle.
 */

/**
 * Get the current theme mode from Material for MkDocs.
 * @returns {"light" | "dark"}
 */
function getThemeMode() {
  const scheme = document.body.getAttribute("data-md-color-scheme");
  return scheme === "slate" ? "dark" : "light";
}

/**
 * Update the visible image in a slide based on the current theme.
 * @param {HTMLElement} slide
 */
function updateSlideTheme(slide) {
  const mode = getThemeMode();
  const img = slide.querySelector(".guide-slide-img");
  if (!img) return;

  const src = mode === "dark" ? slide.dataset.darkSrc : slide.dataset.lightSrc;
  // Fall back to the other mode if preferred isn't available
  const fallback =
    mode === "dark" ? slide.dataset.lightSrc : slide.dataset.darkSrc;
  img.src = src || fallback || "";
}

/**
 * Initialize a single slideshow element.
 * @param {HTMLElement} slideshow
 */
function initSlideshow(slideshow) {
  const slides = slideshow.querySelectorAll(".guide-slide");
  const total = slides.length;
  if (total === 0) return;

  let current = 0;

  const counter = slideshow.querySelector(".guide-counter");
  const label = slideshow.querySelector(".guide-label");
  const prevBtn = slideshow.querySelector(".guide-prev");
  const nextBtn = slideshow.querySelector(".guide-next");

  function show(index) {
    // Clamp
    if (index < 0) index = 0;
    if (index >= total) index = total - 1;
    current = index;

    slides.forEach((slide, i) => {
      if (i === current) {
        slide.setAttribute("data-active", "true");
        updateSlideTheme(slide);
      } else {
        slide.removeAttribute("data-active");
      }
    });

    if (counter) counter.textContent = `${current + 1} / ${total}`;
    if (label) label.textContent = slides[current].dataset.label || "";
    if (prevBtn) prevBtn.disabled = current === 0;
    if (nextBtn) nextBtn.disabled = current === total - 1;

    // Preload adjacent slides
    if (current > 0) updateSlideTheme(slides[current - 1]);
    if (current < total - 1) updateSlideTheme(slides[current + 1]);
  }

  // Navigation
  if (prevBtn) prevBtn.addEventListener("click", () => show(current - 1));
  if (nextBtn) nextBtn.addEventListener("click", () => show(current + 1));

  // Keyboard navigation when focused
  slideshow.setAttribute("tabindex", "0");
  slideshow.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      show(current - 1);
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      show(current + 1);
    }
  });

  // Show first slide with correct theme
  show(0);

  // Watch for theme changes
  const observer = new MutationObserver(() => {
    // Update the currently visible slide's image
    updateSlideTheme(slides[current]);
  });
  observer.observe(document.body, {
    attributes: true,
    attributeFilter: ["data-md-color-scheme"],
  });
}

// Initialize on page load (Material for MkDocs instant navigation)
document$.subscribe(({ body }) => {
  body.querySelectorAll(".guide-slideshow").forEach(initSlideshow);
});
