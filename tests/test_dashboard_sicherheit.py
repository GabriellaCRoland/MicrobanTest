# Sicherheit (Gabriella): tests for ZIEL.md, "Schnittstellen-Sicherheit" (S1-S11). Real UDP packets on 127.0.0.1.
#   PYTHONPATH=src uv run --no-project --python 3.12 --with pytest pytest -q tests/test_dashboard_sicherheit.py
import json
import math
import os
import socket
import sys
import time
import types

import pytest

from humanoid_dashboard.link import MAX_CLIENTS, Link
from humanoid_dashboard.secure import Signer, load_key, sign

KEY = bytes(range(32))
OTHER_KEY = bytes(range(1, 33))


# ---------------------------------------------------------------------------------------------------------- helpers
@pytest.fixture
def link():
    lk = Link("test", fields={"q": ["a", "b"]}, meta={"commands": ["reboot"]}, port=0, key=KEY)
    yield lk
    lk.close()


@pytest.fixture
def pc():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    s.settimeout(0.3)
    yield s
    s.close()


def addr(lk):
    return ("127.0.0.1", lk.sock.getsockname()[1])


def send(sock, lk, msg):
    sock.sendto(msg if isinstance(msg, bytes) else json.dumps(msg).encode(), addr(lk))


def collect(lk, wait=0.15):
    """The commands the robot accepted (polled a little: UDP on loopback is fast, not instant)."""
    out, end = [], time.monotonic() + wait
    while time.monotonic() < end:
        out += lk.commands()
        time.sleep(0.01)
    return out


def replies(sock):
    out = []
    try:
        while True:
            data, _ = sock.recvfrom(65536)
            out.append(json.loads(data) if data[:1] == b"{" else {"op": "frame"})
    except TimeoutError:
        return out


def signer_for(lk, key=KEY):
    s = Signer(key)
    s.session = lk.auth.session
    return s


def cmd(name="reboot", **args):
    return {"op": "cmd", "seq": 1, "name": name, "args": args or {"joint": "a"}}


# --------------------------------------------------------------------------------------------- control: it works
def test_signierter_befehl_kommt_an(link, pc):
    send(pc, link, signer_for(link).wrap(cmd()))
    got = collect(link)
    assert [c["name"] for c in got] == ["reboot"]
    assert got[0]["args"] == {"joint": "a"}


# -------------------------------------------------------------------------------------------------------- S1 - S3
def test_s1_befehl_ohne_signatur_wird_verworfen(link, pc):
    """S1: Befehl ohne oder mit falscher Signatur (fremder Rechner im WLAN) -> verworfen, nicht ausgeführt."""
    send(pc, link, cmd())                                             # no signature at all
    send(pc, link, signer_for(link, OTHER_KEY).wrap(cmd()))           # signed with another key
    forged = signer_for(link).wrap(cmd())
    forged["args"] = {"joint": "b"}                                   # signed, then changed on the way
    send(pc, link, forged)
    assert collect(link) == []
    assert link.rejected == 3
    assert replies(pc) == []                                          # a stranger gets no answer either


def test_s2_wiederholter_befehl_wird_verworfen(link, pc):
    """S2: Mitgeschnittener gültiger Befehl wird erneut gesendet -> verworfen."""
    packet = json.dumps(signer_for(link).wrap(cmd())).encode()
    send(pc, link, packet)
    send(pc, link, packet)
    send(pc, link, packet)
    assert len(collect(link)) == 1


def test_s3_befehl_alter_sitzung_wird_verworfen(link, pc):
    """S3: Gültiger Befehl aus einer früheren Sitzung (Roboter neu gestartet) -> verworfen."""
    old = signer_for(link)
    old.session = "0123456789abcdef"                                  # the session before the restart
    send(pc, link, old.wrap(cmd()))
    assert collect(link) == []
    restarted = Link("test", fields={"q": ["a"]}, port=0, key=KEY)    # same key, new session
    try:
        packet = signer_for(link).wrap(cmd())                         # valid for the first robot only
        send(pc, restarted, packet)
        assert collect(restarted) == []
    finally:
        restarted.close()


# ------------------------------------------------------------------------------------------------------------- S4
@pytest.mark.parametrize("packet", [
    b"not json", b"[1]", b"5", b'"cmd"', b"null", b"{}",
    b'{"op": "cmd", "name": ["reboot"], "args": {}}',
    b'{"op": "cmd", "name": "reboot", "args": [1, 2]}',
    b'{"op": "cmd", "name": "' + b"x" * 100 + b'", "args": {}}',
    b'{"op": "hello", "seq": 1e999, "session": [], "sig": 5}',
    b"[" * 8000,                                                      # deep nesting: RecursionError in json
    b'{"op": "cmd", "pad": "' + b"x" * 9000 + b'"}',                  # too big
])
def test_s4_kaputte_pakete_stoppen_die_schleife_nicht(link, pc, packet):
    """S4: Kaputtes Paket -> ignoriert, Regelschleife läuft weiter (danach kommt ein gültiger Befehl an)."""
    send(pc, link, packet)
    assert collect(link, 0.05) == []
    send(pc, link, signer_for(link).wrap(cmd()))
    assert [c["name"] for c in collect(link)] == ["reboot"]


