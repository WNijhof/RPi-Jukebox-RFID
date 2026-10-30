# RPi-Jukebox-RFID Version 3 - Eigen uitbreiding muziekbox
# Copyright (c) See file LICENSE in project root folder
"""
Keeps track of how long the box runs on one battery charge and how much of that time music played.

A cycle starts when the box runs on battery and ends at the next charge. Only time with the box on and
on battery counts, so time switched off is not included. The current cycle is saved regularly, because
the box may lose power without a clean shutdown.
"""
import json
import logging
import os
import time

logger = logging.getLogger('jb.battmon')

#: Number of finished cycles to keep
MAX_CYCLES = 50
#: Shorter cycles are left out of the history (e.g. a charger that was unplugged for a moment)
MIN_CYCLE_SECONDS = 60
#: The level rose by more than this since the last update: the box was charged while switched off
RECHARGED_MARGIN = 5
#: Save the current cycle every this many updates
SAVE_EVERY_UPDATES = 6


class BatteryCycles:
    def __init__(self, filename: str):
        self.filename = filename
        self.current = None
        self.history = []
        self._updates = 0
        self._load()

    def _load(self):
        try:
            with open(self.filename) as f:
                data = json.load(f)
            self.current = data.get('current')
            self.history = data.get('history', [])
        except FileNotFoundError:
            pass
        except (OSError, ValueError, AttributeError) as e:
            logger.warning(f"Cannot read battery cycles from {self.filename}: {e}")

    def _save(self):
        tmp_file = f"{self.filename}.tmp"
        try:
            with open(tmp_file, 'w') as f:
                json.dump({'current': self.current, 'history': self.history}, f)
            os.replace(tmp_file, self.filename)
        except OSError as e:
            logger.warning(f"Cannot save battery cycles to {self.filename}: {e}")

    def _finish(self):
        if self.current is None:
            return
        if self.current['on_seconds'] >= MIN_CYCLE_SECONDS:
            self.history.insert(0, self.current)
            del self.history[MAX_CYCLES:]
        self.current = None
        self._save()

    def update(self, soc: int, on_battery: bool, playing: bool, seconds: int):
        """Add :attr:`seconds` of running time to the current cycle

        :param soc: Battery level in %

        :param on_battery: :data:`False` while the charger is connected, which ends the cycle

        :param playing: :data:`True` if music is playing

        :param seconds: Time since the last update
        """
        if not on_battery:
            self._finish()
            return
        if self.current is not None and soc > self.current['end_soc'] + RECHARGED_MARGIN:
            self._finish()
        now = int(time.time())
        if self.current is None:
            self.current = {'started': now, 'ended': now, 'start_soc': soc, 'end_soc': soc,
                            'on_seconds': 0, 'played_seconds': 0}
        self.current['ended'] = now
        self.current['end_soc'] = soc
        self.current['on_seconds'] += seconds
        if playing:
            self.current['played_seconds'] += seconds
        self._updates += 1
        if self._updates % SAVE_EVERY_UPDATES == 0:
            self._save()

    def get(self) -> dict:
        """Return the current cycle and the finished cycles, newest first"""
        return {'current': self.current, 'history': self.history}
