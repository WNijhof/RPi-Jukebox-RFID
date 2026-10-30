import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  ListItem,
  ListItemText,
  ListItemAvatar,
  Avatar,
} from '@mui/material';

import NewReleasesIcon from '@mui/icons-material/NewReleases';

import request from '../../../utils/request';

// Eigen uitbreiding muziekbox: geinstalleerde release
const StatusRelease = () => {
  const { t } = useTranslation();

  const [release, setRelease] = useState(undefined);

  useEffect(() => {
    const fetchRelease = async () => {
      const { result } = await request('getRelease');
      if (result) setRelease(result);
    };

    fetchRelease();
  }, []);

  return (
    <ListItem disableGutters>
      <ListItemAvatar>
        <Avatar>
          <NewReleasesIcon />
        </Avatar>
      </ListItemAvatar>
      <ListItemText
        primary={release || `${t('general.loading')} ...`}
        secondary={t('settings.status.release.label')}
      />
    </ListItem>
  );
};

export default StatusRelease;
