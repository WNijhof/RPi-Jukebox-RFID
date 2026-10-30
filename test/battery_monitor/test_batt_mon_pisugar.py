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
from components.battery_monitor.batt_mon_pisugar.cycles import BatteryCycles  # noqa: E402

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
def battmon(tmp_path):
    with mock.patch.object(jukebox.multitimer, 'GenericEndlessTimerClass'):
        mon = pisugar.BattmonPiSugar()
    mon.cycles = BatteryCycles(str(tmp_path / 'cycles.json'))
    with mock.patch.object(pisugar.socket, 'create_connection', FakePiSugarSocket):
        yield mon


def test_low_sound_plays_once(battmon):
    with mock.patch.object(pisugar.plugs, 'call_ignore_errors') as call:
        for soc in (8, 7, 7, 6):
            battmon.play_low_sound({'soc': soc, 'charging': 0})
    assert call.call_count == 1
    assert call.call_args.args[:2] == ('jingle', 'play')


def test_no_low_sound_while_charging(battmon):
    with mock.patch.object(pisugar.plugs, 'call_ignore_errors') as call:
        battmon.play_low_sound({'soc': 6, 'charging': 1})
    call.assert_not_called()


def test_low_sound_again_after_charging(battmon):
    with mock.patch.object(pisugar.plugs, 'call_ignore_errors') as call:
        battmon.play_low_sound({'soc': 6, 'charging': 0})
        battmon.play_low_sound({'soc': 6, 'charging': 1})
        battmon.play_low_sound({'soc': 6, 'charging': 0})
    assert call.call_count == 2


def test_led_low_with_margin(battmon):
    with mock.patch.object(pisugar.plugs, 'call_ignore_errors'):
        battmon.update_charge_state({'soc': 11, 'charging': 0})
        assert battmon.charge_state == 'discharging'
        battmon.update_charge_state({'soc': 10, 'charging': 0})
        assert battmon.charge_state == 'low'
        battmon.update_charge_state({'soc': 14, 'charging': 0})
        assert battmon.charge_state == 'low'
        battmon.update_charge_state({'soc': 16, 'charging': 0})
        assert battmon.charge_state == 'discharging'


def test_cycle_counts_battery_and_music_time(battmon):
    with mock.patch.object(pisugar.plugs, 'call_ignore_errors', return_value={'state': 'play'}):
        for soc in (80, 79):
            battmon.update_cycles({'soc': soc, 'charging': 0})
    with mock.patch.object(pisugar.plugs, 'call_ignore_errors', return_value={'state': 'stop'}):
        battmon.update_cycles({'soc': 78, 'charging': 0})
    current = battmon.get_cycles()['current']
    assert (current['start_soc'], current['end_soc']) == (80, 78)
    assert current['on_seconds'] == 3 * battmon.interval
    assert current['played_seconds'] == 2 * battmon.interval


def test_charger_finishes_cycle_and_it_survives_restart(tmp_path):
    filename = str(tmp_path / 'cycles.json')
    cycles = BatteryCycles(filename)
    cycles.update(90, True, True, 3600)
    cycles.update(40, True, False, 3600)
    cycles.update(40, False, False, 10)

    restored = BatteryCycles(filename).get()
    assert restored['current'] is None
    assert len(restored['history']) == 1
    assert restored['history'][0]['on_seconds'] == 7200
    assert restored['history'][0]['played_seconds'] == 3600


def test_current_cycle_survives_power_loss(tmp_path):
    filename = str(tmp_path / 'cycles.json')
    cycles = BatteryCycles(filename)
    for _ in range(6):
        cycles.update(50, True, False, 10)
    assert BatteryCycles(filename).get()['current']['on_seconds'] == 60


def test_charged_while_switched_off_starts_new_cycle(tmp_path):
    cycles = BatteryCycles(str(tmp_path / 'cycles.json'))
    cycles.update(20, True, False, 120)
    cycles.update(100, True, False, 10)
    assert len(cycles.get()['history']) == 1
    assert cycles.get()['current']['start_soc'] == 100


def test_short_cycle_is_left_out(tmp_path):
    cycles = BatteryCycles(str(tmp_path / 'cycles.json'))
    cycles.update(60, True, False, 10)
    cycles.update(60, False, False, 10)
    assert cycles.get()['history'] == []


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
