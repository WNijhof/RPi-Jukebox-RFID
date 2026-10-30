import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  Chip,
  Grid,
  Slider,
  Typography,
} from '@mui/material';

import { useTheme } from '@mui/material/styles';
import { equals } from 'ramda';

import request from '../../../utils/request';

const formatBand = (band) => band < 1000 ? `${band}` : `${band / 1000}k`;

// Eigen uitbreiding muziekbox: equalizer
const Equalizer = () => {
  const { t } = useTranslation();
  const theme = useTheme();

  const [equalizer, setEqualizer] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const fetchEqualizer = async () => {
      const { result, error } = await request('getEqualizer');
      if (error) return setFailed(true);
      setEqualizer(result);
    };

    fetchEqualizer();
  }, []);

  const applyGains = async (gains) => {
    const { result, error } = await request('setEqualizer', { gains });
    if (error) return setFailed(true);
    setFailed(false);
    setEqualizer(result);
  };

  const handleChange = (index) => (event, gain) => {
    const gains = [...equalizer.gains];
    gains[index] = gain;
    setEqualizer({ ...equalizer, gains });
  };

  if (failed && !equalizer) return <Typography>{t('settings.audio.equalizer.load-failed')}</Typography>;
  if (!equalizer) return null;
  if (!equalizer.gains) return <Typography>{t('settings.audio.equalizer.none')}</Typography>;

  const { bands, gains, presets, min, max } = equalizer;

  return (
    <Grid container direction="column">
      <Typography>{t('settings.audio.equalizer.title')}</Typography>
      <Typography variant="body2" color="textSecondary">
        {t('settings.audio.equalizer.description')}
      </Typography>
      {failed && <Typography color="error">{t('settings.audio.equalizer.save-failed')}</Typography>}
      <Grid container direction="row" sx={{ gap: theme.spacing(1), paddingTop: theme.spacing(2) }}>
        {Object.keys(presets).map((preset) => (
          <Chip
            key={preset}
            label={t(`settings.audio.equalizer.presets.${preset}`, preset)}
            color={equals(presets[preset], gains) ? 'primary' : 'default'}
            onClick={() => applyGains(presets[preset])}
          />
        ))}
      </Grid>
      <Grid
        container
        direction="row"
        justifyContent="space-between"
        wrap="nowrap"
        sx={{ paddingTop: theme.spacing(3), paddingBottom: theme.spacing(1) }}
      >
        {bands.map((band, index) => (
          <Grid
            container
            direction="column"
            alignItems="center"
            key={band}
            sx={{ width: 'auto', minWidth: 0 }}
          >
            <Slider
              aria-label={`${formatBand(band)} Hz`}
              orientation="vertical"
              value={gains[index]}
              onChange={handleChange(index)}
              onChangeCommitted={() => applyGains(gains)}
              max={max}
              min={min}
              step={1}
              track={false}
              valueLabelDisplay="auto"
              sx={{ height: 160 }}
            />
            <Typography variant="caption" sx={{ paddingTop: theme.spacing(1) }}>
              {formatBand(band)}
            </Typography>
          </Grid>
        ))}
      </Grid>
    </Grid>
  );
};

export default Equalizer;
