/**
 * Viewer Controls Component
 * Controls for composite mode and intensity normalization
 */

import React from 'react';
import type { IntensityMode } from '../types';

interface ViewerControlsProps {
  showComposite: boolean;
  intensityMode: IntensityMode;
  onCompositeChange: (show: boolean) => void;
  onIntensityModeChange: (mode: IntensityMode) => void;
}

export const ViewerControls: React.FC<ViewerControlsProps> = ({
  showComposite,
  intensityMode,
  onCompositeChange,
  onIntensityModeChange,
}) => {
  return (
    <div className="p-4 bg-gray-800 rounded-lg">
      <h3 className="text-lg font-bold mb-3">Display Settings</h3>

      <div className="space-y-3">
        {/* Composite toggle */}
        <div className="flex items-center justify-between">
          <label className="text-sm font-semibold">Composite View</label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={showComposite}
              onChange={(e) => onCompositeChange(e.target.checked)}
              className="w-4 h-4"
            />
            <span className="text-xs">
              {showComposite ? 'On' : 'Off'}
            </span>
          </label>
        </div>

        {/* Intensity mode */}
        <div>
          <label className="text-sm font-semibold block mb-2">
            Intensity Mode
          </label>
          <div className="flex gap-2">
            <button
              onClick={() => onIntensityModeChange('normalized')}
              className={`flex-1 px-3 py-2 rounded text-sm ${
                intensityMode === 'normalized'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Normalized
            </button>
            <button
              onClick={() => onIntensityModeChange('raw')}
              className={`flex-1 px-3 py-2 rounded text-sm ${
                intensityMode === 'raw'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              Raw
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            {intensityMode === 'normalized'
              ? 'Percentile-based scaling (1-99%)'
              : 'Original intensity values'}
          </p>
        </div>
      </div>
    </div>
  );
};
