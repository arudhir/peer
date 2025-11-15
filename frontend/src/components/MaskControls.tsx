/**
 * Mask Controls Component
 * Controls for mask visibility and opacity
 */

import React from 'react';
import type { MaskInfo, MaskState } from '../types';

interface MaskControlsProps {
  masks: MaskInfo[];
  maskStates: Record<string, MaskState>;
  onMaskStateChange: (mask: string, state: MaskState) => void;
}

export const MaskControls: React.FC<MaskControlsProps> = ({
  masks,
  maskStates,
  onMaskStateChange,
}) => {
  return (
    <div className="p-4 bg-gray-800 rounded-lg">
      <h3 className="text-lg font-bold mb-3">Masks</h3>

      <div className="space-y-3">
        {masks.map((mask) => {
          const state = maskStates[mask.name] || {
            visible: false,
            opacity: 0.5,
          };

          return (
            <div
              key={mask.name}
              className="border border-gray-700 rounded p-3"
            >
              {/* Header with visibility toggle */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <label className="font-mono text-sm font-semibold">
                    {mask.name}
                  </label>
                  {mask.is_label_mask && (
                    <span className="text-xs bg-purple-600 px-2 py-0.5 rounded">
                      Label
                    </span>
                  )}
                </div>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={state.visible}
                    onChange={(e) =>
                      onMaskStateChange(mask.name, {
                        ...state,
                        visible: e.target.checked,
                      })
                    }
                    className="w-4 h-4"
                  />
                  <span className="text-xs">Visible</span>
                </label>
              </div>

              {/* Opacity slider */}
              <div className="flex items-center gap-2">
                <label className="text-xs text-gray-400 w-16">Opacity</label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={state.opacity}
                  onChange={(e) =>
                    onMaskStateChange(mask.name, {
                      ...state,
                      opacity: parseFloat(e.target.value),
                    })
                  }
                  disabled={!state.visible}
                  className="flex-1"
                />
                <span className="text-xs text-gray-400 w-8">
                  {Math.round(state.opacity * 100)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
