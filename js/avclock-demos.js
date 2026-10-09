// ============================================================
// AvClock homepage demos (beyond the live board and map, which live
// in index.html's own inline script):
//   - "Try any airport": search the same OurAirports dataset the app
//     downloads (data/airports.json, made from avcock-data's
//     clean_airports.json: [iata, icao, name, lat, lon, tz, country,
//     city]; loaded only when the section comes near the screen) and see
//     that airport's live local time, Zulu offset, difference from you,
//     and sunrise/sunset.
//   - Overlap: the hours that work for everyone, same rule as the
//     app's Overlap screen.
//   - Jet lag: day 1 of the same plan the app builds for a logged
//     flight (same light-timing rule as JetLagPlanView.swift).
//   - Big Clock: a preview of the StandBy widget, arrow included.
// Plain JS, no libraries. Time zone math is Intl.DateTimeFormat.
// ============================================================
(function () {
  "use strict";

  var track = window.avTrack || function () {};
  // One "demo" event per page load at most (the first demo used), so
  // trying all four demos costs one KV write, not four.
  var tracked = false;
  function trackOnce(name) {
    if (tracked) return;
    tracked = true;
    track("demo", name);
  }

  // ---- Time helpers ------------------------------------------------

  var fmtCache = {};
  function fmt(tz, opts) {
    var key = tz + JSON.stringify(opts);
    if (!fmtCache[key]) {
      var o = Object.assign({ timeZone: tz }, opts);
      fmtCache[key] = new Intl.DateTimeFormat("en-US", o);
    }
    return fmtCache[key];
  }

  function parts(date, tz) {
    var out = {};
    fmt(tz, { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23" })
      .formatToParts(date).forEach(function (p) { out[p.type] = p.value; });
    return out;
  }

  // Minutes the zone is ahead of UTC at a moment.
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

  var youTZ = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";

  // Sunrise/sunset, same approximation as the app's SunTime.swift
  // (declination + hour angle, refraction-corrected, ~2 minutes).
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
    return {
      rise: new Date(midnight + (noon - ha / 15) * 3600000),
      set: new Date(midnight + (noon + ha / 15) * 3600000)
    };
  }

  // ---- Shared hubs for Overlap, Jet lag, Big Clock -----------------

  var HUBS = [
    { code: "JFK", city: "New York", tz: "America/New_York", lat: 40.64, lon: -73.78 },
    { code: "LAX", city: "Los Angeles", tz: "America/Los_Angeles", lat: 33.94, lon: -118.41 },
    { code: "ORD", city: "Chicago", tz: "America/Chicago", lat: 41.98, lon: -87.90 },
    { code: "DEN", city: "Denver", tz: "America/Denver", lat: 39.86, lon: -104.67 },
    { code: "LHR", city: "London", tz: "Europe/London", lat: 51.47, lon: -0.45 },
    { code: "CDG", city: "Paris", tz: "Europe/Paris", lat: 49.01, lon: 2.55 },
    { code: "DXB", city: "Dubai", tz: "Asia/Dubai", lat: 25.25, lon: 55.36 },
    { code: "SIN", city: "Singapore", tz: "Asia/Singapore", lat: 1.36, lon: 103.99 },
    { code: "HND", city: "Tokyo", tz: "Asia/Tokyo", lat: 35.55, lon: 139.78 },
    { code: "SYD", city: "Sydney", tz: "Australia/Sydney", lat: -33.95, lon: 151.18 },
    { code: "GRU", city: "São Paulo", tz: "America/Sao_Paulo", lat: -23.43, lon: -46.47 },
    { code: "JNB", city: "Johannesburg", tz: "Africa/Johannesburg", lat: -26.13, lon: 28.24 }
  ];
  function hub(code) { return HUBS.filter(function (h) { return h.code === code; })[0]; }

  // ---- Try any airport ----------------------------------------------

  (function tryAirport() {
    var section = document.getElementById("try");
    if (!section) return;
    var input = document.getElementById("try-input");
    var list = document.getElementById("try-results");
    var card = document.getElementById("try-card");
    var status = document.getElementById("try-status");
    var airports = null, loading = false, current = null, active = -1, matches = [];

    function load() {
      if (airports || loading) return;
      loading = true;
      status.textContent = "Loading airports…";
      fetch("data/airports.json").then(function (r) { return r.json(); }).then(function (rows) {
        airports = rows.map(function (r) {
          // r[7], the city, came in 2026-10-09; older copies of the file
          // without it still work.
          return { code: r[0], icao: r[1], name: r[2], lat: r[3], lon: r[4], tz: r[5], country: r[6], blob: (r[0] + " " + r[1] + " " + r[2] + " " + (r[7] || "") + " " + r[6]).toLowerCase() };
        });
        status.textContent = airports.length.toLocaleString() + " airports ready. Try LHR, Denver, or Haneda.";
        if (!current) show(airports.filter(function (a) { return a.code === "LHR"; })[0]);
        if (input.value) search(input.value);
      }).catch(function () {
        status.textContent = "Couldn't load the airport list. Check your connection and try again.";
        loading = false;
      });
    }

    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (entries) {
        if (entries.some(function (e) { return e.isIntersecting; })) { load(); io.disconnect(); }
      }, { rootMargin: "400px" });
      io.observe(section);
    } else {
      load();
    }
    input.addEventListener("focus", load);

    function search(q) {
      q = q.trim().toLowerCase();
      if (!airports || !q) { matches = []; render(); return; }
      var up = q.toUpperCase();
      var scored = [];
      for (var i = 0; i < airports.length; i++) {
        var a = airports[i], s = 0;
        if (a.code === up || a.icao === up) s = 100;
        else if (a.code.indexOf(up) === 0 || (a.icao && a.icao.indexOf(up) === 0)) s = 60;
        else if (a.name.toLowerCase().indexOf(q) === 0) s = 40;
        else if (a.blob.indexOf(q) !== -1) s = 20;
        if (s) scored.push([s, a]);
      }
      scored.sort(function (x, y) { return y[0] - x[0] || x[1].name.localeCompare(y[1].name); });
      matches = scored.slice(0, 6).map(function (x) { return x[1]; });
      active = matches.length ? 0 : -1;
      render();
    }

    function render() {
      list.innerHTML = "";
      list.hidden = !matches.length;
      input.setAttribute("aria-expanded", String(!!matches.length));
      matches.forEach(function (a, i) {
        var li = document.createElement("li");
        li.id = "try-opt-" + i;
        li.setAttribute("role", "option");
        li.setAttribute("aria-selected", String(i === active));
        var code = document.createElement("span");
        code.className = "code";
        code.textContent = a.code;
        var name = document.createElement("span");
        name.className = "name";
        name.textContent = a.name + (a.country ? ", " + a.country : "");
        li.appendChild(code);
        li.appendChild(name);
        li.addEventListener("mousedown", function (e) { e.preventDefault(); pick(a); });
        list.appendChild(li);
      });
      if (active >= 0) input.setAttribute("aria-activedescendant", "try-opt-" + active);
      else input.removeAttribute("aria-activedescendant");
    }

    function pick(a) {
      show(a);
      input.value = "";
      matches = [];
      render();
      trackOnce("try-airport");
    }

    input.addEventListener("input", function () { search(input.value); });
    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" && matches.length) { e.preventDefault(); active = (active + 1) % matches.length; render(); }
      else if (e.key === "ArrowUp" && matches.length) { e.preventDefault(); active = (active - 1 + matches.length) % matches.length; render(); }
      else if (e.key === "Enter" && active >= 0) { e.preventDefault(); pick(matches[active]); }
      else if (e.key === "Escape") { matches = []; render(); }
    });
    input.addEventListener("blur", function () { setTimeout(function () { matches = []; render(); }, 120); });

    function show(a) {
      if (!a) return;
      current = a;
      card.hidden = false;
      card.querySelector("[data-f=code]").textContent = a.code + (a.icao ? " · " + a.icao : "");
      card.querySelector("[data-f=name]").textContent = a.name + (a.country ? ", " + a.country : "");
      card.classList.remove("try-card-in");
      void card.offsetWidth;
      card.classList.add("try-card-in");
      tick();
    }

    function tick() {
      if (!current) return;
      var now = new Date();
      try {
        card.querySelector("[data-f=time]").textContent = time(now, current.tz, true);
        card.querySelector("[data-f=date]").textContent = fmt(current.tz, { weekday: "long", month: "short", day: "numeric" }).format(now);
        var off = offsetMinutes(now, current.tz);
        var diff = off - offsetMinutes(now, youTZ);
        card.querySelector("[data-f=utc]").textContent = "UTC" + offsetText(off);
        card.querySelector("[data-f=diff]").textContent = diff === 0 ? "Same as you" : offsetText(diff) + "h from you";
        card.querySelector("[data-f=zulu]").textContent = fmt("UTC", { hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(now) + "Z";
        var sun = sunTimes(current.lat, current.lon, now);
        card.querySelector("[data-f=sun]").textContent = sun
          ? time(sun.rise, current.tz) + " / " + time(sun.set, current.tz)
          : "No sunrise or sunset today";
      } catch (e) { /* unknown zone in this browser */ }
    }
    setInterval(tick, 1000);
  })();

  // ---- Overlap -------------------------------------------------------

  (function overlap() {
    var root = document.getElementById("overlap-demo");
    if (!root) return;
    var chips = root.querySelector(".ov-chips");
    var grid = root.querySelector(".ov-grid");
    var out = root.querySelector(".ov-result");
    var detail = root.querySelector(".ov-detail");
    var windowSel = root.querySelector(".ov-window");
    var chosen = ["JFK", "LHR", "HND"];
    var selected = new Date().getHours();

    HUBS.forEach(function (h) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "chip-btn";
      b.textContent = h.code;
      b.setAttribute("aria-pressed", String(chosen.indexOf(h.code) !== -1));
      b.addEventListener("click", function () {
        var i = chosen.indexOf(h.code);
        if (i !== -1) chosen.splice(i, 1);
        else { chosen.push(h.code); if (chosen.length > 4) chosen.shift(); }
        chips.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", String(chosen.indexOf(x.textContent) !== -1)); });
        draw();
        trackOnce("overlap");
      });
      chips.appendChild(b);
    });
    windowSel.addEventListener("change", function () { draw(); trackOnce("overlap"); });

    function rows() {
      return [{ code: "YOU", tz: youTZ }].concat(chosen.map(hub));
    }
    function slots() {
      var d = new Date(); d.setHours(0, 0, 0, 0);
      var s = [];
      for (var i = 0; i < 24; i++) s.push(new Date(d.getTime() + i * 3600000));
      return s;
    }
    function localHour(date, tz) {
      var p = parts(new Date(date.getTime() + 30 * 60000), tz);
      return +p.hour + (+p.minute) / 60;
    }
    function inWindow(date, tz) {
      var w = windowSel.value === "business" ? [9, 17] : [8, 22];
      var h = localHour(date, tz);
      return h >= w[0] && h < w[1];
    }

    function draw() {
      var rs = rows(), ss = slots();
      grid.innerHTML = "";
      var all = ss.map(function (s) { return rs.every(function (r) { return inWindow(s, r.tz); }); });
      rs.forEach(function (r) {
        var row = document.createElement("div");
        row.className = "ov-row";
        var label = document.createElement("span");
        label.className = "ov-code";
        label.textContent = r.code;
        row.appendChild(label);
        var cells = document.createElement("div");
        cells.className = "ov-cells";
        ss.forEach(function (s, i) {
          var c = document.createElement("button");
          c.type = "button";
          c.className = "ov-cell" + (all[i] ? " all" : inWindow(s, r.tz) ? " in" : "") + (i === selected ? " sel" : "");
          c.setAttribute("aria-label", time(s, youTZ) + " your time");
          c.addEventListener("click", function () { selected = i; draw(); trackOnce("overlap"); });
          cells.appendChild(c);
        });
        row.appendChild(cells);
        grid.appendChild(row);
      });
      var ticks = document.createElement("div");
      ticks.className = "ov-row ov-ticks";
      ticks.innerHTML = "<span class=\"ov-code\"></span><div class=\"ov-cells\">" +
        ss.map(function (s, i) { return "<span>" + (i % 6 === 0 ? time(s, youTZ).replace(":00", "") : "") + "</span>"; }).join("") + "</div>";
      grid.appendChild(ticks);

      var ranges = [], start = null;
      all.forEach(function (ok, i) {
        if (ok && start === null) start = i;
        if (start !== null && (!ok || i === 23)) {
          var end = ok && i === 23 ? 24 : i;
          ranges.push(time(ss[start], youTZ) + " to " + time(new Date(ss[0].getTime() + end * 3600000), youTZ));
          start = null;
        }
      });
      out.textContent = ranges.length
        ? "Works for everyone (your time): " + ranges.join(", ")
        : "No hour today works for everyone in this window. Try the Awake window or fewer airports.";
      detail.textContent = "At " + time(ss[selected], youTZ) + " your time: " +
        rs.slice(1).map(function (r) { return r.code + " " + time(ss[selected], r.tz); }).join(" · ");
    }
    draw();
  })();

  // ---- Jet lag, day 1 ------------------------------------------------

  (function jetLag() {
    var root = document.getElementById("jetlag-demo");
    if (!root) return;
    var from = root.querySelector(".jl-from"), to = root.querySelector(".jl-to"), wake = root.querySelector(".jl-wake");
    var out = root.querySelector(".jl-out");
    HUBS.forEach(function (h) {
      [from, to].forEach(function (sel) {
        var o = document.createElement("option");
        o.value = h.code;
        o.textContent = h.code + " · " + h.city;
        sel.appendChild(o);
      });
    });
    from.value = "JFK"; to.value = "LHR";

    function hm(hours) {
      var h = ((hours % 24) + 24) % 24;
      var d = new Date(2000, 0, 1, Math.floor(h), Math.round((h % 1) * 60));
      return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
    }

    function draw() {
      var a = hub(from.value), b = hub(to.value), now = new Date();
      var diff = (offsetMinutes(now, b.tz) - offsetMinutes(now, a.tz)) / 60;
      if (diff > 12) diff -= 24;
      if (diff <= -12) diff += 24;
      var abs = Math.abs(diff);
      var head = b.code + " is " + (abs % 1 ? abs.toFixed(1) : abs) + " hours " + (diff > 0 ? "ahead of " : "behind ") + a.code + ".";
      if (abs < 3) {
        out.innerHTML = "";
        var p = document.createElement("p");
        p.textContent = head + " Under 3 hours, most people adjust within a day or two. Get daylight at your destination and keep to local meal and sleep times.";
        out.appendChild(p);
        return;
      }
      var advance = diff > 0 && diff <= 9;
      var shift = diff > 9 ? 24 - diff : abs;
      var rate = advance ? 1 : 1.5;
      var days = Math.ceil(shift / rate);
      var sign = advance ? 1 : -1;
      var usual = +wake.value;
      var bodyWake = usual + sign * shift;
      var low = bodyWake - 3;
      var seek = advance ? [low, low + 3] : [low - 3, low];
      var avoid = advance ? [low - 3, low] : [low, low + 3];
      var goal = usual + sign * Math.max(0, shift - rate);
      out.innerHTML = "";
      var lines = [
        ["jl-head", head + " Your body clock moves " + shift + " hours " + (advance ? "earlier" : "later") + ", about " + days + " day" + (days === 1 ? "" : "s") + " to adjust." + (diff > 9 ? " That's a big jump east, so the plan goes the long way round." : "")],
        ["jl-seek", "Day 1, get bright light " + hm(seek[0]) + " to " + hm(seek[1])],
        ["jl-avoid", "Avoid bright light " + hm(avoid[0]) + " to " + hm(avoid[1])],
        ["jl-sleep", "Aim to sleep " + hm(goal - 8) + " to " + hm(goal)]
      ];
      lines.forEach(function (l) {
        var p = document.createElement("p");
        p.className = l[0];
        p.textContent = l[1];
        out.appendChild(p);
      });
      var note = document.createElement("p");
      note.className = "jl-note";
      note.textContent = "Times are " + b.city + " local time. The app builds every day of the plan from your logged flight. General guidance, not medical advice.";
      out.appendChild(note);
    }
    [from, to, wake].forEach(function (el) { el.addEventListener("change", function () { draw(); trackOnce("jetlag"); }); });
    draw();
  })();

  // ---- Big Clock -----------------------------------------------------

  (function bigClock() {
    var root = document.getElementById("bigclock-demo");
    if (!root) return;
    var order = ["LHR", "HND", "JFK", "SYD", "DXB"], i = 0;
    var code = root.querySelector(".bc-code"), city = root.querySelector(".bc-city");
    var t = root.querySelector(".bc-time"), d = root.querySelector(".bc-date"), off = root.querySelector(".bc-off");
    function draw() {
      var h = hub(order[i]), now = new Date();
      code.textContent = h.code;
      city.textContent = h.city;
      t.textContent = fmt(h.tz, { hour: "numeric", minute: "2-digit" }).format(now).replace(/\s?[AP]M$/, "");
      d.textContent = fmt(h.tz, { weekday: "short", day: "numeric", month: "short" }).format(now);
      var diff = offsetMinutes(now, h.tz) - offsetMinutes(now, youTZ);
      off.textContent = diff === 0 ? "Same time" : offsetText(diff) + "h";
    }
    root.querySelector(".bc-next").addEventListener("click", function () {
      i = (i + 1) % order.length;
      t.classList.remove("bc-swap"); void t.offsetWidth; t.classList.add("bc-swap");
      draw();
      trackOnce("bigclock");
    });
    draw();
    setInterval(draw, 15000);
  })();
})();
