# Mega.nz Downloads (megadl)

## When to use

- User provides a `mega.nz/folder/<id>#<key>` or `mega.nz/folder/<id>#<key>/folder/<subid>` URL
- Videos are hosted on Mega.nz behind an exported folder link with decryption key

## Tools

**megadl** (part of `megatools` package) — works on exported folder/file links with keys.

Check installation:
```bash
which megadl   # usually /usr/bin/megadl (part of megatools)
```

Also available: `mega.py` Python library (pip install mega.py in a venv due to PEP 668).

## Usage

### Download all files from a MEGA folder to current directory

```bash
megadl "https://mega.nz/folder/<folder_id>#<key>"
```

Files are downloaded sequentially (one at a time) to the working directory. Progress is shown as percentage + MiB + speed.

### Download to a specific path

```bash
megadl --path "/mnt/pivideos/videos/" "https://mega.nz/folder/<folder_id>#<key>"
```

### List files (without full download)

`megadl` has no pure-listing mode. `--print-names` prints names as they download but doesn't stop the download.

Workaround: use `--choose-files` for interactive selection (not useful for automation).

### Run in background

```bash
megadl "https://mega.nz/folder/<id>#<key>" &
```

Or use Hermes terminal with `background=true`.

## Known patterns

- **Subfolder URLs**: `https://mega.nz/folder/<parent_id>#<key>/folder/<sub_id>` works the same way — megadl traverses into the subfolder.
- **Sequential download**: Files download one after another; megadl handles the queue itself.
- **Decryption errors**: Some files may warn "key can't be decrypted" and be skipped. These are likely access-restricted or corrupt files.
- **No partial resume state visible**: megadl doesn't leave `.part` files like yt-dlp — it writes to the final filename during download.

## Limitations

- No way to list files before downloading (use the web UI or mega.py for that)
- Slower than yt-dlp for the same file size (single-threaded download)
- Subfolder traversal works but you can't selectively download individual files
- No progress bar in non-interactive mode
