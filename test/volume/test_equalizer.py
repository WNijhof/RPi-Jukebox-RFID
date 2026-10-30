# RPi-Jukebox-RFID Version 3 - Eigen uitbreiding muziekbox
# Copyright (c) See file LICENSE in project root folder
import importlib.util
import os

import pytest

# Load the file directly: the volume package itself needs PulseAudio
_path = os.path.join(os.path.dirname(__file__), '../../src/jukebox/components/volume/equalizer.py')
_spec = importlib.util.spec_from_file_location('equalizer', _path)
equalizer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(equalizer)

ARGUMENT = 'sink_name=eq sink_master=hw plugin=caps label=Eq10X2 control=-18,-10,-2,-1,-4,-4,-4,-4,-1,-2'
GAINS = [1, 2, 3, 4, 5, 6, 7, 8, 9, -10.5]


def test_parse_control():
    assert equalizer.parse_control(ARGUMENT) == equalizer.DEFAULT_GAINS


@pytest.mark.parametrize('argument', ['', None, 'sink_name=eq', 'control=1,2,3', 'control=a,2,3,4,5,6,7,8,9,10',
                                      'my_control=1,2,3,4,5,6,7,8,9,10'])
def test_parse_control_without_valid_gains(argument):
    assert equalizer.parse_control(argument) is None


def test_replace_control_keeps_other_arguments():
    assert equalizer.replace_control(ARGUMENT, GAINS) == \
        'sink_name=eq sink_master=hw plugin=caps label=Eq10X2 control=1,2,3,4,5,6,7,8,9,-10.5'


def test_check_gains():
    assert equalizer.check_gains(GAINS) == [float(gain) for gain in GAINS]


@pytest.mark.parametrize('gains', [[0] * 9, [0] * 11, [equalizer.GAIN_MAX + 1] + [0] * 9,
                                   [equalizer.GAIN_MIN - 1] + [0] * 9])
def test_check_gains_rejects(gains):
    with pytest.raises(ValueError):
        equalizer.check_gains(gains)


@pytest.mark.parametrize('preset', equalizer.PRESETS)
def test_presets_are_usable_and_do_not_boost(preset):
    gains = equalizer.check_gains(equalizer.PRESETS[preset])
    assert max(gains) <= 0


def test_save_gains_changes_only_the_equalizer_line(tmp_path):
    cfg_file = tmp_path / 'default.pa'
    cfg_file.write_text(f'# control=keep\nload-module module-always-sink\nload-module module-ladspa-sink {ARGUMENT}\n'
                        'set-default-sink eq\n')
    equalizer.save_gains(GAINS, str(cfg_file))
    assert cfg_file.read_text() == ('# control=keep\nload-module module-always-sink\n'
                                    'load-module module-ladspa-sink sink_name=eq sink_master=hw plugin=caps '
                                    'label=Eq10X2 control=1,2,3,4,5,6,7,8,9,-10.5\nset-default-sink eq\n')


def test_save_gains_without_equalizer(tmp_path):
    cfg_file = tmp_path / 'default.pa'
    cfg_file.write_text('load-module module-always-sink\n')
    with pytest.raises(ValueError):
        equalizer.save_gains(GAINS, str(cfg_file))
