# kitty → cat Rebrand Reference

Project: dylmarriner/cat (kitty terminal emulator fork)
Scope: 546 files content-changed, 19 files renamed, 2 directories renamed

## Replacement Strategy

Three-pass case-sensitive replacement, in order:
1. `KITTY` → `CAT` (all-caps)
2. `Kitty` → `Cat` (title case)
3. `kitty` → `cat` (lowercase, word-boundary only)

## Directories Renamed

| Old | New |
|-----|-----|
| `kitty/` | `cat/` |
| `kitty_tests/` | `cat_tests/` |
| `tools/cmd/edit_in_kitty/` | `tools/cmd/edit_in_cat/` |

## Files Renamed (19 total)

Logos: `kitty-128.png`, `kitty.icns`, `kitty.png`, `kitty.svg`
Shell integration: `kitty.bash`, `kitty.zsh`, `kitty-integration`, `_kitty` (completion), `kitty.fish`, `clone-in-kitty.fish`, `kitty-shell-integration.fish`
Terminfo: `kitty.terminfo`, `kitty.termcap`, `xterm-kitty`
Source: `cat/launcher/kitty-verstable.h` → `cat-verstable.h`
Kittens: `show_key/kitty.go` → `cat.go`, `tools/tui/dcs_to_kitty.go` → `dcs_to_cat.go`
SSH: `shell-integration/ssh/kitty` → `cat`

## Build System Fixes Required

### setup.py (3 changes)
- `KITTY_LIB_PATH` → `CAT_LIB_PATH` (line 1416)
- `KITTY_VERSION` → `CAT_VERSION` (line 1434)
- `KITTY_LIB_DIR_NAME` → `CAT_LIB_DIR_NAME` (line 1396)

### glfw/include path fixes (14 files)
All `#include "../kitty/"` references in `glfw/*.h`, `glfw/*.c`, `glfw/*.m`:
- `backend_utils.h`, `internal.h`, `main_loop.h`
- `dbus_glfw.c`, `input.c`, `momentum-scroll.c`, `monotonic.c`
- `null_window.c`, `window.c`, `wl_init.c`, `wl_window.c`, `x11_window.c`
- `cocoa_init.m`, `cocoa_window.m`

Also: `glfw/glfw.py` (2x `open('../kitty/...')` → `'../cat/...'`)
Also: `glad/generate.py` (1x `open('../kitty/...')` → `'../cat/...'`)

### Shell script wrapper paths
`shell-integration/ssh/cat` — printf message "kitty needs to be installed"

## CI Changes

### .github/workflows/ci.py
- `build_kitty()` → `build_cat()`, `test_kitty()` → `test_cat()`, `package_kitty()` → `package_cat()`
- `KITTY_BUNDLE` → `CAT_BUNDLE`, `KITTY_CODEQL` → `CAT_CODEQL`, `KITTY_SANITIZE` → `CAT_SANITIZE`
- Bundle URL: `kovidgoyal/kitty` → `dylmarriner/cat`
- App path: `kitty.app/Contents/MacOS/kitty` → `cat.app/Contents/MacOS/cat`
- Build dir: `/Users/Shared/kitty-build/sw/sw` → `/Users/Shared/cat-build/sw/sw`
- Kitten binary: `kitty/launcher/kitten` → `cat/launcher/kitten`
- CVE comment: "unused in kitty" → "unused in cat"

### .github/workflows/ci.yml
- Step names: "Build kitty" → "Build cat", "Test kitty" → "Test cat", "Build kitty package" → "Build cat package"
- Grep paths: `kitty kitty_tests` → `cat cat_tests`

### .github/workflows/codeql-analysis.yml
- Step name: "Build kitty" → "Build cat"

## Things to Leave As-Is

- External protocol specs: `docs/graphics-protocol.rst`, `docs/keyboard-protocol.rst`
  (these are standards that other terminals implement)
- 3rdparty code: `glad/`, `glfw/`, `3rdparty/` (internal comments/URLs referencing upstream)
- Logos: just the filenames change, not the image content
- Build defines in setup.py that are internal (KITTY_DEBUG_BUILD, KITTY_NO_SIMD — these are compile-time flags for 3rdparty code, not branding)
