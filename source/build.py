"""Build NDS Pocket: patch EmulatorJS so it runs from inline scripts + same-origin wasm files,
then inline everything into dist/index.html.

Usage: python3 build.py <emulatorjs data dir> <extracted cores dir>
"""
import json, os, shutil, sys

EJS, CORES = sys.argv[1], sys.argv[2]
ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
CORE_NAMES = ["desmume2015"]  # melonDS dropped in V05: it never rendered and doubled the download


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def must_replace(src, old, new):
    assert src.count(old) == 1, f"patch anchor not unique/missing: {old[:60]!r}"
    return src.replace(old, new)


def patched_emulator():
    s = read(os.path.join(EJS, "src/emulator.js"))
    # 1) Skip the .data core download when the core is embedded in the page.
    s = must_replace(s,
        '    downloadGameCore() {\n        this.textElem.innerText = this.localization("Download Game Core");\n',
        '    downloadGameCore() {\n        this.textElem.innerText = this.localization("Download Game Core");\n'
        '        const __emb = window.__EJS_CORES && window.__EJS_CORES[this.getCore()];\n'
        '        if (__emb) {\n'
        '            const meta = __emb.meta;\n'
        '            this.extensions = meta.extensions; this.coreName = meta.name; this.repository = meta.repo;\n'
        '            this.defaultCoreOpts = meta.options || {}; this.enableMouseLock = !!(meta.options && meta.options.supportsMouse);\n'
        '            this.retroarchOpts = meta.retroarchOpts; this.saveFileExt = meta.save;\n'
        '            if (this.webgl2Enabled === null) this.webgl2Enabled = true;\n'
        '            if (!this.supportsWebgl2) { this.startGameError(this.localization("Outdated graphics driver")); return; }\n'
        '            this.initGameCore(null, null, null);\n'
        '            return;\n'
        '        }\n')
    # 2) Run the embedded core runtime instead of injecting a blob: script.
    s = must_replace(s,
        '    initGameCore(js, wasm, thread) {\n',
        '    initGameCore(js, wasm, thread) {\n'
        '        if (js === null && window.__EJS_CORES && window.__EJS_CORES[this.getCore()]) {\n'
        '            const emb = window.__EJS_CORES[this.getCore()];\n'
        '            window.EJS_Runtime = emb.runtime();\n'
        '            // the engine ships gzip-compressed; unpack it in the browser, then hand emscripten a blob URL\n'
        '            const getBytes = emb.wasm.charAt(0) === "#"\n'
        '                ? Promise.resolve().then(() => { const t = document.getElementById(emb.wasm.slice(1)).textContent.trim(); const bin = atob(t); const u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u.buffer; })\n'
        '                : fetch(emb.wasm).then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.arrayBuffer(); });\n'
        '            getBytes.then(buf => {\n'
        '                const b = new Uint8Array(buf);\n'
        '                if (b[0] !== 0x1f || b[1] !== 0x8b) return buf;\n'
        '                return new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();\n'
        '            }).then(wasm => {\n'
        '                window.__EJS_WASM_BIN = new Uint8Array(wasm);\n'
        '                this.initModule(null, null);\n'
        '            }).catch(e => { console.error(e); this.startGameError(this.localization("Error downloading core")); });\n'
        '            return;\n'
        '        }\n')
    # 3) Point emscripten at the same-origin wasm file.
    s = must_replace(s,
        '                if (fileName.endsWith(".wasm")) {\n                    return URL.createObjectURL(new Blob([wasmData]',
        '                if (fileName.endsWith(".wasm") && window.__EJS_WASM_URL) return window.__EJS_WASM_URL;\n'
        '                if (fileName.endsWith(".wasm")) {\n                    return URL.createObjectURL(new Blob([wasmData]')
    # 2b) Only cores that ship with the page may be chosen: a saved pick of another core
    #     (e.g. melonds) made every launch try to download it and fail with "Network Error".
    s = must_replace(s,
        '        if (cores[gen] && cores[gen].includes(this.preGetSetting("retroarch_core"))) {',
        '        if (cores[gen] && cores[gen].includes(this.preGetSetting("retroarch_core")) && (!window.__EJS_CORES || window.__EJS_CORES[this.preGetSetting("retroarch_core")])) {')
    s = must_replace(s,
        '        const core = cores[this.getCore(true)];\n        if (core && core.length > 1) {',
        '        const core = cores[this.getCore(true)];\n        if (core && core.length > 1 && !window.__EJS_CORES) {')
    # 3b) Hand emscripten the unpacked engine bytes directly (no URL fetch).
    s = must_replace(s, "noInitialRun: true,", "noInitialRun: true, wasmBinary: window.__EJS_WASM_BIN,")
    # 4) No update check against an outside host.
    s = must_replace(s,
        'fetch("https://cdn.emulatorjs.org/stable/data/version.json")',
        'Promise.resolve({ ok: false })')
    return s


