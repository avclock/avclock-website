// Cloudflare Pages Function -- POST /api/track
// Public/unauthenticated on purpose: every visitor's browser needs to
// reach this to log a pageview, scroll, outbound click, or share
// click (see ../../js/track.js). Only the READ side (stats.js, and
// analytics.html itself) should ever be gated behind Cloudflare
// Access -- gating this endpoint too would just make everyone's
// pageviews silently fail to log.
//
// Requires a KV namespace bound to this Pages project as
// ANALYTICS_KV (Cloudflare dashboard -> your Pages project ->
// Settings -> Functions -> KV namespace bindings). See README.md.

const ALLOWED_TYPES = new Set(["view", "scroll", "outbound", "share"]);
const RECENT_KEY = "recent";
const RECENT_LIMIT = 50;

export async function onRequestPost({ request, env }) {
  if (!env.ANALYTICS_KV) return new Response(null, { status: 204 });

  let body;
  try {
    body = await request.json();
  } catch (e) {
    return new Response(null, { status: 204 });
  }

  const type = String(body.type || "").slice(0, 20);
  if (!ALLOWED_TYPES.has(type)) return new Response(null, { status: 204 });

  const path = String(body.path || "/").slice(0, 200);
  const detail = body.detail != null ? String(body.detail).slice(0, 200) : null;
  const day = new Date().toISOString().slice(0, 10);

  const counterKey = detail
    ? `count:${type}:${path}:${detail}:${day}`
    : `count:${type}:${path}:${day}`;

  const kv = env.ANALYTICS_KV;
  const current = parseInt((await kv.get(counterKey)) || "0", 10);
  await kv.put(counterKey, String(current + 1));

  // Rolling recent-activity log for the dashboard's live feed.
  const recentRaw = await kv.get(RECENT_KEY);
  const recent = recentRaw ? JSON.parse(recentRaw) : [];
  recent.unshift({ type, path, detail, t: Date.now() });
  await kv.put(RECENT_KEY, JSON.stringify(recent.slice(0, RECENT_LIMIT)));

  return new Response(null, { status: 204 });
}
