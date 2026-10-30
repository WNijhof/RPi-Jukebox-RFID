# RPi-Jukebox-RFID Version 3 - Eigen uitbreiding muziekbox
# Copyright (c) See file LICENSE in project root folder
import os
import sys
import types
from collections import deque
from unittest import mock

import pytest

# In case this is run locally from
sys.path.append(os.path.abspath('../../src/jukebox'))

_publisher = mock.MagicMock()
sys.modules.setdefault('jukebox.publishing', types.SimpleNamespace(get_publisher=lambda: _publisher))

import jukebox  # noqa: E402
import jukebox.plugs  # noqa: E402
jukebox.plugs.ALLOW_DIRECT_IMPORTS = True
# The stub is not imported as a real submodule, so attach it to the package explicitly
jukebox.publishing = sys.modules['jukebox.publishing']
import jukebox.multitimer  # noqa: E402
import components.battery_monitor.batt_mon_pisugar as pisugar  # noqa: E402

ANSWERS = {'battery': '8.6', 'battery_v': '3.52', 'battery_power_plugged': 'false'}


class FakePiSugarSocket:
    """Behaves like a connection to pisugar-server, which also pushes button events between answers"""

    def __init__(self, *args, **kwargs):
        self.lines = deque()

    def sendall(self, data):
        key = data.decode().strip().replace('get ', '')
        self.lines.extend(['single\n', f"{key}: {ANSWERS[key]}\n"])

    def makefile(self, mode):
        return self

    def readline(self):
        return self.lines.popleft() if self.lines else ''

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def battmon():
    with mock.patch.object(jukebox.multitimer, 'GenericEndlessTimerClass'):
        mon = pisugar.BattmonPiSugar()
    with mock.patch.object(pisugar.socket, 'create_connection', FakePiSugarSocket):
        yield mon


def test_reads_status(battmon):
    assert battmon.read() == {'soc': 9, 'charging': 0, 'voltage': 3520}


def test_warns_once_when_low(battmon):
    with mock.patch.object(pisugar.utils, 'decode_and_call_rpc_command') as call:
        battmon.warning_action = {'alias': 'set_volume', 'args': 20}
        battmon.publish_status()
        battmon.publish_status()
    assert call.call_count == 1
    assert battmon.batt_status['soc'] == 9
    jukebox.publishing.get_publisher().send.assert_called_with('batt_status', battmon.batt_status)


def test_shuts_down_when_empty(battmon):
    with mock.patch.dict(ANSWERS, {'battery': '2.0'}), \
         mock.patch.object(pisugar.plugs, 'call_ignore_errors') as call:
        battmon.publish_status()
    call.assert_any_call('host', 'shutdown')


def test_no_shutdown_while_charging(battmon):
    with mock.patch.dict(ANSWERS, {'battery': '2.0', 'battery_power_plugged': 'true'}), \
         mock.patch.object(pisugar.plugs, 'call_ignore_errors') as call:
        battmon.publish_status()
    assert mock.call('host', 'shutdown') not in call.call_args_list
    assert battmon.batt_status['charging'] == 1


@pytest.mark.parametrize('soc, expected', [(50, 'charging'), (97, 'charging'), (98, 'full'), (100, 'full')])
def test_charge_state(battmon, soc, expected):
    with mock.patch.object(pisugar.plugs, 'call_ignore_errors') as call:
        battmon.update_charge_state({'soc': soc, 'charging': 1})
    call.assert_called_once_with('gpio', 'set_charge_state', args=[expected])


def test_charge_state_reports_changes_only(battmon):
    with mock.patch.object(pisugar.plugs, 'call_ignore_errors') as call:
        for soc in (50, 51, 98, 99):
            battmon.update_charge_state({'soc': soc, 'charging': 1})
        battmon.update_charge_state({'soc': 99, 'charging': 0})
    assert [c.kwargs['args'][0] for c in call.call_args_list] == ['charging', 'full', 'discharging']


def test_full_survives_small_dip(battmon):
    with mock.patch.object(pisugar.plugs, 'call_ignore_errors'):
        battmon.update_charge_state({'soc': 100, 'charging': 1})
        battmon.update_charge_state({'soc': 94, 'charging': 1})
        assert battmon.charge_state == 'full'
        battmon.update_charge_state({'soc': 92, 'charging': 1})
        assert battmon.charge_state == 'charging'


def test_unreachable_server_is_quiet(battmon):
    with mock.patch.object(pisugar.socket, 'create_connection', side_effect=ConnectionRefusedError()):
        battmon.publish_status()  # must not raise
    assert battmon._reachable is False
