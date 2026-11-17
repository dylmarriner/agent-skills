# Windows PowerShell Hermes Installer Quirks

Debugging history from building the `install.ps1` for `Hermesconfig` repo deployment.

## 1. UTF-8 BOM kills config.yaml

**Symptom**: Hermes returns HTTP 400 "No models provided" on startup after config is written by the installer.

**Root cause**: `Set-Content -Path config.yaml -Value $content -Encoding UTF8` in Windows PowerShell 5.1 writes a UTF-8 **with BOM** (`0xEF 0xBB 0xBF` prefix). Hermes's YAML parser chokes on it.

**Fix**: Always write config files without BOM:

```powershell
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[IO.File]::WriteAllText($path, $content, $utf8NoBom)
```

Or for simple ASCII content (`.bat` files, .sh scripts):

```powershell
[IO.File]::WriteAllText($path, $content, [System.Text.Encoding]::ASCII)
```

## 2. `$ErrorActionPreference = "Stop"` is too aggressive

**Symptom**: Script dies on non-fatal errors — stale temp dir, git clone failure on first attempt, Copy-Item to a path that needs admin.

**Fix**: Use `"Continue"` and track errors manually:

```powershell
$ErrorActionPreference = "Continue"
$script:errCount = 0
# ...
if ($condition) { $script:errCount++ }
```

## 3. `$MyInvocation.MyCommand.Path` breaks under iex

**Symptom**: The "re-run this script" instruction at the end shows:
```
powershell -ExecutionPolicy Bypass -File
```
with nothing after `-File`.

**Root cause**: When run via `irm https://.../install.ps1 | iex`, the script is eval'd from a string — there is no script file path. `$MyInvocation.MyCommand.Path` returns empty string.

**Fix**: Use a hardcoded URL string for the re-run instruction, or detect iex context:

```powershell
$rerunCmd = "irm https://raw.githubusercontent.com/<user>/<repo>/main/install.ps1 | iex"
Write-Step "Re-run: powershell -ExecutionPolicy Bypass -c `"$rerunCmd`""
```

## 4. Exit code after piped git commands

**Symptom**: `git pull 2>&1 | Out-Null` runs but `$LASTEXITCODE` reports 0 even when the pull failed.

**Root cause**: Piping git's output through `| Out-Null` with redirection `2>&1` swallows the process exit code in some PowerShell versions. `$?` may also be unreliable after pipelines.

**Fix**: Don't pipe git output when you need the exit code. Capture separately:

```powershell
git pull --ff-only 2>&1 | Tee-Object -Variable pullOut | Out-Null
if ($LASTEXITCODE -ne 0) { ... }
```

Or drop `Out-Null` and redirect to a log file:

```powershell
git pull --ff-only >> "$logFile" 2>&1
if ($LASTEXITCODE -ne 0) { ... }
```

## 5. Stale temp dir prevents clone

**Symptom**: Second run of the installer on the same machine logs "Updating existing clone..." then fails with "Clone failed."

**Root cause**: The `$env:TEMP\Hermesconfig` dir exists (from a previous run) but either has no `.git` (incomplete first clone, manual deletion, or leftover files) or the git repo is corrupt.

**Fix**: Always check for `.git` specifically, not just directory existence:

```powershell
if (Test-Path "$repoDir\.git") {
    # Safe to pull
    Push-Location $repoDir
    git pull --ff-only 2>&1 | Out-Null
    Pop-Location
} elseif (Test-Path $repoDir) {
    # Stale — clean and re-clone
    Remove-Item -Recurse -Force $repoDir -ErrorAction SilentlyContinue
    git clone $RepoUrl $repoDir
} else {
    git clone $RepoUrl $repoDir
}
```

## 6. `Invoke-RestMethod` vs `Invoke-WebRequest`

The one-liner `irm ... | iex` uses `Invoke-RestMethod` (shorthand `irm`) which returns the raw text of the script. `Invoke-WebRequest` (shorthand `iwr`) returns a `BasicHtmlWebResponseObject` and needs `.Content` extraction.

**Use `irm` for iex pipelines, not `iwr`.**

```powershell
# Correct
irm https://raw.githubusercontent.com/.../install.ps1 | iex

# Wrong — passes an object, not text
iwr https://raw.githubusercontent.com/.../install.ps1 | iex
```

## 7. `Write-Skip` doesn't skip — it just prints

If your script has a `Write-Skip` function that only prints a message but doesn't `continue`/`return`, the fallthrough still executes the copy below it. Either:

a) Use `if-else` blocks (the fallthrough is by design — the `else` block is what actually runs):

```powershell
if (Test-Path $dst -and -not $f.Overwrite) {
    Write-Host "  [SKIP] $fName" -ForegroundColor Yellow
} else {
    Copy-Item ... -Force
}
```

b) Or use `return`/`continue` inside the loop:

```powershell
if (Test-Path $dst -and -not $f.Overwrite) {
    Write-Host "  [SKIP] $fName" -ForegroundColor Yellow
    continue
}
Copy-Item ... -Force
```

## 8. Batch file escaping in here-strings

When writing a `.bat` file from PowerShell, `%DATE%`, `%TIME%`, `%ERRORLEVEL%` are literal in the `.bat` runtime and must NOT be escaped for PowerShell. However, `%USERPROFILE%` is a PowerShell variable too:

```powershell
$batContent = @"
echo [%DATE% %TIME%] Start >> "%USERPROFILE%\.hermes\log.txt"
"@
```

In a double-quoted here-string `@"..."@`, `%USERPROFILE%` is NOT expanded by PowerShell (it uses `$` for variable expansion, not `%`). So `%USERPROFILE%` passes through verbatim to the `.bat` file, where cmd.exe expands it correctly. This works correctly.

But `$env:USERPROFILE` WOULD be expanded by PowerShell. Don't mix them.