@pytest.mark.parametrize("depth", [500, 900, 990, 2000, 4000])
def test_s4_tiefe_verschachtelung_mit_sitzung(link, pc, depth):
    """S4: Gültige (öffentliche) Sitzung, falsche Signatur, tief verschachteltes Feld -> verworfen, kein Absturz."""
    nest = "[" * depth + "1" + "]" * depth
    body = f'{{"op":"cmd","session":"{link.auth.session}","seq":5,"sig":"x","name":"a","args":{{}},"x":{nest}}}'.encode()
    send(pc, link, body)
    assert collect(link, 0.05) == []
    send(pc, link, signer_for(link).wrap(cmd()))
    assert [c["name"] for c in collect(link)] == ["reboot"]


def test_s4_fehler_im_link_stoppt_tick_nicht(tel):
    """S4: Jede unerwartete Ausnahme im Dashboard-Teil (publish, commands) -> tick() kehrt normal zurück."""
    def kaputt(**_):
        raise RecursionError("simuliert")
    tel.link.publish = kaputt
    tel.tick(_state(), {}, 20.0)                                      # must not raise
    tel.link.publish = lambda **_: None
    tel.link.commands = lambda: (_ for _ in ()).throw(OSError("simuliert"))
    tel.tick(_state(), {}, 20.0)                                      # must not raise


def test_s4_flut_haelt_die_schleife_nicht_an(link, pc):
    """S4: Eine Flut von Paketen wird je Aufruf nur begrenzt gelesen (die Schleife kommt immer zurück)."""
    for _ in range(1000):
        send(pc, link, b"x")
    time.sleep(0.1)
    t = time.perf_counter()
    link.commands()
    assert time.perf_counter() - t < 0.05


# -------------------------------------------------------------------------------------------------------- S5, S6
def test_s5_hello_ohne_signatur_bekommt_keine_daten(link, pc):
    """S5: Unsigniertes hello -> mit Schlüssel keine Daten, kein Abo, nur die kleine challenge."""
    send(pc, link, {"op": "hello"})
    link.commands()
    link.publish(q=[1.0, 2.0])
    got = replies(pc)
    assert [m["op"] for m in got] == ["challenge"]
    assert got[0]["session"] == link.auth.session
    assert got[0]["refused"] is False                                 # unsigned: not a wrong key, just no session yet
    assert not link.listening


def test_s5_hello_mit_falschem_schluessel_wird_gemeldet(link, pc):
    send(pc, link, signer_for(link, OTHER_KEY).wrap({"op": "hello"}))
    link.commands()
    got = replies(pc)
    assert [m["op"] for m in got] == ["challenge"] and got[0]["refused"] is True
    assert not link.listening


def test_s5_signiertes_hello_bekommt_daten(link, pc):
    send(pc, link, signer_for(link).wrap({"op": "hello"}))
    link.commands()
    link.publish(q=[1.0, 2.0])
    ops = [m["op"] for m in replies(pc)]
    assert ops == ["schema", "frame"]


def test_s6_abonnenten_sind_begrenzt(link):
    """S6: Viele hello von verschiedenen Absendern -> höchstens MAX_CLIENTS gleichzeitig."""
    s = signer_for(link)
    socks = []
    try:
        for _ in range(MAX_CLIENTS + 6):
            p = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            p.bind(("127.0.0.1", 0))
            socks.append(p)
            send(p, link, s.wrap({"op": "hello"}))
        collect(link)
        assert len(link.clients) == MAX_CLIENTS
    finally:
        for p in socks:
            p.close()


# ------------------------------------------------------------------------------------------------------------- S8
def test_s8_ohne_schluessel_nur_anzeigen(pc):
    """S8: Kein Schlüssel auf dem Roboter -> Messdaten ja, jeder Befehl abgelehnt mit Hinweis."""
    lk = Link("test", fields={"q": ["a"]}, port=0, key=None)
    try:
        send(pc, lk, {"op": "hello"})
        lk.commands()
        lk.publish(q=[1.0])
        got = replies(pc)
        assert [m["op"] for m in got] == ["schema", "frame"]
        assert got[0]["auth"] is False
        send(pc, lk, cmd())
        send(pc, lk, Signer(KEY).wrap(cmd()))
        assert collect(lk) == []
        acks = [m for m in replies(pc) if m["op"] == "ack"]
        assert len(acks) == 2 and not any(a["ok"] for a in acks)
        assert "no dashboard key" in acks[0]["text"]
    finally:
        lk.close()


