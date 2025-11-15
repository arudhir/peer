/**
 * Type definitions for PICA viewer
 */

export interface ExperimentInfo {
  experiment_id: string;
  name: string;
  description?: string;
  num_sequences: number;
}

export interface SequenceInfo {
  sequence_id: string;
  experiment_id: string;
  name: string;
  num_wells: number;
}

export interface WellMetadata {
  well_id: string;
  row: string;
  col: number;
  has_image: boolean;
  has_masks: boolean;
  has_processed: boolean;
  image_path?: string;
  preview_path?: string;
}

export interface PlateMetadata {
  experiment_id: string;
  sequence_id: string;
  wells: WellMetadata[];
  rows: number;
  cols: number;
}

export interface ChannelInfo {
  name: string;
  index: number;
  color?: [number, number, number];
  dtype: string;
  shape: [number, number];
}

export interface MaskInfo {
  name: string;
  path: string;
  is_label_mask: boolean;
  num_objects?: number;
}

export interface ImageInfo {
  experiment_id: string;
  sequence_id: string;
  well_id: string;
  shape: [number, number];
  num_levels: number;
  channels: ChannelInfo[];
  masks: MaskInfo[];
  format: 'tiff' | 'zarr';
}

export interface ChannelState {
  visible: boolean;
  opacity: number;
}

export interface MaskState {
  visible: boolean;
  opacity: number;
}

export type IntensityMode = 'normalized' | 'raw';

export interface ViewerState {
  zoom: number;
  pan: { x: number; y: number };
  level: number;
  channels: Record<string, ChannelState>;
  masks: Record<string, MaskState>;
  intensityMode: IntensityMode;
  showComposite: boolean;
}
