/**
 * Guide slideshow component for HAEO documentation.
 *
 * Provides prev/next navigation through guide screenshots,
 * with automatic light/dark theme switching based on the
 * Material for MkDocs color scheme toggle.
 *
 * Images are preloaded on initialization to prevent flicker
 * when navigating between slides.
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
 * Preload all slide images for a given theme mode.
 * @param {NodeList} slides
 * @param {string} mode - "light" or "dark"
 */
function preloadAllSlides(slides, mode) {
  slides.forEach((slide) => {
    const url = getSlideSrc(slide, mode);
    if (url) {
      const img = new Image();
      img.src = url;
    }
  });
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

  // Preload all images for the current theme
  const mode = getThemeMode();
  preloadAllSlides(slides, mode);

  // Set the first slide's image immediately
  const firstImg = slides[0].querySelector(".guide-slide-img");
  if (firstImg) firstImg.src = getSlideSrc(slides[0], mode);

  function show(index) {
    // Clamp
    if (index < 0) index = 0;
    if (index >= total) index = total - 1;
    current = index;

    const targetSlide = slides[current];
    const targetImg = targetSlide.querySelector(".guide-slide-img");
    const targetSrc = getSlideSrc(targetSlide, getThemeMode());

    // Ensure the target image is loaded before switching
    function activate() {
      slides.forEach((slide, i) => {
        if (i === current) {
          slide.setAttribute("data-active", "true");
        } else {
          slide.removeAttribute("data-active");
        }
      });

      if (counter) counter.textContent = `${current + 1} / ${total}`;
      if (label) label.textContent = targetSlide.dataset.label || "";
      if (prevBtn) prevBtn.disabled = current === 0;
      if (nextBtn) nextBtn.disabled = current === total - 1;
    }

    if (targetImg) {
      targetImg.src = targetSrc;
      if (targetImg.complete && targetImg.naturalWidth > 0) {
        activate();
      } else {
        targetImg.onload = activate;
        targetImg.onerror = activate;
      }
    } else {
      activate();
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

  // Watch for theme changes
  const observer = new MutationObserver(() => {
    const newMode = getThemeMode();
    preloadAllSlides(slides, newMode);
    // Update current slide to new theme
    const img = slides[current].querySelector(".guide-slide-img");
    if (img) img.src = getSlideSrc(slides[current], newMode);
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
