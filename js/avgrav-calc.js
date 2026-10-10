// ============================================================
// AvGrav page: the calculator at the top, running the same math as
// the app (GravityCorrection.swift, version 2): API MPMS 11.1
// Table 6B with the °F constants and its four density bands, the
// exp() volume correction, the glass hydrometer correction, and a
// bisection solve. Density mode is Table 53B (constants x1.8 for °C,
// metric glass correction). Checked against the published Table 5B
// pair (46.0 API at 85°F is 43.8 at 60°F) and the app's unit tests.
// Reference only, like the app.
// ============================================================
(function () {
  "use strict";

  var W = 999.016; // kg/m³, water at 60°F

  // Table 6B, per °F, density in kg/m³ at 60°F.
  function alpha60(d) {
    if (d >= 838.3127) return 103.8720 / (d * d) + 0.2701 / d;   // fuel oils
    if (d >= 787.5195) return 330.3010 / (d * d);                 // jet fuels
    if (d >= 770.3520) return 1489.0670 / (d * d) - 0.00186840;   // transition
    return 192.4571 / (d * d) + 0.2438 / d;                       // gasolines
  }
  function ctl(alpha, dT) { return Math.exp(-alpha * dT * (1 + 0.8 * alpha * dT)); }

  function solve(observed, expanded) {
    var lo = observed * 0.7, hi = observed * 1.4;
    if (expanded(lo) > observed || expanded(hi) < observed) return NaN;
    for (var i = 0; i < 100 && hi - lo > 1e-9; i++) {
      var mid = (lo + hi) / 2;
      if (expanded(mid) < observed) lo = mid; else hi = mid;
    }
    return (lo + hi) / 2;
  }

  // API mode: observed API at °F -> API at 60°F.
  function correctedAPI(api, tF) {
    if (!(api > -10 && api < 100 && tF > -50 && tF < 200)) return NaN;
    var dT = tF - 60;
    if (Math.abs(dT) < 0.001) return api;
    var observed = W * 141.5 / (api + 131.5) * (1 - 0.00001278 * dT - 0.0000000062 * dT * dT);
    var d60 = solve(observed, function (d) { return d * ctl(alpha60(d), dT); });
    return 141.5 * W / d60 - 131.5;
  }

  // Density mode: observed kg/m³ at °C -> kg/m³ at 15°C.
  function density15(rho, tC) {
    if (!(rho > 600 && rho < 1100 && tC > -45 && tC < 93)) return NaN;
    var dT = tC - 15;
    if (Math.abs(dT) < 0.0005) return rho;
    var observed = rho * (1 - 0.000023 * dT - 0.00000002 * dT * dT);
    return solve(observed, function (d) { return d * ctl(1.8 * alpha60(d), dT); });
  }
  function apiFromDensity15(d15) {
    var d60 = d15 * ctl(1.8 * alpha60(d15), 5 / 9);
    return 141.5 * W / d60 - 131.5;
  }
  function density15FromAPI(api) {
    var d60 = W * 141.5 / (api + 131.5);
    return solve(d60, function (d) { return d * ctl(1.8 * alpha60(d), 5 / 9); });
  }

  // Exposed for the self-check below and for anyone curious in the console.
  window.avgravMath = { correctedAPI: correctedAPI, density15: density15, apiFromDensity15: apiFromDensity15, density15FromAPI: density15FromAPI };

  var FUELS = {
    jet: { label: "Jet A / Jet A-1", range: [36, 51] },
    // Same ranges as FuelType.typicalAPIRange in the app; 100LL is 60-72
    // since 2026-10-10 (55-65 flagged ordinary avgas, about 65-68 API).
    avgas: { label: "Avgas 100LL", range: [60, 72] },
    mogas: { label: "Mogas", range: [55, 65] },
    diesel: { label: "Diesel", range: [30, 42] }
  };

  var root = document.getElementById("grav-calc");
  if (!root) return;
  var form = root.querySelector("form");
  var modeInputs = root.querySelectorAll("input[name=mode]");
  var reading = root.querySelector("#gc-reading"), readingLabel = root.querySelector("#gc-reading-label");
  var temp = root.querySelector("#gc-temp"), unit = root.querySelector("#gc-unit"), fuel = root.querySelector("#gc-fuel");
  var big = root.querySelector(".gc-big"), bigLabel = root.querySelector(".gc-big-label");
  var second = root.querySelector(".gc-second"), statusEl = root.querySelector(".gc-status");
  var sg = root.querySelector("[data-f=sg]"), lbgal = root.querySelector("[data-f=lbgal]"), d15el = root.querySelector("[data-f=d15]");
  var hydrometer = root.querySelector(".gc-hydrometer");
  var used = false;

  function mode() { return root.querySelector("input[name=mode]:checked").value; }
  function num(el) {
    var v = parseFloat(String(el.value).replace(",", "."));
    return isFinite(v) ? v : NaN;
  }

  function setMode() {
    var dens = mode() === "density";
    readingLabel.textContent = dens ? "Observed density (kg/m³)" : "Observed API gravity";
    reading.placeholder = dens ? "e.g. 800.0" : "e.g. 46.0";
    reading.value = dens ? "800.0" : "46.0";
    if (dens) { unit.value = "C"; temp.value = "29.4"; } else { unit.value = "F"; temp.value = "85"; }
    calc();
  }

  function calc() {
    var r = num(reading), t = num(temp);
    var tF = unit.value === "C" ? t * 9 / 5 + 32 : t;
    var tC = unit.value === "C" ? t : (t - 32) * 5 / 9;
    var api, d15;
    if (mode() === "density") {
      d15 = density15(r, tC);
      api = isFinite(d15) ? apiFromDensity15(d15) : NaN;
    } else {
      api = correctedAPI(r, tF);
      d15 = isFinite(api) ? density15FromAPI(api) : NaN;
    }
    if (!isFinite(api)) {
      big.textContent = "—";
      second.textContent = "";
      statusEl.textContent = "Enter a realistic reading and temperature.";
      statusEl.className = "gc-status";
      sg.textContent = lbgal.textContent = d15el.textContent = "–";
      return;
    }
    var dens = mode() === "density";
    bigLabel.textContent = dens ? "Density @ 15°C (kg/m³)" : "Corrected API @ 60°F";
    big.textContent = dens ? d15.toFixed(1) : api.toFixed(2);
    second.textContent = dens ? api.toFixed(2) + " API @ 60°F" : d15.toFixed(1) + " kg/m³ @ 15°C";
    var s = 141.5 / (api + 131.5);
    sg.textContent = s.toFixed(4);
    lbgal.textContent = (s * 8.32774).toFixed(3);
    d15el.textContent = (s * W / 1000).toFixed(4);
    var range = FUELS[fuel.value].range, span = range[1] - range[0];
    var cls, text;
    if (api < range[0] || api > range[1]) { cls = "bad"; text = "Outside the typical range for " + FUELS[fuel.value].label; }
    else if (api - range[0] < span * 0.1 || range[1] - api < span * 0.1) { cls = "marginal"; text = "Near the edge of the typical range"; }
    else { cls = "good"; text = "Within the typical range for " + FUELS[fuel.value].label; }
    statusEl.textContent = text;
    statusEl.className = "gc-status " + cls;
    big.className = "gc-big " + cls;
    // The hydrometer floats lower in lighter fuel (higher API).
    if (hydrometer) {
      var depth = Math.max(0, Math.min(1, (api - 25) / 50));
      hydrometer.style.setProperty("--sink", (depth * 46).toFixed(1) + "px");
    }
    big.classList.remove("gc-pop"); void big.offsetWidth; big.classList.add("gc-pop");
  }

  modeInputs.forEach(function (m) { m.addEventListener("change", setMode); });
  [reading, temp, unit, fuel].forEach(function (el) {
    el.addEventListener("input", function () {
      calc();
      if (!used && window.avTrack) { used = true; window.avTrack("demo", "avgrav-calc"); }
    });
  });
  form.addEventListener("submit", function (e) { e.preventDefault(); calc(); });
  calc();
})();
