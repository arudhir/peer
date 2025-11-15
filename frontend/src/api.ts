/**
 * API client for PICA backend
 */

import axios from 'axios';
import type {
  ExperimentInfo,
  SequenceInfo,
  PlateMetadata,
  ImageInfo,
  ChannelInfo,
  MaskInfo,
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
});

// TODO: Add authentication interceptor when auth is enabled
// api.interceptors.request.use((config) => {
//   const token = getAuthToken();
//   if (token) {
//     config.headers.Authorization = `Bearer ${token}`;
//   }
//   return config;
// });

export const experimentApi = {
  listExperiments: async (): Promise<ExperimentInfo[]> => {
    const response = await api.get('/api/experiments');
    return response.data;
  },

  listSequences: async (experimentId: string): Promise<SequenceInfo[]> => {
    const response = await api.get(`/api/experiments/${experimentId}/sequences`);
    return response.data;
  },
};

export const metadataApi = {
  getPlateMetadata: async (
    experiment: string,
    sequence: string
  ): Promise<PlateMetadata> => {
    const response = await api.get(
      `/api/experiments/${experiment}/sequences/${sequence}/plate-metadata`
    );
    return response.data;
  },

  getImageInfo: async (
    experiment: string,
    sequence: string,
    well: string
  ): Promise<ImageInfo> => {
    const response = await api.get(
      `/api/experiments/${experiment}/sequences/${sequence}/wells/${well}/info`
    );
    return response.data;
  },

  getChannels: async (
    experiment: string,
    sequence: string,
    well: string
  ): Promise<ChannelInfo[]> => {
    const response = await api.get(
      `/api/experiments/${experiment}/sequences/${sequence}/wells/${well}/channels`
    );
    return response.data;
  },

  getMasks: async (
    experiment: string,
    sequence: string,
    well: string
  ): Promise<MaskInfo[]> => {
    const response = await api.get(
      `/api/experiments/${experiment}/sequences/${sequence}/wells/${well}/masks`
    );
    return response.data;
  },
};

export const tileApi = {
  getTileUrl: (
    experiment: string,
    sequence: string,
    well: string,
    channel: string,
    level: number,
    x: number,
    y: number,
    tileSize: number = 256
  ): string => {
    const params = new URLSearchParams({
      channel,
      level: level.toString(),
      x: x.toString(),
      y: y.toString(),
      tile_size: tileSize.toString(),
    });
    return `${API_BASE_URL}/api/experiments/${experiment}/sequences/${sequence}/wells/${well}/tile?${params}`;
  },

  getCompositeTileUrl: (
    experiment: string,
    sequence: string,
    well: string,
    level: number,
    x: number,
    y: number,
    options: {
      tileSize?: number;
      mode?: 'normalized' | 'raw';
      channelOpacities?: Record<string, number>;
      channelVisibility?: Record<string, boolean>;
    } = {}
  ): string => {
    const {
      tileSize = 256,
      mode = 'normalized',
      channelOpacities = {},
      channelVisibility = {},
    } = options;

    const params = new URLSearchParams({
      level: level.toString(),
      x: x.toString(),
      y: y.toString(),
      tile_size: tileSize.toString(),
      mode,
    });

    // Add channel controls
    Object.entries(channelOpacities).forEach(([channel, opacity]) => {
      params.append(`${channel}_opacity`, opacity.toString());
    });
    Object.entries(channelVisibility).forEach(([channel, visible]) => {
      params.append(`${channel}_visible`, visible.toString());
    });

    return `${API_BASE_URL}/api/experiments/${experiment}/sequences/${sequence}/wells/${well}/composite?${params}`;
  },

  getMaskTileUrl: (
    experiment: string,
    sequence: string,
    well: string,
    maskName: string,
    level: number,
    x: number,
    y: number,
    options: {
      tileSize?: number;
      opacity?: number;
      isLabel?: boolean;
    } = {}
  ): string => {
    const { tileSize = 256, opacity = 0.5, isLabel = false } = options;

    const params = new URLSearchParams({
      mask_name: maskName,
      level: level.toString(),
      x: x.toString(),
      y: y.toString(),
      tile_size: tileSize.toString(),
      opacity: opacity.toString(),
      is_label: isLabel.toString(),
    });

    return `${API_BASE_URL}/api/experiments/${experiment}/sequences/${sequence}/wells/${well}/mask-tile?${params}`;
  },
};

export default api;
