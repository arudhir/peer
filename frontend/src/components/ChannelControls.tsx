/**
 * Channel Controls Component
 * Controls for channel visibility and opacity
 */

import React from 'react';
import type { ChannelInfo, ChannelState } from '../types';

interface ChannelControlsProps {
  channels: ChannelInfo[];
  channelStates: Record<string, ChannelState>;
  onChannelStateChange: (channel: string, state: ChannelState) => void;
}

const CHANNEL_COLORS: Record<string, string> = {
  nuclei: 'rgb(0, 0, 255)', // Blue
  actin: 'rgb(0, 255, 0)', // Green
  mito_mp: 'rgb(255, 0, 255)', // Magenta
  mito_tot: 'rgb(255, 255, 0)', // Yellow
};

export const ChannelControls: React.FC<ChannelControlsProps> = ({
  channels,
  channelStates,
  onChannelStateChange,
}) => {
  return (
    <div className="p-4 bg-gray-800 rounded-lg">
      <h3 className="text-lg font-bold mb-3">Channels</h3>

      <div className="space-y-3">
        {channels.map((channel) => {
          const state = channelStates[channel.name] || {
            visible: true,
            opacity: 1.0,
          };

          const color = CHANNEL_COLORS[channel.name] || 'rgb(255, 255, 255)';

          return (
            <div
              key={channel.name}
              className="border border-gray-700 rounded p-3"
            >
              {/* Header with visibility toggle */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: color }}
                  />
                  <label className="font-mono text-sm font-semibold">
                    {channel.name}
                  </label>
                </div>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={state.visible}
                    onChange={(e) =>
                      onChannelStateChange(channel.name, {
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
                    onChannelStateChange(channel.name, {
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