def script(js):
    # each piece is wrapped so one file's top-level declarations stay separate in the joined bundle
    return "\n;" + js + "\n;\n"


def write(rel, text):
    with open(os.path.join(DIST, rel), "w", encoding="utf-8") as f:
        f.write(text)


def main():
    if os.path.exists(DIST):
        shutil.rmtree(DIST)
    os.makedirs(os.path.join(DIST, "cores"))
    os.makedirs(os.path.join(DIST, "ejs/compression"))

    parts = []
    # emulator CSS is injected at launch time by the bundle
    parts.append("(function(){var s=document.createElement('style');s.textContent=" + json.dumps(read(os.path.join(EJS, "emulator.css"))) + ";document.head.appendChild(s);})();\n")
    # The upstream ko-KO.json is missing a comma after DPAD_RIGHT; repair it before embedding.
    ko = read(os.path.join(EJS, "localization/ko-KO.json"))
    ko = ko.replace('"DPAD_RIGHT": "DPAD_오른쪽"\n', '"DPAD_RIGHT": "DPAD_오른쪽",\n')
    ko = ko.replace('저장되었습니가', '저장되었습니다')
    parts.append(script("window.__EJS_LANG_KO = " + json.dumps(json.loads(ko)) + ";"))
    order = ["nipplejs.js", "shaders.js", "storage.js", "gamepad.js", "GameManager.js", "socket.io.min.js", "compression.js"]
    parts.append(script(patched_emulator()))
    for f in order:
        parts.append(script(read(os.path.join(EJS, "src", f))))

    for c in CORE_NAMES:
        d = os.path.join(CORES, c)
        meta = json.load(open(os.path.join(d, "core.json"), encoding="utf-8"))
        js = read(os.path.join(d, f"{c}_libretro.js"))
        wasm_name = f"{c}_libretro.gz.wasm"  # gzip bytes under a served extension; unpacked in the browser
        import gzip
        with open(os.path.join(d, f"{c}_libretro.wasm"), "rb") as src, open(os.path.join(DIST, "cores", wasm_name), "wb") as dst:
            dst.write(gzip.compress(src.read(), 9, mtime=0))
        write(f"cores/{c}.js",
            "window.__EJS_CORES = window.__EJS_CORES || {};\n"
            f"window.__EJS_CORES[{json.dumps(c)}] = {{ meta: {json.dumps(meta)}, wasm: {json.dumps('cores/' + wasm_name)},\n"
            "runtime: function () {\n" + js + "\n;return EJS_Runtime; } };\n")

    for f in ["extractzip.js"]:
        shutil.copy(os.path.join(EJS, "compression", f), os.path.join(DIST, "ejs/compression", f))

    write("ejs/bundle.js", "".join(parts))
    shell = read(os.path.join(ROOT, "src/shell.html"))
    import datetime
    stamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec="minutes")
    vinfo = json.load(open(os.path.join(ROOT, "src/version.json"), encoding="utf-8"))
    vinfo["stamp"] = stamp
    shell = shell.replace("__VERSION_JSON__", json.dumps(vinfo, ensure_ascii=False))
    write("version.json", json.dumps(vinfo, ensure_ascii=False, indent=1))
    write("index.html", shell.replace("<!--EJS_BUNDLE-->", ""))

    # Single-file page (no supporting files): the Claude app viewer will only open those.
    # Scripts inline; the gzip'd engine rides along as base64 in a script block that never executes.
    import base64
    def inline(js):
        return "<script>\n" + js.replace("</script", "<\\/script") + "\n</script>\n"
    blocks = [inline("".join(parts))]
    for c in CORE_NAMES:
        core_js = read(os.path.join(DIST, f"cores/{c}.js")).replace(
            json.dumps("cores/" + f"{c}_libretro.gz.wasm"), json.dumps("#wasm-" + c))
        blocks.append(inline(core_js))
        gz = open(os.path.join(DIST, "cores", f"{c}_libretro.gz.wasm"), "rb").read()
        blocks.append(f'<script type="application/octet-stream" id="wasm-{c}">' + base64.b64encode(gz).decode() + "</script>\n")
    write("single.html", shell.replace("<!--EJS_BUNDLE-->", "".join(blocks)))
    for root, _, files in os.walk(DIST):
        for f in files:
            p = os.path.join(root, f)
            print(f"{os.path.getsize(p):>9}  {os.path.relpath(p, DIST)}")


if __name__ == "__main__":
    main()
