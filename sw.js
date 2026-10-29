const CACHE = "ndsp-3c7c85265f";
const FILES = ["./", "cores/desmume2015-thread.js", "cores/desmume2015-thread.raw.js", "cores/desmume2015-thread_libretro.gz.wasm", "cores/desmume2015.js", "cores/desmume2015_libretro.gz.wasm", "ejs/bundle.js", "ejs/compression/extractzip.js", "icons/apple-touch-icon.png", "icons/icon-192.png", "icons/icon-512.png", "icons/icon-maskable-512.png", "index.html", "manifest.webmanifest"];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES.map(f => new Request(f, { cache: "reload" })))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
// GitHub Pages can't send headers, so the worker adds the ones that make the page
// "cross-origin isolated": that is what lets the engine use several CPU cores.
function isolate(r) {
  if (!r || r.status === 0 || r.type === "opaque") return r;
  const h = new Headers(r.headers);
  h.set("Cross-Origin-Opener-Policy", "same-origin");
  h.set("Cross-Origin-Embedder-Policy", "require-corp");
  h.set("Cross-Origin-Resource-Policy", "same-origin");
  return new Response(r.body, { status: r.status, statusText: r.statusText, headers: h });
}
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin || u.pathname.endsWith("/version.json")) return;
  e.respondWith(caches.match(e.request, { ignoreSearch: true }).then(r => r || fetch(e.request)).then(isolate));
});
