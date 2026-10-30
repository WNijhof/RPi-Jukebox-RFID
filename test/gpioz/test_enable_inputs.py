# RPi-Jukebox-RFID Version 3
# Copyright (c) See file LICENSE in project root folder
import sys
import os

from unittest.mock import patch

from gpiozero import Device
from gpiozero.pins.mock import MockFactory, MockPin

# In case this is run locally from
sys.path.append(os.path.abspath('../../src/jukebox'))
from components.gpio.gpioz.core.input_devices import Button, ShortLongPressButton  # noqa: E402

Device.pin_factory = MockFactory(pin_class=MockPin)


class Counter:
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1


def press(pin):
    pin.drive_low()
    pin.drive_high()


def bind(device, action_names):
    counter = Counter()
    with patch('jukebox.utils.bind_rpc_command', return_value=counter.increment):
        device.set_rpc_actions({name: {'alias': 'dummy'} for name in action_names})
    return counter


def test_disabled_button_runs_no_action():
    with Button(5, name='b', pin_factory=Device.pin_factory) as button:
        counter = bind(button, ['on_press'])
        pin = button.pin

        press(pin)
        assert counter.value == 1

        button.enabled = False
        press(pin)
        assert counter.value == 1

        button.enabled = True
        press(pin)
        assert counter.value == 2


def test_disabled_short_long_press_button_runs_no_action():
    with ShortLongPressButton(6, name='s', hold_time=10, pin_factory=Device.pin_factory) as button:
        counter = bind(button, ['on_short_press', 'on_long_press'])
        pin = button.pin

        button.enabled = False
        press(pin)
        assert counter.value == 0

        button.enabled = True
        press(pin)
        assert counter.value == 1
