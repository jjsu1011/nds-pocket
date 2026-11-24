# How the engine in `cores/` is built (V27 and later)

From V27 the engine files in `cores/` are built from source instead of using the prebuilt
EmulatorJS package. Nothing in the emulator code is changed; only the build setup below.

## Sources

| Part | Repository | Commit |
|---|---|---|
| DeSmuME 2015 libretro core | https://github.com/EmulatorJS/desmume2015 | `b4ae0af744cf8f7895f3586ece449f876f3142e6` |
| RetroArch (web front-end) | https://github.com/EmulatorJS/RetroArch | `97f2cfa65d01d57406e4ce9459242c8ada7c7e3b` |
| zlib | https://github.com/madler/zlib | tag `v1.2.13` |
| Emscripten | https://github.com/emscripten-core/emscripten | tag `3.1.74` |

Compiler back-end: wasi-sdk 27 (clang 20) and binaryen version_121, from their GitHub releases.

## Steps

1. Core: in `desmume2015/desmume`,
   `emmake make -f Makefile.libretro platform=emscripten`
   (threaded engine: add `EMULATORJS_THREADS=1`).
2. zlib: compile the 15 library `.c` files with `emcc -O2 -DHAVE_UNISTD_H -c` and archive them
   into `libz.a` with `emar rcs`. This replaces Emscripten's automatic zlib download.
3. RetroArch: apply `Makefile.emulatorjs-local-zlib.patch` (points the build at the zlib above),
   copy the core's `.bc` to `libretro_emscripten.a`, then
   `emmake make -f Makefile.emulatorjs ZLIB_DIR=<zlib folder> HAVE_7ZIP=1 HAVE_CHD=1 HAVE_THREADS=0 PTHREAD_POOL_SIZE=0 ASYNC=0 HAVE_OPENGLES3=1 STACK_SIZE=4194304 INITIAL_HEAP=134217728 HAVE_AL=0 HAVE_RWEBAUDIO=1 LIGHT_DEBUG=0 TARGET=desmume2015_libretro.js`
   (threaded engine: `HAVE_THREADS=1 PTHREAD_POOL_SIZE=4`).
4. Package with `source/build.py` as before (it wraps the `.js` and gzip-compresses the `.wasm`).
