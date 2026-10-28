"""Turn dist/ (the artifact build) into a stand-alone home-screen web app in site/.

Adds a full HTML document head, a web app manifest, home-screen icons and a service
worker that caches the emulator so it opens offline after the first run.
Run build.py first.
"""
import hashlib, json, os, shutil
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
SITE = os.path.join(ROOT, "site")

BG = (18, 20, 23)
AMBER = (242, 179, 61)


def icon(size, path, pad=0.0):
    im = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(im)
    s = size * (1 - pad * 2)
    o = size * pad
    w, h = s * 0.62, s * 0.30
    x0 = o + (s - w) / 2
    r = max(2, int(s * 0.04))
    top = (x0, o + s * 0.15, x0 + w, o + s * 0.15 + h)
    bot = (x0, o + s * 0.55, x0 + w, o + s * 0.55 + h)
    d.rounded_rectangle(top, radius=r, outline=AMBER, width=max(2, int(s * 0.045)))
    d.rounded_rectangle(bot, radius=r, fill=AMBER)
    im.save(path)


HEAD = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no">
<meta name="theme-color" content="#121417">
<meta name="apple-mobile-web-app-title" content="NDS Pocket">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>NDS Pocket</title>
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">
<link rel="icon" type="image/png" href="icons/icon-192.png">
<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px);box-sizing:border-box}body{margin:0}[hidden]{display:none!important}</style>
</head>
<body>
"""

TAIL = """
<script>
if ("serviceWorker" in navigator) {
  // a page that was already controlled and then gets a new worker = a new version was downloaded
  var hadController = !!navigator.serviceWorker.controller;
  // first visit (or first visit after this change): reload once under the worker's headers
  var needIsolation = function () {
    try {
      if (window.crossOriginIsolated || sessionStorage.getItem("ndsp-coi-reload")) return false;
      sessionStorage.setItem("ndsp-coi-reload", "1"); return true;
    } catch (e) { return false; }
  };
  if (navigator.serviceWorker.controller && needIsolation()) location.reload();
  navigator.serviceWorker.addEventListener("controllerchange", function () {
    if (!hadController && needIsolation()) { location.reload(); return; }
    if (hadController && window.__ndspUpdateReady) window.__ndspUpdateReady();
    hadController = true;
  });
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("sw.js").then(function (reg) {
      var check = function () { reg.update().catch(function () {}); };
      document.addEventListener("visibilitychange", function () { if (document.visibilityState === "visible") check(); });
      setInterval(check, 30 * 60 * 1000);
    }).catch(function () {});
  });
}
</script>
</body>
</html>
"""


def main():
    if os.path.exists(SITE):
        shutil.rmtree(SITE)
    shutil.copytree(DIST, SITE)
    # the single-file page is only for the Claude viewer; the site uses the split files
    for extra in ("single.html", "_test.html"):
        if os.path.exists(os.path.join(SITE, extra)):
            os.remove(os.path.join(SITE, extra))
    os.makedirs(os.path.join(SITE, "icons"), exist_ok=True)

    page = open(os.path.join(DIST, "index.html"), encoding="utf-8").read()
    # the artifact page has no head of its own; give the standalone app one
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
        f.write(HEAD + page + TAIL)

    icon(180, os.path.join(SITE, "icons/apple-touch-icon.png"))
    icon(192, os.path.join(SITE, "icons/icon-192.png"))
    icon(512, os.path.join(SITE, "icons/icon-512.png"))
    icon(512, os.path.join(SITE, "icons/icon-maskable-512.png"), pad=0.1)

    manifest = {
        "name": "NDS Pocket",
        "short_name": "NDS Pocket",
        "start_url": "./",
        "scope": "./",
        "display": "fullscreen",
        "display_override": ["fullscreen", "standalone"],
        "orientation": "any",
        "background_color": "#121417",
        "theme_color": "#121417",
        "lang": "ko",
        "icons": [
            {"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    with open(os.path.join(SITE, "manifest.webmanifest"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # cache list + version derived from the files, so any rebuild refreshes the cache
    files, h = [], hashlib.sha1()
    for root, _, names in os.walk(SITE):
        for n in sorted(names):
            rel = os.path.relpath(os.path.join(root, n), SITE).replace(os.sep, "/")
            if rel == "version.json" or rel.startswith("source/") or rel in ("README.md", "LICENSE", ".nojekyll"):
                continue
            files.append(rel)
            h.update(rel.encode()); h.update(open(os.path.join(root, n), "rb").read())
    files.sort()
    version = h.hexdigest()[:10]
    sw = f"""const CACHE = "ndsp-{version}";
const FILES = {json.dumps(["./"] + files)};
self.addEventListener("install", e => {{
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES.map(f => new Request(f, {{ cache: "reload" }})))).then(() => self.skipWaiting()));
}});
self.addEventListener("activate", e => {{
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
}});
// GitHub Pages can't send headers, so the worker adds the ones that make the page
// "cross-origin isolated": that is what lets the engine use several CPU cores.
function isolate(r) {{
  if (!r || r.status === 0 || r.type === "opaque") return r;
  const h = new Headers(r.headers);
  h.set("Cross-Origin-Opener-Policy", "same-origin");
  h.set("Cross-Origin-Embedder-Policy", "require-corp");
  h.set("Cross-Origin-Resource-Policy", "same-origin");
  return new Response(r.body, {{ status: r.status, statusText: r.statusText, headers: h }});
}}
self.addEventListener("fetch", e => {{
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin || u.pathname.endsWith("/version.json")) return;
  e.respondWith(caches.match(e.request, {{ ignoreSearch: true }}).then(r => r || fetch(e.request)).then(isolate));
}});
"""
    with open(os.path.join(SITE, "sw.js"), "w", encoding="utf-8") as f:
        f.write(sw)
    open(os.path.join(SITE, ".nojekyll"), "w").close()
    # repo docs and the sources behind the build (GPL), kept outside the offline cache list
    for f in ("README.md", "LICENSE"):
        shutil.copy(os.path.join(ROOT, "repo_extra", f), os.path.join(SITE, f))
    os.makedirs(os.path.join(SITE, "source"), exist_ok=True)
    for f in ("src/shell.html", "build.py", "build_pwa.py"):
        shutil.copy(os.path.join(ROOT, f), os.path.join(SITE, "source", os.path.basename(f)))
    print("site ready:", len(files), "files, cache", version)


if __name__ == "__main__":
    main()
