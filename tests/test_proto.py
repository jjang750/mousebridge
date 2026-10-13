import socket

from bridge import proto


def _roundtrip(frame):
    a, b = socket.socketpair()
    try:
        a.sendall(frame)
        return proto.read_frame(b)
    finally:
        a.close(); b.close()


def test_hello():
    assert _roundtrip(proto.hello(1920, 1080, "mac")) == (proto.HELLO, {"w": 1920, "h": 1080, "name": "mac"})


def test_enter_move_button_wheel_key():
    t, d = _roundtrip(proto.enter(proto.EDGE_LEFT, 0.5))
    assert t == proto.ENTER and d["edge"] == proto.EDGE_LEFT and abs(d["ratio"] - 0.5) < 1e-6
    assert _roundtrip(proto.move(-3, 7)) == (proto.MOVE, {"dx": -3, "dy": 7})
    assert _roundtrip(proto.move(99999, -99999)) == (proto.MOVE, {"dx": 32767, "dy": -32768})
    assert _roundtrip(proto.button("left", True)) == (proto.BUTTON, {"btn": "left", "pressed": True})
    assert _roundtrip(proto.wheel(0, -1)) == (proto.WHEEL, {"dx": 0, "dy": -1})
    assert _roundtrip(proto.key(0x28, True)) == (proto.KEY, {"hid": 0x28, "pressed": True})
    assert _roundtrip(proto.leave()) == (proto.LEAVE, {})
    assert _roundtrip(proto.ping(123)) == (proto.PING, {"ts": 123})


def test_peer_closed():
    a, b = socket.socketpair()
    a.close()
    try:
        proto.read_frame(b)
        assert False
    except ConnectionError:
        pass
