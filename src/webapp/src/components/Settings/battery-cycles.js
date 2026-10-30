import React, { useContext, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  Card,
  CardContent,
  CardHeader,
  Divider,
  List,
  ListItem,
  ListItemText,
  Typography,
} from '@mui/material';

import PubSubContext from '../../context/pubsub/context';
import request from '../../utils/request';
import { pluginIsLoaded } from '../../utils/utils';

const formatDuration = (seconds) => {
  const minutes = Math.floor(seconds / 60);
  return `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(2, '0')}`;
};

// Eigen uitbreiding muziekbox: gebruik per acculading
const SettingsBatteryCycles = () => {
  const { t } = useTranslation();

  const { state: { 'core.plugins.loaded': plugins } } = useContext(PubSubContext);

  const [cycles, setCycles] = useState({ current: null, history: [] });

  useEffect(() => {
    const fetchCycles = async () => {
      const { result } = await request('getBatteryCycles');
      if (result) setCycles(result);
    };

    if (pluginIsLoaded(plugins, 'battmon')) fetchCycles();
  }, [plugins]);

  if (!pluginIsLoaded(plugins, 'battmon')) return null;

  const { current, history } = cycles;

  const renderCycle = (cycle, title) => (
    <ListItem disableGutters key={cycle.started}>
      <ListItemText
        primary={`${title}: ${cycle.start_soc}% → ${cycle.end_soc}%`}
        secondary={t('settings.battery-cycles.usage', {
          on: formatDuration(cycle.on_seconds),
          played: formatDuration(cycle.played_seconds),
        })}
      />
    </ListItem>
  );

  return (
    <Card>
      <CardHeader
        title={t('settings.battery-cycles.title')}
        subheader={t('settings.battery-cycles.description')}
      />
      <Divider />
      <CardContent>
        {!current && history.length === 0 && <Typography>{t('settings.battery-cycles.none')}</Typography>}
        <List>
          {current && renderCycle(current, t('settings.battery-cycles.current'))}
          {history.map((cycle) => renderCycle(cycle, new Date(cycle.ended * 1000).toLocaleDateString()))}
        </List>
      </CardContent>
    </Card>
  );
};

export default SettingsBatteryCycles;
