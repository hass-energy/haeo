window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true,
  },
  options: {
    ignoreHtmlClass: ".*",
    processHtmlClass: "arithmatex",
  },
  startup: {
    pageReady: () => {
      return MathJax.startup.defaultPageReady().then(() => {
        console.log("MathJax initial typesetting complete");
      });
    },
  },
};

// Re-render math when navigating or when tabs change
document$.subscribe(() => {
  MathJax.typesetPromise().catch((err) =>
    console.log("MathJax typeset failed: " + err.message)
  );
});

// Also re-render when tab content becomes visible
document.addEventListener("DOMContentLoaded", () => {
  // Watch for tab changes
  const observer = new MutationObserver(() => {
    MathJax.typesetPromise();
  });

  // Observe tab content containers
  const tabContainers = document.querySelectorAll(".tabbed-content");
  tabContainers.forEach((container) => {
    observer.observe(container, {
      childList: true,
      subtree: true,
      attributes: true,
    });
  });
});
