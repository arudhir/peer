/**
 * Plate Browser Component
 * Displays A1-H12 grid for well selection
 */

import React from 'react';
import type { PlateMetadata, WellMetadata } from '../types';

interface PlateBrowserProps {
  plateMetadata: PlateMetadata;
  selectedWell?: string;
  onWellSelect: (well: string) => void;
}

export const PlateBrowser: React.FC<PlateBrowserProps> = ({
  plateMetadata,
  selectedWell,
  onWellSelect,
}) => {
  const { wells, rows, cols } = plateMetadata;

  // Create a map for quick lookup
  const wellMap = new Map<string, WellMetadata>();
  wells.forEach((well) => {
    wellMap.set(well.well_id, well);
  });

  // Generate row labels (A-H)
  const rowLabels = Array.from({ length: rows }, (_, i) =>
    String.fromCharCode(65 + i)
  );

  // Generate column labels (1-12)
  const colLabels = Array.from({ length: cols }, (_, i) => i + 1);

  const getWellClass = (well?: WellMetadata) => {
    if (!well || !well.has_image) {
      return 'bg-gray-700 text-gray-500 cursor-not-allowed';
    }

    if (well.well_id === selectedWell) {
      return 'bg-blue-600 text-white cursor-pointer hover:bg-blue-700';
    }

    return 'bg-gray-600 text-white cursor-pointer hover:bg-gray-500';
  };

  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-4">Plate Layout</h2>

      <div className="inline-block border border-gray-600 rounded-lg overflow-hidden">
        {/* Header row with column numbers */}
        <div className="flex">
          <div className="w-10 h-10" /> {/* Empty corner */}
          {colLabels.map((col) => (
            <div
              key={col}
              className="w-10 h-10 flex items-center justify-center font-mono text-sm bg-gray-800"
            >
              {col}
            </div>
          ))}
        </div>

        {/* Rows */}
        {rowLabels.map((row) => (
          <div key={row} className="flex">
            {/* Row label */}
            <div className="w-10 h-10 flex items-center justify-center font-mono text-sm bg-gray-800">
              {row}
            </div>

            {/* Wells */}
            {colLabels.map((col) => {
              const wellId = `${row}${col}`;
              const well = wellMap.get(wellId);

              return (
                <div
                  key={wellId}
                  className={`w-10 h-10 flex items-center justify-center text-xs border border-gray-700 ${getWellClass(
                    well
                  )}`}
                  onClick={() => {
                    if (well && well.has_image) {
                      onWellSelect(wellId);
                    }
                  }}
                  title={
                    well && well.has_image
                      ? `${wellId} - Click to view`
                      : `${wellId} - No data`
                  }
                >
                  {well && well.has_image && (
                    <span className="font-mono">{wellId}</span>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {selectedWell && (
        <div className="mt-4 text-sm">
          <p>
            Selected: <span className="font-bold">{selectedWell}</span>
          </p>
        </div>
      )}
    </div>
  );
};
