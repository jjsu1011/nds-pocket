# NDS Pocket

A personal web front-end for a Nintendo DS emulator, made to run on an iPhone as a home-screen web app.

**No game files are included or linked.** This repository contains no ROMs, no BIOS or firmware images, and no game assets. The page starts with an empty library; you add `.nds` files that you dumped yourself from cartridges you own. ROMs and save data stay in your own browser's storage on your device and are never uploaded anywhere.

개인용 닌텐도 DS 에뮬레이터 화면입니다. 롬, BIOS, 펌웨어, 게임 자료는 포함하지 않으며 다운로드 링크도 없습니다. 본인이 소유한 카트리지에서 직접 추출한 파일만 사용하세요. 롬과 세이브는 각자의 기기 브라우저 안에만 저장되고 어디에도 업로드되지 않습니다.

## What's inside

- `index.html` — the app (library, screen layouts, controls)
- `ejs/bundle.js` — [EmulatorJS](https://github.com/EmulatorJS/EmulatorJS) 4.2.3 with small patches (loads the engine from this site, no update check)
- `cores/` — the [DeSmuME](https://github.com/TASEmulators/desmume) 2015 libretro core as built by EmulatorJS (`@emulatorjs/core-desmume2015` 4.2.3), engine binary gzip-compressed
- `source/` — the build scripts and app source used to produce the files above
- `sw.js`, `manifest.webmanifest`, `icons/` — home-screen install and offline support

## License

GPL-3.0 (see `LICENSE`), following EmulatorJS (GPL-3.0) and DeSmuME (GPL-2.0-or-later).
Nintendo DS is a trademark of Nintendo. This project is not affiliated with or endorsed by Nintendo.
