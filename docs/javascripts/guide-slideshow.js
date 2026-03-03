/**
 * Guide slideshow component for HAEO documentation.
 *
 * Provides prev/next navigation through guide screenshots,
 * with automatic light/dark theme switching based on the
 * Material for MkDocs color scheme toggle.
 *
 * Shows a loading spinner while images load, with a fixed-ratio
 * placeholder matching the screenshot viewport dimensions to
 * prevent layout shifts.
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
 * Get the image source URL for a slide based on theme mode.
 * @param {HTMLElement} slide
 * @param {string} mode - "light" or "dark"
 * @returns {string}
 */
function getSlideSrc(slide, mode) {
  const src = mode === "dark" ? slide.dataset.darkSrc : slide.dataset.lightSrc;
  const fallback = mode === "dark" ? slide.dataset.lightSrc : slide.dataset.darkSrc;
  return src || fallback || "";
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

  const slidesContainer = slideshow.querySelector(".guide-slides");
  const counter = slideshow.querySelector(".guide-counter");
  const label = slideshow.querySelector(".guide-label");
  const prevBtn = slideshow.querySelector(".guide-prev");
  const nextBtn = slideshow.querySelector(".guide-next");

  // Set aspect ratio from data attributes for the placeholder sizing
  const w = parseInt(slideshow.dataset.width, 10) || 1280;
  const h = parseInt(slideshow.dataset.height, 10) || 800;
  slidesContainer.style.aspectRatio = `${w} / ${h}`;

  function show(index) {
    // Clamp
    if (index < 0) index = 0;
    if (index >= total) index = total - 1;
    current = index;

    const targetSlide = slides[current];
    const targetImg = targetSlide.querySelector(".guide-slide-img");
    const targetSrc = getSlideSrc(targetSlide, getThemeMode());

    // Switch active slide and show loading state
    slides.forEach((slide, i) => {
      if (i === current) {
        slide.setAttribute("data-active", "true");
      } else {
        slide.removeAttribute("data-active");
      }
    });

    // Update controls immediately
    if (counter) counter.textContent = `${current + 1} / ${total}`;
    if (label) label.textContent = targetSlide.dataset.label || "";
    if (prevBtn) prevBtn.disabled = current === 0;
    if (nextBtn) nextBtn.disabled = current === total - 1;

    // Load image - show spinner until ready
    if (targetImg) {
      targetImg.src = targetSrc;
      if (targetImg.complete && targetImg.naturalWidth > 0) {
        targetSlide.removeAttribute("data-loading");
      } else {
        targetSlide.setAttribute("data-loading", "");
        const done = () => {
          targetSlide.removeAttribute("data-loading");
          targetImg.onload = null;
          targetImg.onerror = null;
        };
        targetImg.onload = done;
        targetImg.onerror = done;
      }
    }
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

  // Show first slide
  show(0);

  // Watch for theme changes - reload current slide in new theme
  const observer = new MutationObserver(() => {
    show(current);
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
