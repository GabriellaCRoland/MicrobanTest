# Sicherheit (Gabriella): not in Rhoban's original. See ZIEL.md, "Schnittstellen-Sicherheit".
"""Who may command the robot over the dashboard link: only a PC that holds the shared key.

Every hello and command from the PC carries the robot's session (a random number drawn at each robot start), a
number that only ever grows, and an HMAC-SHA256 of all that with the shared key. The robot drops what is not signed
with its key (a stranger on the same wifi), what it saw already (a captured packet sent again) and what belongs to an
earlier session (a packet from before the robot restarted).

The key is a file outside the repository, readable by its owner only: ~/.config/humanoid_dashboard/key. The PC makes
it at the dashboard's first start; `make deploy` copies it to the robot. A robot without it only shows its data: every
command is refused.

    python src/humanoid_dashboard/secure.py --ensure      # makes the key if missing, prints its path
"""
import hashlib
import hmac
import json
import os
import pathlib
import secrets
import sys
import time

KEY_FILE = pathlib.Path.home() / ".config" / "humanoid_dashboard" / "key"
KEY_BYTES = 32


def load_key(path: pathlib.Path = KEY_FILE, create: bool = False) -> bytes | None:
    """The shared key, or None without one (create: make a new one first, readable by its owner only)."""
    path = pathlib.Path(path)
    if not path.is_file():
        if not create:
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)     # never readable by others, not even briefly
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_hex(KEY_BYTES) + "\n")
    text = path.read_text().strip()
    try:
        key = bytes.fromhex(text)
    except ValueError:
        return None
    return key if len(key) >= 16 else None


def _canonical(msg: dict) -> bytes:
    return json.dumps({k: v for k, v in msg.items() if k != "sig"}, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode()


def sign(key: bytes, msg: dict) -> str:
    return hmac.new(key, _canonical(msg), hashlib.sha256).hexdigest()


class Signer:
    """PC side: adds the robot's session, the next number and the signature to what it sends."""

    def __init__(self, key: bytes | None):
        self.key = key
        self.session = None                       # the robot's, from its schema or its challenge
        self._seq = int(time.time() * 1000)       # grows across the PC's restarts too (a robot remembers the last)

    def wrap(self, msg: dict) -> dict:
        if self.key is None or self.session is None:
            return msg                            # the robot answers with its session (a challenge) first
        self._seq += 1
        out = {**msg, "session": self.session, "seq": self._seq}
        out["sig"] = sign(self.key, out)
        return out


class Verifier:
    """Robot side: accepts a message once, only with this session's number above the last one, signed with the key."""

    def __init__(self, key: bytes | None):
        self.key = key
        self.session = secrets.token_hex(8)       # new at each start: packets of an earlier session never count
        self.last_seq = 0

    def check(self, msg: dict) -> bool:
        if self.key is None:
            return False
        sig, seq = msg.get("sig"), msg.get("seq")
        if not isinstance(sig, str) or msg.get("session") != self.session:
            return False
        if not isinstance(seq, int) or isinstance(seq, bool) or seq <= self.last_seq:
            return False
        if not hmac.compare_digest(sig, sign(self.key, msg)):
            return False
        self.last_seq = seq                       # only a signed message moves it: a stranger cannot block the PC
        return True


if __name__ == "__main__":
    if sys.argv[1:] == ["--ensure"]:
        if load_key(create=True) is None:
            raise SystemExit(f"{KEY_FILE} is not a valid key: delete it and run this again")
        print(KEY_FILE)
    else:
        raise SystemExit(__doc__)
