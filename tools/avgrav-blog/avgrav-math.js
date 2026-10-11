// Copied from avclock/AvGrav tools/app-store-screenshots/avgrav-math.js on 2026-10-11 so the daily
// post can compute fuel numbers without that repository. If the app's math changes, copy it again.
//   node -e 'const M=require("./tools/avgrav-blog/avgrav-math.js").AvGravMath; ...'   (from the repo root)
// The app's own correction math (Api Gravity Calculator/
// GravityCorrection.swift), ported line for line so every number in the
// screenshots is what AvGrav really shows for those inputs.
(function (root) {
  var WATER = 999.016;
  function constants(d) {
    if (d >= 838.3127) return [103.8720, 0.2701, 0];
    if (d >= 787.5195) return [330.3010, 0, 0];
    if (d >= 770.3520) return [1489.0670, 0, -0.00186840];
    return [192.4571, 0.2438, 0];
  }
  function alpha60(d) { var k = constants(d); return k[0] / (d * d) + k[1] / d + k[2]; }
  function solve(obs, expanded) {
    var lo = obs * 0.7, hi = obs * 1.4;
    for (var i = 0; i < 100; i++) { var mid = (lo + hi) / 2; if (expanded(mid) < obs) lo = mid; else hi = mid; if (hi - lo < 1e-9) break; }
    return (lo + hi) / 2;
  }
  function correctedAPI(api, tF) {
    var dT = tF - 60;
    if (Math.abs(dT) < 0.001) return api;
    var obs = WATER * 141.5 / (api + 131.5) * (1 - 0.00001278 * dT - 0.0000000062 * dT * dT);
    var d60 = solve(obs, function (c) { var a = alpha60(c); return c * Math.exp(-a * dT * (1 + 0.8 * a * dT)); });
    return 141.5 * WATER / d60 - 131.5;
  }
  function ctlMetric(d15, dTC) { var a = 1.8 * alpha60(d15); return Math.exp(-a * dTC * (1 + 0.8 * a * dTC)); }
  function density15C(obsDensity, tC) {
    var dT = tC - 15;
    if (Math.abs(dT) < 0.0005) return obsDensity;
    var f = 1 - 0.000023 * dT - 0.00000002 * dT * dT;
    return solve(obsDensity * f, function (d) { return d * ctlMetric(d, dT); });
  }
  function apiFromDensity15(d15) { return 141.5 * WATER / (d15 * ctlMetric(d15, 5 / 9)) - 131.5; }
  function density15FromAPI(api) { var d60 = WATER * 141.5 / (api + 131.5); return solve(d60, function (d) { return d * ctlMetric(d, 5 / 9); }); }
  function vcf(api, tF) { var d60 = WATER * 141.5 / (api + 131.5), a = alpha60(d60), dT = tF - 60; return Math.exp(-a * dT * (1 + 0.8 * a * dT)); }
  function sg(api) { return 141.5 / (api + 131.5); }
  function lbPerGal(api) { return sg(api) * 8.32774; }
  function kgPerL(api) { return sg(api) * WATER / 1000; }
  root.AvGravMath = { correctedAPI: correctedAPI, density15C: density15C, apiFromDensity15: apiFromDensity15, density15FromAPI: density15FromAPI, vcf: vcf, sg: sg, lbPerGal: lbPerGal, kgPerL: kgPerL };
})(typeof window !== "undefined" ? window : module.exports);
