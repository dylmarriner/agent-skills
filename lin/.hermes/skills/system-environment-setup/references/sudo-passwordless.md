# Passwordless Sudo: Non-Interactive Setup

## The Standard Way (when you have a terminal)

Create a drop-in file in `/etc/sudoers.d/`:

```bash
echo 'username ALL=(ALL) NOPASSWD: ALL' | sudo tee /etc/sudoers.d/username-nopasswd
sudo chmod 440 /etc/sudoers.d/username-nopasswd
```

Replace `username` with the target user. Drop-in files survive package updates and are cleaner than editing the main sudoers file.

## The Non-Interactive Workaround (automated/agent contexts)

When sudo requires a password but you're in a non-interactive context (no PTY, no way to type), pipe the password with `sudo -S`:

```bash
echo 'password' | sudo -S sh -c 'command_that_needs_sudo'
```

**Critical detail: use `sh -c`** — without it, the pipe from `echo` provides both the sudo password (consumed by `-S`) AND the stdin of the command. `sh -c` decouples them: sudo reads the password from the pipe, then the shell command runs independently.

### Wrong (stdin collision):
```bash
echo 'password' | sudo -S tee /etc/sudoers.d/x <<< 'content'   # <<< also uses stdin
```

### Right:
```bash
echo 'password' | sudo -S sh -c 'echo "content" > /etc/sudoers.d/x && chmod 440 /etc/sudoers.d/x'
```

## Verify

```bash
sudo -n true && echo "Passwordless sudo OK"
```

`sudo -n` (non-interactive) succeeds only if no password is required.
