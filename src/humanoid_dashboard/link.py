"""Robot side of the dashboard: stream what the control loop already has, receive a few commands. Standard library
only, nothing blocks: meant to be called once per tick of the control loop.

    link = Link("Microban", fields={"q": joint_names, "imu_quat": ["w", "x", "y", "z"], ...}, meta={...})
    ...each tick:
    link.publish(q=positions, imu_quat=quat, ...)       # nothing is sent while no PC listens
    for cmd in link.commands():                         # e.g. {"name": "reboot", "args": {"joint": "left_knee"}}
        ...
        link.ack(cmd, ok=True, text="rebooted")
    link.event("overcurrent safety", level="error")

Protocol (UDP, one port on the robot):
* PC -> robot, JSON: {"op": "hello"} about once a second (subscribes for 3 s); {"op": "cmd", "seq", "name", "args"}.
* robot -> PC, JSON: {"op": "schema", "robot", "fields": [[name, [labels]], ...], "meta"} in answer to every hello;
  {"op": "ack", "seq", "ok", "text"}; {"op": "event", "level", "text", "t"}.
* robot -> PC, binary frame: MAGIC, uint32 schema id, uint32 sequence, float64 robot time, then float32 values in the
  schema's field order (NaN for a value not given this tick).

Sicherheit (Gabriella): with the shared key (secure.py) the robot takes hellos and commands only when signed
({"session", "seq", "sig"} added by the PC); an unsigned or stale hello gets a small {"op": "challenge", "session"}
(no data), anything else unsigned is dropped. Without a key on the robot: data for any hello, every command refused.
Malformed packets are dropped, at most MAX_CLIENTS PCs listen, and one call reads at most MAX_PACKETS packets.
"""
import json
import math
import socket
import struct
import time
import zlib

from .secure import Verifier, load_key

PORT = 7350
MAGIC = b"HDT1"
HEADER = struct.Struct("<4sIId")
SUBSCRIPTION_S = 3.0
# Sicherheit (Gabriella): limits against floods and malformed packets
MAX_PACKET_BYTES = 8192           # a command is ~300 bytes
MAX_PACKETS = 200                 # read per call: a flood cannot hold the control loop
MAX_COMMANDS = 50                 # kept per call, the rest dropped
MAX_CLIENTS = 4                   # PCs listening at once (forged hellos cannot fill the robot's memory)
MAX_NAME = 40
REJECT_LOG_S = 10.0               # dropped commands: one line in the robot's log at most this often
_KEY_FILE = object()              # Link(key=...) default: the key file of the user running the robot


