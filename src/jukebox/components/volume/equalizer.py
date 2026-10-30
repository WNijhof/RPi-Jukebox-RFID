# RPi-Jukebox-RFID Version 3 - Eigen uitbreiding muziekbox
# Copyright (c) See file LICENSE in project root folder
"""Equalizer settings of the module-ladspa-sink with the Eq10X2 plugin

The gains live in the control argument of the module. There is no second copy of them:
the running module is the current state and the PulseAudio configuration file makes it survive a restart.
"""
import os
import re
from typing import List, Optional

#: Center frequencies of the Eq10X2 bands in Hz
BANDS = [31, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
#: Tuned by ear for the 75 mm speaker of the box, see the build manual
DEFAULT_GAINS = [-18, -10, -2, -1, -4, -4, -4, -4, -1, -2]
#: Common curve shapes fitted to that speaker: no deep bass it cannot play and no band above 0 dB, which would clip
PRESETS = {
    'standard': DEFAULT_GAINS,
    'flat': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    'warm': [-18, -8, 0, 0, -3, -5, -6, -6, -4, -4],
    'bright': [-18, -12, -6, -4, -4, -3, -1, 0, 0, -1],
    'voice': [-24, -16, -8, -4, -1, 0, 0, -1, -4, -6],
    'v-shape': [-18, -8, 0, 0, -5, -7, -7, -4, 0, 0],
    'loud': [-24, -14, -3, 0, 0, 0, 0, 0, 0, -2],
}
GAIN_MIN = -24
GAIN_MAX = 12

PULSE_CFG_FILE = '~/.config/pulse/default.pa'

_CONTROL = re.compile(r'(?<![^\s])control=(\S*)')
_LADSPA_LINE = re.compile(r'^\s*load-module\s+module-ladspa-sink\s.*label=Eq10X2.*$', re.MULTILINE)


def parse_control(argument: str) -> Optional[List[float]]:
    """Return the gains from a module argument string, or None if it holds no valid gains"""
    match = _CONTROL.search(argument or '')
    if match is None:
        return None
    try:
        gains = [float(gain) for gain in match.group(1).split(',')]
    except ValueError:
        return None
    return gains if len(gains) == len(BANDS) else None


def format_control(gains: List[float]) -> str:
    """Return the value of the control argument for gains"""
    return ','.join(f'{gain:g}' for gain in gains)


def replace_control(argument: str, gains: List[float]) -> str:
    """Return the module argument string with the control argument set to gains"""
    return _CONTROL.sub(f'control={format_control(gains)}', argument)


def check_gains(gains: List[float]) -> List[float]:
    """Return gains as a list of floats, raise ValueError if they cannot be used"""
    if len(gains) != len(BANDS):
        raise ValueError(f'Need {len(BANDS)} gains, got {len(gains)}')
    gains = [float(gain) for gain in gains]
    if not all(GAIN_MIN <= gain <= GAIN_MAX for gain in gains):
        raise ValueError(f'Gains must be in range {GAIN_MIN}..{GAIN_MAX}: {gains}')
    return gains


def save_gains(gains: List[float], cfg_file: str = PULSE_CFG_FILE) -> None:
    """Write gains to the equalizer line of the PulseAudio configuration file"""
    cfg_file = os.path.expanduser(cfg_file)
    with open(cfg_file) as f:
        content = f.read()
    content, count = _LADSPA_LINE.subn(lambda line: replace_control(line.group(0), gains), content)
    if count == 0:
        raise ValueError(f'No equalizer found in {cfg_file}')
    tmp_file = f'{cfg_file}.tmp'
    with open(tmp_file, 'w') as f:
        f.write(content)
    os.replace(tmp_file, cfg_file)
