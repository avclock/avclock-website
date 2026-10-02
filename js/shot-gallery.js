// Screenshot gallery device tabs (index.html, avgrav.html): show the
// gallery whose data-gallery matches the clicked tab. Arrow keys move
// between tabs. Without JavaScript, the first gallery (data-active)
// still shows.
(function () {
  var tabs = Array.prototype.slice.call(document.querySelectorAll("[data-gallery-tab]"));
  var galleries = document.querySelectorAll("[data-gallery]");
  function show(tab, focus) {
    var device = tab.getAttribute("data-gallery-tab");
    tabs.forEach(function (t) {
      t.setAttribute("aria-selected", t === tab ? "true" : "false");
      t.tabIndex = t === tab ? 0 : -1;
    });
    galleries.forEach(function (g) {
      if (g.getAttribute("data-gallery") === device) g.setAttribute("data-active", "");
      else g.removeAttribute("data-active");
    });
    if (focus) tab.focus();
  }
  tabs.forEach(function (tab, i) {
    tab.tabIndex = tab.getAttribute("aria-selected") === "true" ? 0 : -1;
    tab.addEventListener("click", function () { show(tab); });
    tab.addEventListener("keydown", function (e) {
      var step = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      if (!step) return;
      e.preventDefault();
      show(tabs[(i + step + tabs.length) % tabs.length], true);
    });
  });
})();
