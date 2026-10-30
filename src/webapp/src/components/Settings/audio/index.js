import React from 'react';
import { useTranslation } from 'react-i18next';

import {
  Card,
  CardContent,
  CardHeader,
  Divider,
} from '@mui/material';

import Equalizer from './equalizer';
import MaxVolume from './max-volume';
import Outputs from './outputs';

const SettingsAudio = () => {
  const { t } = useTranslation();

  return (
    <Card>
      <CardHeader title={t('settings.audio.title')} />
      <Divider />
      <CardContent>
        <Outputs />
      </CardContent>
      <Divider />
      <CardContent>
        <MaxVolume />
      </CardContent>
      <Divider />
      <CardContent>
        <Equalizer />
      </CardContent>
    </Card>
  );
};

export default SettingsAudio;
