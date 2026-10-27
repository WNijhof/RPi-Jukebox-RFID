// Eigen uitbreiding muziekbox: register a card to play Spotify content
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  FormControl,
  Grid,
  NativeSelect,
  TextField,
  Typography,
} from '@mui/material';

import request from '../../../../../utils/request';
import {
  getActionAndCommand,
  getArgsValues,
} from '../../../utils';

const COMMAND = 'play_spotify';

const SelectSpotify = ({
  actionData,
  handleActionDataChange,
}) => {
  const { t } = useTranslation();
  const { action } = getActionAndCommand(actionData);
  const [uri = '', name = ''] = getArgsValues(actionData);

  const [playlists, setPlaylists] = useState([]);
  const [playlistsError, setPlaylistsError] = useState(false);

  useEffect(() => {
    const loadPlaylists = async () => {
      const { result, error } = await request('spotifyPlaylists');

      if (result) setPlaylists(result);
      if (error) setPlaylistsError(true);
    };

    loadPlaylists();
  }, []);

  const update = (newUri, newName) => {
    handleActionDataChange(action, COMMAND, { uri: newUri, name: newName });
  };

  const onSelectPlaylist = (event) => {
    const playlist = playlists.find(p => p.uri === event.target.value);
    if (playlist) update(playlist.uri, playlist.name);
  };

  const selectedPlaylist = playlists.find(p => p.uri === uri);

  return (
    <Grid container direction="column" sx={{ gap: '20px' }}>
      <Grid item>
        <Typography>{t('cards.controls.actions.spotify.playlist-label')}</Typography>
        {playlistsError
          ? <Typography color="error">
              {t('cards.controls.actions.spotify.playlists-unavailable')}
            </Typography>
          : <FormControl fullWidth>
              <NativeSelect
                value={selectedPlaylist ? uri : '0'}
                onChange={onSelectPlaylist}
                name="spotify-playlists"
              >
                <option key={0} value={'0'} disabled={true}>
                  {t('cards.controls.actions.spotify.playlist-placeholder')}
                </option>
                {playlists.map((playlist) =>
                  <option key={playlist.uri} value={playlist.uri}>
                    {playlist.name}
                    {playlist.collaborative
                      ? ` (${t('cards.controls.actions.spotify.collaborative')})`
                      : ''}
                  </option>
                )}
              </NativeSelect>
            </FormControl>
        }
      </Grid>
      <Grid item>
        <TextField
          fullWidth
          label={t('cards.controls.actions.spotify.link-label')}
          helperText={t('cards.controls.actions.spotify.link-helper')}
          value={uri}
          onChange={(event) => update(event.target.value.trim(), name)}
        />
      </Grid>
      <Grid item>
        <TextField
          fullWidth
          label={t('cards.controls.actions.spotify.name-label')}
          value={name}
          onChange={(event) => update(uri, event.target.value)}
        />
      </Grid>
    </Grid>
  );
};

export default SelectSpotify;
