/**
 * Resolve once the page has finished rendering, for screenshot capture.
 *
 * Rather than sleeping, this waits on the signals the page itself offers:
 * requests to Home Assistant being answered, custom elements becoming
 * defined, Lit elements' updateComplete, icons receiving their paths, images
 * on screen loading, and web fonts loading.
 * Finite animations and transitions are finished on the spot, as the
 * screenshot would show them, so their end handlers run without waiting out
 * their duration.
 *
 * Settling one thing can start another, such as an update that renders a new
 * image, or an image whose size makes a virtualized list lay itself out
 * again. So the page counts as settled only once an animation frame passes
 * with nothing outstanding and no change to the DOM, watched by a
 * MutationObserver on the document and every shadow root.
 *
 * Rejects naming what is still outstanding if the page has not settled by
 * the deadline, so a capture never silently shows a half-rendered page.
 */
async (deadlineMs) => {
  const deadline = performance.now() + deadlineMs;
  const frame = () => new Promise((resolve) => requestAnimationFrame(() => resolve()));

  // An IntersectionObserver applies the clipping of scroll containers, so an
  // image counts only if some of it shows. Lazy images scrolled out of sight
  // never load, and do not appear in the capture anyway.
  const showing = (images) =>
    new Promise((resolve) => {
      if (images.length === 0) {
        resolve([]);
        return;
      }
      const observer = new IntersectionObserver((entries) => {
        observer.disconnect();
        resolve(entries.filter((entry) => entry.isIntersecting).map((entry) => entry.target));
      });
      for (const image of images) observer.observe(image);
    });

  // Some work runs on timers and leaves the DOM untouched until it is done,
  // so it is checked for directly: ha-icon looking its path up, ripples held
  // pressed for a minimum time after a click, and Material dialogs, menu
  // surfaces and ripples, which mark their timed animations by class. A dialog
  // moves focus into itself once its opening animation ends.
  const iconLoading = (el) => el.localName === "ha-icon" && el.icon && !el._legacy && !el._path;
  const ripplePressed = (el) => (el.localName === "md-ripple" || el.localName === "ha-ripple") && el.pressed;
  const timedClasses = [
    "mdc-dialog--opening",
    "mdc-dialog--closing",
    "mdc-menu-surface--animating-open",
    "mdc-menu-surface--animating-closed",
    "mdc-ripple-upgraded--foreground-activation",
    "mdc-ripple-upgraded--foreground-deactivation",
  ];
  const timedAnimation = (el) => timedClasses.some((name) => el.classList.contains(name));

  let mutated = false;
  const mutations = new MutationObserver(() => {
    mutated = true;
  });
  const observed = new WeakSet();

  const outstanding = async () => {
    const waits = [];
    const loading = [];
    const visit = (root) => {
      if (!observed.has(root)) {
        observed.add(root);
        mutations.observe(root, { subtree: true, childList: true, attributes: true, characterData: true });
      }
      for (const animation of root.getAnimations()) {
        const end = animation.effect?.getComputedTiming().endTime;
        if (animation.playState === "running" && Number.isFinite(end)) {
          const name = animation.animationName ?? animation.transitionProperty ?? "animation";
          animation.finish();
          waits.push([name, animation.finished.catch(() => {})]);
        }
      }
      for (const el of root.querySelectorAll("*")) {
        const tag = el.localName;
        if (tag.includes("-") && !customElements.get(tag)) {
          waits.push([`<${tag}> definition`, customElements.whenDefined(tag)]);
        } else if (el.isUpdatePending) {
          waits.push([`<${tag}> update`, el.updateComplete]);
        } else if (iconLoading(el)) {
          waits.push([`<ha-icon> ${el.icon}`, frame()]);
        } else if (ripplePressed(el)) {
          waits.push([`<${tag}> press`, frame()]);
        } else if (timedAnimation(el)) {
          waits.push([`<${tag}> timed animation`, frame()]);
        }
        if (tag === "img" && !el.complete) loading.push(el);
        if (el.shadowRoot) visit(el.shadowRoot);
      }
    };
    visit(document);
    for (const image of await showing(loading)) {
      waits.push([`image ${image.currentSrc || image.src}`, image.decode().catch(() => {})]);
    }
    // The frontend's connection keeps each request it is waiting on, beside
    // its subscriptions, which are the entries with a callback. A page waiting
    // on an answer, such as action descriptions, leaves the DOM untouched until
    // it arrives.
    const connection = document.querySelector("home-assistant")?.hass?.connection;
    const requests = connection ? [...connection.commands.values()].filter((command) => !command.callback) : [];
    if (requests.length > 0) {
      waits.push(["Home Assistant requests", frame()]);
    }
    if (document.fonts.status !== "loaded") {
      waits.push(["fonts", document.fonts.ready]);
    }
    return waits;
  };

  try {
    let quiet = false;
    let waiting = ["DOM changes"];
    while (!quiet) {
      const remaining = deadline - performance.now();
      if (remaining <= 0) {
        throw new Error(`Page did not settle within ${deadlineMs} ms, still waiting on: ${waiting.join(", ")}`);
      }
      mutated = false;
      const waits = await outstanding();
      if (waits.length > 0) {
        waiting = [...new Set(waits.map(([name]) => name))];
        let timer;
        const expired = new Promise((resolve) => {
          timer = setTimeout(resolve, remaining);
        });
        await Promise.race([Promise.all(waits.map(([, wait]) => wait)), expired]);
        clearTimeout(timer);
      }
      await frame();
      quiet = waits.length === 0 && !mutated;
      if (waits.length === 0) waiting = ["DOM changes"];
    }
  } finally {
    mutations.disconnect();
  }
};
