// ============================================================
// Airport time pages (airport-time/, written by
// tools/airport-time/make_pages.py): keeps the clocks live.
//   - One airport: [data-tz] card with local time, date, offset, Zulu,
//     difference from you, sunrise/sunset, and the next clock change
//     (data-changes: the page's clock changes as Unix seconds).
//   - The index: every .apt-row[data-tz] shows its local time.
// Same time and sun math as js/avclock-demos.js (Try any airport).
// Plain JS, no libraries. Without it the pages still read correctly.
// ============================================================
(function () {
  "use strict";

  var fmtCache = {};
  function fmt(tz, opts) {
    var key = tz + JSON.stringify(opts);
    if (!fmtCache[key]) fmtCache[key] = new Intl.DateTimeFormat("en-US", Object.assign({ timeZone: tz }, opts));
    return fmtCache[key];
  }
  function parts(date, tz) {
    var out = {};
    fmt(tz, { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" })
      .formatToParts(date).forEach(function (p) { out[p.type] = p.value; });
    return out;
  }
  function offsetMinutes(date, tz) {
    var p = parts(date, tz);
    var asUTC = Date.UTC(+p.year, +p.month - 1, +p.day, +p.hour, +p.minute, +p.second);
    return Math.round((asUTC - Math.floor(date.getTime() / 1000) * 1000) / 60000);
  }
  function offsetText(mins) {
    var sign = mins >= 0 ? "+" : "−";
    var a = Math.abs(mins), h = Math.floor(a / 60), m = a % 60;
    return sign + h + (m ? ":" + String(m).padStart(2, "0") : "");
  }
  function time(date, tz, seconds) {
    var o = { hour: "numeric", minute: "2-digit" };
    if (seconds) o.second = "2-digit";
    return fmt(tz, o).format(date);
  }
  // Same approximation as the app's SunTime.swift (about 2 minutes).
  function sunTimes(lat, lon, date) {
    var start = Date.UTC(date.getUTCFullYear(), 0, 0);
    var dayOfYear = Math.floor((Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()) - start) / 86400000);
    var decl = -23.45 * Math.cos(2 * Math.PI / 365 * (dayOfYear + 10)) * Math.PI / 180;
    var latR = lat * Math.PI / 180;
    var cosHA = (Math.cos(90.833 * Math.PI / 180) - Math.sin(latR) * Math.sin(decl)) / (Math.cos(latR) * Math.cos(decl));
    if (cosHA < -1 || cosHA > 1) return null;
    var ha = Math.acos(cosHA) * 180 / Math.PI;
    var noon = 12 - lon / 15;
    var midnight = Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
    return { rise: new Date(midnight + (noon - ha / 15) * 3600000), set: new Date(midnight + (noon + ha / 15) * 3600000) };
  }

  var youTZ = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  function zulu(now) { return fmt("UTC", { hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(now).replace(":", "") + "Z"; }
  function set(root, f, text) { var el = root.querySelector("[data-f=" + f + "]"); if (el && el.textContent !== text) el.textContent = text; }

  var card = document.querySelector(".apt-clock[data-tz]");
  var rows = Array.prototype.slice.call(document.querySelectorAll(".apt-row[data-tz]"));
  var board = document.querySelector(".apt-zulu");

  function tickCard(now) {
    var tz = card.getAttribute("data-tz");
    set(card, "time", time(now, tz, true));
    set(card, "date", fmt(tz, { weekday: "long", month: "long", day: "numeric", year: "numeric" }).format(now));
    var off = offsetMinutes(now, tz), diff = off - offsetMinutes(now, youTZ);
    set(card, "utc", "UTC" + offsetText(off));
    set(card, "zulu", zulu(now));
    set(card, "diff", diff === 0 ? "Same as you" : offsetText(diff) + " h from you");
    var sun = sunTimes(+card.getAttribute("data-lat"), +card.getAttribute("data-lon"), now);
    set(card, "sun", sun ? time(sun.rise, tz) + " / " + time(sun.set, tz) : "No sunrise or sunset today");
    var changes = (card.getAttribute("data-changes") || "").split(",").filter(Boolean).map(Number);
    var next = changes.filter(function (s) { return s * 1000 > now.getTime(); })[0];
    if (changes.length) {
      if (next) {
        var at = new Date(next * 1000);
        var after = offsetMinutes(new Date(at.getTime() + 60000), tz), before = offsetMinutes(new Date(at.getTime() - 60000), tz);
        set(card, "next", fmt(tz, { month: "short", day: "numeric", year: "numeric" }).format(new Date(at.getTime() - 60000)) +
          ", clocks go " + (after > before ? "forward" : "back"));
      } else {
        set(card, "next", "See the table below");
      }
    }
  }

  function tick() {
    var now = new Date();
    try {
      if (card) tickCard(now);
      if (board) set(board, "zulu", zulu(now));
      rows.forEach(function (r) { set(r, "time", time(now, r.getAttribute("data-tz"))); });
    } catch (e) { /* a zone this browser doesn't know: the page's own text stays */ }
  }
  tick();
  setInterval(tick, 1000);
})();