# ------------------------------------------------------------------------------------------------------------ S11
def test_s11_schluessel_wird_privat_angelegt(tmp_path):
    """S11: Schlüsseldatei wird zufällig und nur für den Besitzer lesbar angelegt, bleibt danach gleich."""
    path = tmp_path / "sub" / "key"
    assert load_key(path) is None                                     # not made without create
    key = load_key(path, create=True)
    assert key is not None and len(key) == 32
    assert load_key(path) == key
    assert load_key(tmp_path / "k2", create=True) != key              # random, not a fixed value
    if os.name == "posix":
        assert (path.stat().st_mode & 0o777) == 0o600
    path.write_text("not hex")
    assert load_key(path) is None                                     # a broken file is no key


def test_signatur_haengt_an_jedem_feld():
    base = {"op": "cmd", "session": "s", "seq": 5, "name": "torque", "args": {"joint": "a", "on": True}}
    sig = sign(KEY, base)
    for change in ({"seq": 6}, {"name": "reboot"}, {"args": {"joint": "a", "on": False}}, {"session": "t"}):
        assert sign(KEY, {**base, **change}) != sig


# ------------------------------------------------------------------------------- S4, S7, S9 in telemetry.py
def _telemetry():
    """telemetry.py needs the robot's constants and moves; on a PC without them, small stand-ins."""
    try:
        import telemetry
        return telemetry
    except ImportError:
        constants = types.ModuleType("constants")
        constants.MOTOR_TO_ID = {"a": 1, "b": 2}
        moves = types.ModuleType("moves")
        moves.__path__ = []
        move = types.ModuleType("moves.move")
        move.ALL, move.CLASSIC = ["classic", "climber"], "classic"
        sys.modules.update({"constants": constants, "moves": moves, "moves.move": move})
        import telemetry
        return telemetry


class FakeLink:
    listening = True

    def __init__(self):
        self.acks, self.queue = [], []

    def commands(self):
        out, self.queue = self.queue, []
        return out

    def ack(self, cmd, ok=True, text=""):
        self.acks.append((cmd["name"], ok, text))

    def publish(self, **_):
        pass

    def event(self, *_):
        pass


class FakeController:
    def __init__(self):
        self.reboots, self.torques = [], []

    def reboot(self, mid):
        self.reboots.append(mid)
        return 0.1

    def write_torque_enable(self, mid, on):
        self.torques.append((mid, on))


@pytest.fixture
def tel():
    t_mod = _telemetry()
    t = t_mod.Telemetry(FakeController())
    t.health = None
    t.link = FakeLink()
    t.names = list(t_mod.MOTOR_TO_ID)[:2]
    t.ids = [t_mod.MOTOR_TO_ID[n] for n in t.names]
    t.torque = [math.nan] * len(t.names)
    t.error = [math.nan] * len(t.names)
    return t


def _state():
    return types.SimpleNamespace(motor_positions={}, motor_velocities={}, measured_currents={}, body_quat=None,
                                 gyro=None, acc=None)


def test_s4_kaputter_befehl_stoppt_telemetry_nicht(tel):
    """S4 (Roboterseite): Befehl mit unerwarteten Werten wirft -> abgelehnt, tick() läuft weiter."""
    tel.moves = {"walk": types.SimpleNamespace(options={}, sliders={}, slider={}, state=types.SimpleNamespace(name="INACTIVE"))}
    bad = [{"name": "move_start", "args": {"move": ["walk"]}, "seq": 1, "addr": None},     # unhashable: TypeError
           {"name": "slider", "args": {"move": {"x": 1}}, "seq": 2, "addr": None}]
    tel.link.queue = bad
    tel.tick(_state(), {}, 20.0)                                      # must not raise
    assert ("move_start", False) in [(n, ok) for n, ok, _ in tel.link.acks]


def test_s7_reboot_flut_wird_begrenzt(tel):
    """S7: Flut von reboot/torque -> höchstens 1 reboot je 2 s, Rest abgelehnt; em nie begrenzt."""
    joint = tel.names[0]
    for _ in range(5):
        tel._run({"name": "reboot", "args": {"joint": joint}, "seq": 1, "addr": None})
    assert len(tel.controller.reboots) == 1
    assert sum(1 for n, ok, _ in tel.link.acks if n == "reboot" and not ok) == 4
    for _ in range(5):
        tel._run({"name": "em", "args": {}, "seq": 1, "addr": None})
    assert [r for r in tel.requests if r[0] == "em"] == [("em", None)] * 5


def test_s9_slider_wird_begrenzt(tel):
    """S9: Slider-Wert NaN/Inf/1e30, unbekannter Slider -> begrenzt bzw. ignoriert."""
    m = types.SimpleNamespace(sliders={"speed": [0.0, 1.0, 0.5]}, slider={"speed": 0.5})
    tel.moves = {"walk": m}
    for value, expected in ((float("nan"), 0.5), (float("inf"), 0.5), (1e30, 1.0), (-1e30, 0.0), ("1", 0.0)):
        tel._run({"name": "slider", "args": {"move": "walk", "slider": "speed", "value": value}})
        assert m.slider["speed"] == expected
    tel._run({"name": "slider", "args": {"move": "walk", "slider": "unbekannt", "value": 0.7}})
    assert "unbekannt" not in m.slider
