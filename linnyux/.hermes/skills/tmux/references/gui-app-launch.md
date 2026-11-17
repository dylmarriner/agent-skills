# GUI apps in tmux

Use tmux when you want a GUI app to keep running after the shell closes, or when you want its logs in a stable session.

Session pattern:

```bash
tmux new-session -d -s openhuman 'cd /path/to/repo && openhuman'
tmux capture-pane -t openhuman -p -S - | tail -40
```

Practical points:
- Launch from the desktop shell environment if the app needs display access.
- If it exits immediately, capture the pane and read the first failure line; GUI apps often print the real cause before they disappear.
- Prefer a single detached session per app so the pane stays readable.
- For long-running desktop apps, `tmux attach -t <session>` is the quickest way to watch startup logs in real time.
