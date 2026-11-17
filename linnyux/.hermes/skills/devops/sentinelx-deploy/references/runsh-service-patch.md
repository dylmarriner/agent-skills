# run.sh ↔ systemd coexistence patch

`run.sh` unconditionally runs `fuser -k 5000/tcp` before boot and again on exit, so a running
`sentinelx.service` gets killed and then auto-restarts (`Restart=on-failure`) — the two fight for
the port and run.sh's Flask child loses the bind race with a confusing "Address already in use".

Insert this immediately after `trap cleanup INT TERM EXIT`:

```bash
# 0. Release the systemd user service if it already owns the dashboard port
if systemctl --user is-active --quiet sentinelx.service 2>/dev/null; then
    echo -e "${YELLOW}[!] sentinelx.service is running. Stopping it so this launcher owns port 5000...${NC}"
    systemctl --user stop sentinelx.service 2>/dev/null || true
    sleep 0.5
    echo -e "${CYAN}[*] Restart it later with: systemctl --user start sentinelx.service${NC}"
fi
```

Then the launcher owns port 5000 for its whole lifetime and Ctrl+C shuts only what it started
(Ollama is left alone when it was already running as a system service).

## Testing the shutdown path

Run it in a real foreground terminal. `timeout -s INT 15 bash ./run.sh` is the automated
equivalent; the launcher must print `[*] Shutting down SentinelX...` / `[+] All processes cleanly
stopped.` and leave port 5000 free. If you background it with `&`, the trap never fires — bash sets
SIGINT to SIG_IGN for asynchronously started non-interactive shells and POSIX forbids trapping it,
so the Flask child is orphaned. Any stubbed `xdg-open` earlier in `$PATH` suppresses the browser pop.
