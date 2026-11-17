#!/usr/bin/env python3
"""Print the RustDesk permanent password stored in the local RustDesk.toml.

RustDesk stores `enc_id` and `password` as "00" + base64(secretbox(plaintext))
using XSalsa20-Poly1305, key = machine-uid truncated/padded to 32 bytes, nonce =
24 zero bytes (deterministic). The tool itself prints the decrypted `enc_id` as
`rustdesk --get-id`, so a matching decrypt is a free test vector: if enc_id comes
back as the same digits the ID command printed, the password below it is real.

Run ON the machine that owns the config:
    sudo apt-get install -y python3-nacl
    ssh <host> 'python3 -' < scripts/rd_toml_secrets.py

Read-only: never writes the config. Optional argv[1] = path to RustDesk.toml.
"""
import base64
import pathlib
import sys
import tomllib

ZERO_NONCE = b"\x00" * 24


def candidate_keys(cfg):
    """machine-id first (Linux), then the Ed25519 public key fallback."""
    for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        f = pathlib.Path(path)
        if f.exists():
            uid = f.read_text().strip()
            if uid:
                yield "machine-id", uid.encode()[:32].ljust(32, b"\x00")
            break
    kp = cfg.get("key_pair")
    if isinstance(kp, list) and kp and isinstance(kp[0], list):
        yield "ed25519-pub", bytes(kp[0])[:32].ljust(32, b"\x00")


def decrypt(value, key):
    """'00' + base64 secretbox -> plaintext, or None if this key is not it."""
    if not isinstance(value, str) or not value.startswith("00"):
        return None
    body = value[2:]
    try:
        from nacl.secret import SecretBox

        blob = base64.b64decode(body + "=" * (-len(body) % 4))
        return SecretBox(key).decrypt(blob, ZERO_NONCE).decode()
    except Exception:
        return None


def main(argv):
    path = (
        pathlib.Path(argv[1])
        if len(argv) > 1
        else pathlib.Path.home() / ".config/rustdesk/RustDesk.toml"
    )
    if not path.exists():
        print(f"no rustdesk config at {path}", file=sys.stderr)
        return 2
    cfg = tomllib.loads(path.read_text())
    for name, key in candidate_keys(cfg):
        peer_id = decrypt(cfg.get("enc_id"), key)
        print(f"key={name}  enc_id -> {peer_id}")
        if peer_id is not None:
            print(f"key={name}  PASSWORD -> {decrypt(cfg.get('password'), key)}")
            print("cross-check enc_id against `rustdesk --get-id`", file=sys.stderr)
            return 0
    print(
        "no candidate key decrypted enc_id; cross-check `rustdesk --get-id` before "
        "assuming no password is set",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
