from bridge import keymap


def test_letter_roundtrip():
    hid = keymap.win_to_hid(0x41, False)          # VK 'A'
    assert hid == 0x04 and keymap.HID_TO_MAC[hid] == 0x00
    assert keymap.mac_to_hid(0x00) == 0x04 and keymap.HID_TO_WIN[0x04] == 0x41


def test_keypad_enter_extended():
    assert keymap.win_to_hid(0x0D, False) == 0x28
    assert keymap.win_to_hid(0x0D, True) == 0x58


def test_modifiers_and_swap():
    hid = keymap.mac_to_hid(0x37)                 # Cmd
    assert hid == keymap.L_GUI and keymap.HID_TO_WIN[hid] == 0x5B
    assert keymap.SWAP_CMD_CTRL[hid] == keymap.L_CTRL
    assert keymap.win_to_hid(0x11, False) == keymap.L_CTRL     # VK_CONTROL (비구분)


def test_hangul():
    assert keymap.win_to_hid(0x15, False) == keymap.LANG1
    assert keymap.HID_TO_MAC[keymap.LANG1] == 0x68


def test_every_hid_has_pynput_name_for_modifiers():
    for h in (keymap.L_CTRL, keymap.L_SHIFT, keymap.L_ALT, keymap.L_GUI,
              keymap.R_CTRL, keymap.R_SHIFT, keymap.R_ALT, keymap.R_GUI):
        assert h in keymap.HID_TO_PYNPUT
