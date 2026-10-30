import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  Card,
  CardContent,
  CardHeader,
  Divider,
  Grid,
  Switch,
  Typography,
} from '@mui/material';

import request from '../../utils/request';

// Eigen uitbreiding muziekbox: knoppen aan/uit
const SettingsButtons = () => {
  const { t } = useTranslation();

  const [inputs, setInputs] = useState([]);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const fetchInputs = async () => {
      const { result, error } = await request('getInputs');
      if (error) return setFailed(true);
      setInputs(result);
    };

    fetchInputs();
  }, []);

  const handleSwitch = (name) => async (event) => {
    const enabled = event.target.checked;
    const previous = inputs;

    setInputs(inputs.map((input) => input.name === name ? { ...input, enabled } : input));
    const { result, error } = await request('setInputEnabled', { name, enabled });
    if (error) return setInputs(previous);
    setInputs(result);
  };

  return (
    <Card>
      <CardHeader
        title={t('settings.buttons.title')}
        subheader={t('settings.buttons.description')}
      />
      <Divider />
      <CardContent>
        <Grid container direction="column">
          {failed && <Typography>{t('settings.buttons.load-failed')}</Typography>}
          {!failed && inputs.length === 0 && <Typography>{t('settings.buttons.none')}</Typography>}
          {inputs.map(({ name, enabled }) => (
            <Grid container direction="row" justifyContent="space-between" alignItems="center" key={name}>
              <Typography>
                {t(`settings.buttons.names.${name}`, name)}
              </Typography>
              <Switch
                checked={enabled}
                onChange={handleSwitch(name)}
              />
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
};

export default SettingsButtons;