class Link:
    def __init__(self, robot: str, fields: dict, meta: dict | None = None, port: int = PORT, max_hz: float | None = None,
                 key=_KEY_FILE):
        """max_hz: frames sent per second at most (None: every publish(); faster calls send one in a few).
        key: the shared key (bytes; None: no key, commands refused); by default read from secure.KEY_FILE."""
        self.auth = Verifier(load_key() if key is _KEY_FILE else key)      # Sicherheit (Gabriella)
        self.rejected, self._rejected_logged = 0, 0.0
        self.robot = robot
        self.min_period = 1.0 / max_hz if max_hz else 0.0
        self._last_sent = 0.0
        self.fields = [(name, list(labels)) for name, labels in fields.items()]
        self.meta = meta or {}
        self.size = sum(len(labels) for _, labels in self.fields)
        self.offset = {}
        k = 0
        for name, labels in self.fields:
            self.offset[name] = (k, len(labels))
            k += len(labels)
        self._set_schema()
        self.pack = struct.Struct(f"<{self.size}f").pack
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", port))
        self.sock.setblocking(False)
        self.clients = {}          # address -> last hello (monotonic s)
        self.seq = 0
        self._commands = []

    def _set_schema(self):
        self.schema = json.dumps({"op": "schema", "robot": self.robot, "fields": self.fields, "meta": self.meta,
                                  "session": self.auth.session, "auth": self.auth.key is not None}).encode()
        self.schema_id = zlib.crc32(self.schema)

    def set_meta(self, meta: dict) -> None:
        """New meta (e.g. settings changed): sent to the listening PCs now; the frames carry the new schema id."""
        self.meta = meta
        self._set_schema()
        for addr in self.clients:
            self._send(self.schema, addr)

    # ---- receiving ------------------------------------------------------------------------------------------------
    def _receive(self):
        for _ in range(MAX_PACKETS):              # Sicherheit (Gabriella): a flood cannot hold the control loop
            try:
                data, addr = self.sock.recvfrom(65536)
            except (BlockingIOError, InterruptedError):
                return
            except OSError:
                return
            if len(data) > MAX_PACKET_BYTES:
                continue
            try:                                  # Sicherheit (Gabriella): no packet, whatever it holds, stops the loop
                self._handle(data, addr)
            except Exception as e:  # noqa: BLE001 - on purpose: logged, never raised into the control loop
                print(f"dashboard link: packet from {addr[0]} dropped ({type(e).__name__})", flush=True)

    def _handle(self, data: bytes, addr) -> None:
        try:
            msg = json.loads(data)
        except (ValueError, RecursionError):
            return
        if not isinstance(msg, dict):         # Sicherheit (Gabriella): [1], 5, "x" are valid JSON too
            return
        op = msg.get("op")
        if op == "hello":
            if self.auth.key is None or self.auth.check(msg):
                if self._subscribe(addr):
                    self._send(self.schema, addr)
            else:                             # unsigned, or the session before a restart: tell it, no data
                challenge = {"op": "challenge", "session": self.auth.session,
                             "refused": msg.get("session") == self.auth.session and "sig" in msg}   # a wrong key
                self._send(json.dumps(challenge).encode(), addr)
        elif op == "cmd":
            name, args = msg.get("name"), msg.get("args") or {}
            if not isinstance(name, str) or len(name) > MAX_NAME or not isinstance(args, dict):
                return
            cmd = {"seq": msg.get("seq"), "name": name, "args": args, "addr": addr}
            if self.auth.key is None:
                self.ack(cmd, False, "no dashboard key on the robot: commands are off "
                                     "(make deploy copies the PC's key, then restart the robot's program)")
                return
            if not self.auth.check(msg):
                self._reject(addr)
                return
            self._subscribe(addr)
            if len(self._commands) < MAX_COMMANDS:
                self._commands.append(cmd)

    def _subscribe(self, addr) -> bool:
        """Sicherheit (Gabriella): at most MAX_CLIENTS listening PCs; a new one waits until one expired."""
        if addr not in self.clients and not self.listening_room():
            return False
        self.clients[addr] = time.monotonic()
        return True

    def listening_room(self) -> bool:
        _ = self.listening                        # drops the expired ones
        return len(self.clients) < MAX_CLIENTS

    def _reject(self, addr):
        """Sicherheit (Gabriella): a command without this robot's signature (another PC, a stranger, a replay)."""
        self.rejected += 1
        now = time.monotonic()
        if now - self._rejected_logged > REJECT_LOG_S:
            self._rejected_logged = now
            print(f"dashboard link: {self.rejected} command(s) without a valid signature dropped so far "
                  f"(last from {addr[0]})", flush=True)

    def commands(self) -> list:
        """Commands received since the last call (each a dict with name, args); answer each with ack()."""
        self._receive()
        out, self._commands = self._commands, []
        return out

    @property
    def listening(self) -> bool:
        now = time.monotonic()
        self.clients = {a: t for a, t in self.clients.items() if now - t < SUBSCRIPTION_S}
        return bool(self.clients)

    # ---- sending --------------------------------------------------------------------------------------------------
    def _send(self, data: bytes, addr):
        try:
            self.sock.sendto(data, addr)
        except OSError:        # full buffer, network down: telemetry never stops the robot
            pass

    def publish(self, **values) -> None:
        """One frame: each field by name (a number or a sequence in the field's label order). Costs nothing while
        no PC listens."""
        self._receive()
        if not self.listening:
            return
        now = time.monotonic()
        if now - self._last_sent < self.min_period:
            return
        self._last_sent = now
        buf = [math.nan] * self.size
        for name, v in values.items():
            if v is None or name not in self.offset:
                continue
            k, n = self.offset[name]
            if n == 1 and not hasattr(v, "__len__"):
                buf[k] = float(v)
            else:
                for i in range(min(n, len(v))):
                    buf[k + i] = float(v[i])
        self.seq += 1
        frame = HEADER.pack(MAGIC, self.schema_id, self.seq, time.monotonic()) + self.pack(*buf)
        for addr in self.clients:
            self._send(frame, addr)

    def ack(self, cmd: dict, ok: bool = True, text: str = "") -> None:
        self._send(json.dumps({"op": "ack", "seq": cmd.get("seq"), "name": cmd.get("name"), "ok": ok,
                               "text": text}).encode(), cmd["addr"])

    def event(self, text: str, level: str = "info") -> None:
        if not self.listening:
            return
        data = json.dumps({"op": "event", "level": level, "text": text, "t": time.monotonic()}).encode()
        for addr in self.clients:
            self._send(data, addr)

    def close(self) -> None:
        self.sock.close()
