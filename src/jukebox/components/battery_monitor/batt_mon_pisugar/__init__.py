# RPi-Jukebox-RFID Version 3 - Eigen uitbreiding muziekbox
# Copyright (c) See file LICENSE in project root folder
"""
Battery monitor for the PiSugar 3 (Plus) battery/UPS board

The PiSugar measures the battery itself. This module reads the status from the
``pisugar-server`` daemon (TCP, default ``127.0.0.1:8423``) and publishes it as ``batt_status``,
so the Web App shows the battery level (Settings → Status).

Configuration in ``jukebox.yaml``::

    modules:
      named:
        battmon: battery_monitor.batt_mon_pisugar
    battmon:
      warning_level: 10       # % - call warning_action once when below (and not charging)
      shutdown_level: 3       # % - shut down cleanly when below (and not charging)
      full_level: 98          # % - counts as full on the status LED (the LED blinks while charging)
      warning_action:        # optional RPC command, e.g. {alias: set_volume, args: 20}
      all_clear_action:

Setup: install pisugar-server (https://github.com/PiSugar/pisugar-power-manager-rs) and enable I2C.
"""
import logging
import socket

import jukebox.cfghandler
import jukebox.plugs as plugs
import jukebox.publishing
import jukebox.multitimer as multitimer
import jukebox.utils as utils

logger = logging.getLogger('jb.battmon')
cfg = jukebox.cfghandler.get_handler('jukebox')


class BattmonPiSugar:
    """Battery monitor reading from pisugar-server"""

    def __init__(self):
        self.host = cfg.setndefault('battmon', 'pisugar_host', value='127.0.0.1')
        self.port = cfg.setndefault('battmon', 'pisugar_port', value=8423)
        self.interval = cfg.setndefault('battmon', 'interval_sec', value=10)
        self.warning_level = cfg.setndefault('battmon', 'warning_level', value=10)
        self.shutdown_level = cfg.setndefault('battmon', 'shutdown_level', value=3)
        self.full_level = cfg.setndefault('battmon', 'full_level', value=98)
        self.warning_action = cfg.setndefault('battmon', 'warning_action', value=None)
        self.all_clear_action = cfg.setndefault('battmon', 'all_clear_action', value=None)
        self.batt_status = {'soc': 0, 'charging': 0, 'voltage': 0}
        self.charge_state = None
        self._warned = False
        self._reachable = True

        self.status_thread = multitimer.GenericEndlessTimerClass('batt_mon.timer_status',
                                                                 self.interval, self.publish_status)
        self.status_thread.start()

    @staticmethod
    def _query(sock: socket.socket, reader, key: str) -> str:
        """Ask one value. pisugar-server may also push button events (e.g. 'single'), skip those"""
        sock.sendall(f"get {key}\n".encode())
        for _ in range(10):
            line = reader.readline()
            if not line:
                break
            name, sep, value = line.strip().partition(':')
            if sep and name.strip() == key:
                return value.strip()
        raise ValueError(f"No answer from pisugar-server for '{key}'")

    def read(self) -> dict:
        """Read the battery status from pisugar-server"""
        # Close the file object too: an open makefile() keeps the connection alive
        with socket.create_connection((self.host, self.port), timeout=3) as sock, sock.makefile('r') as reader:
            soc = float(self._query(sock, reader, 'battery'))
            voltage = float(self._query(sock, reader, 'battery_v'))
            plugged = self._query(sock, reader, 'battery_power_plugged').lower() == 'true'
        return {'soc': max(0, min(100, int(round(soc)))),
                'charging': 1 if plugged else 0,
                'voltage': int(voltage * 1000)}

    @plugs.tag
    def get_batt_status(self):
        return self.batt_status

    def update_charge_state(self, status: dict):
        """Report changes to the status LED. Margin on 'full': the level dips a little before the charger tops up"""
        if not status['charging']:
            state = 'discharging'
        elif status['soc'] >= self.full_level or (self.charge_state == 'full' and status['soc'] >= self.full_level - 5):
            state = 'full'
        else:
            state = 'charging'
        if state != self.charge_state:
            logger.info(f"Battery {state}: {status['soc']}%")
            self.charge_state = state
            plugs.call_ignore_errors('gpio', 'set_charge_state', args=[state])

    def publish_status(self):
        try:
            status = self.read()
        except (OSError, ValueError) as e:
            if self._reachable:
                logger.warning(f"Cannot read battery from pisugar-server at {self.host}:{self.port}: {e}")
                self._reachable = False
            return
        if not self._reachable:
            logger.info("pisugar-server reachable again")
            self._reachable = True

        soc, on_battery = status['soc'], not status['charging']
        if on_battery and soc <= self.shutdown_level:
            logger.warning(f"Shutdown due to low battery: {soc}%")
            plugs.call_ignore_errors('host', 'shutdown')
        elif on_battery and soc <= self.warning_level:
            if not self._warned:
                logger.warning(f"Battery low: {soc}%")
                self._warned = True
                if self.warning_action is not None:
                    utils.decode_and_call_rpc_command(self.warning_action, logger)
        elif self._warned and (not on_battery or soc > self.warning_level + 5):
            self._warned = False
            if self.all_clear_action is not None:
                utils.decode_and_call_rpc_command(self.all_clear_action, logger)

        logger.debug(f"SOC: {soc}%, Batt Voltage: {status['voltage']}mV, charging: {status['charging']}")
        self.batt_status.update(status)
        self.update_charge_state(status)
        jukebox.publishing.get_publisher().send('batt_status', self.batt_status)


batt_mon = None


@plugs.finalize
def finalize():
    global batt_mon
    batt_mon = BattmonPiSugar()
    plugs.register(batt_mon, name='batt_mon')


@plugs.atexit
def atexit(**ignored_kwargs):
    global batt_mon
    batt_mon.status_thread.cancel()
    return batt_mon.status_thread.timer_thread
