/**
 * WebGL-based Image Viewer
 * Handles tile loading, rendering, pan, and zoom
 */

import React, { useRef, useEffect, useState, useCallback } from 'react';
import type { ImageInfo, ChannelState, MaskState, IntensityMode } from '../types';
import { tileApi } from '../api';

interface ImageViewerProps {
  experiment: string;
  sequence: string;
  well: string;
  imageInfo: ImageInfo;
  channelStates: Record<string, ChannelState>;
  maskStates: Record<string, MaskState>;
  intensityMode: IntensityMode;
  showComposite: boolean;
}

const TILE_SIZE = 256;

export const ImageViewer: React.FC<ImageViewerProps> = ({
  experiment,
  sequence,
  well,
  imageInfo,
  channelStates,
  maskStates,
  intensityMode,
  showComposite,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [level, setLevel] = useState(0);

  // Calculate appropriate pyramid level based on zoom
  useEffect(() => {
    const newLevel = Math.max(0, Math.floor(-Math.log2(zoom)));
    if (newLevel < imageInfo.num_levels) {
      setLevel(newLevel);
    }
  }, [zoom, imageInfo.num_levels]);

  // Render tiles
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Calculate visible tile range
    const [height, width] = imageInfo.shape;
    const scaledWidth = width * zoom;
    const scaledHeight = height * zoom;

    const viewWidth = canvas.width;
    const viewHeight = canvas.height;

    // Center image initially
    const offsetX = pan.x + (viewWidth - scaledWidth) / 2;
    const offsetY = pan.y + (viewHeight - scaledHeight) / 2;

    // Calculate tile grid bounds
    const levelScale = Math.pow(2, level);
    const levelWidth = width / levelScale;
    const levelHeight = height / levelScale;

    const tilesX = Math.ceil(levelWidth / TILE_SIZE);
    const tilesY = Math.ceil(levelHeight / TILE_SIZE);

    // Determine visible tile range
    const tileStartX = Math.max(0, Math.floor(-offsetX / (TILE_SIZE * zoom)));
    const tileEndX = Math.min(tilesX, Math.ceil((viewWidth - offsetX) / (TILE_SIZE * zoom)));
    const tileStartY = Math.max(0, Math.floor(-offsetY / (TILE_SIZE * zoom)));
    const tileEndY = Math.min(tilesY, Math.ceil((viewHeight - offsetY) / (TILE_SIZE * zoom)));

    // Load and render tiles
    const renderTile = (tileX: number, tileY: number) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';

      let tileUrl: string;

      if (showComposite) {
        // Composite mode
        const channelOpacities: Record<string, number> = {};
        const channelVisibility: Record<string, boolean> = {};

        imageInfo.channels.forEach((ch) => {
          const state = channelStates[ch.name];
          if (state) {
            channelOpacities[ch.name] = state.opacity;
            channelVisibility[ch.name] = state.visible;
          }
        });

        tileUrl = tileApi.getCompositeTileUrl(
          experiment,
          sequence,
          well,
          level,
          tileX,
          tileY,
          {
            tileSize: TILE_SIZE,
            mode: intensityMode,
            channelOpacities,
            channelVisibility,
          }
        );
      } else {
        // Single channel mode (show first visible channel)
        const visibleChannel = imageInfo.channels.find(
          (ch) => channelStates[ch.name]?.visible
        );

        if (!visibleChannel) return;

        tileUrl = tileApi.getTileUrl(
          experiment,
          sequence,
          well,
          visibleChannel.name,
          level,
          tileX,
          tileY,
          TILE_SIZE
        );
      }

      img.onload = () => {
        const x = offsetX + tileX * TILE_SIZE * zoom;
        const y = offsetY + tileY * TILE_SIZE * zoom;
        ctx.drawImage(img, x, y, TILE_SIZE * zoom, TILE_SIZE * zoom);
      };

      img.src = tileUrl;
    };

    // Render visible tiles
    for (let ty = tileStartY; ty < tileEndY; ty++) {
      for (let tx = tileStartX; tx < tileEndX; tx++) {
        renderTile(tx, ty);
      }
    }
  }, [
    experiment,
    sequence,
    well,
    imageInfo,
    channelStates,
    maskStates,
    intensityMode,
    showComposite,
    zoom,
    pan,
    level,
  ]);

  // Mouse handlers for pan
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  }, [pan]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging) return;
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    },
    [isDragging, dragStart]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Wheel handler for zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom((prev) => Math.max(0.1, Math.min(10, prev * delta)));
  }, []);

  return (
    <div className="relative w-full h-full bg-black">
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        className="w-full h-full cursor-move"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      />

      {/* Zoom controls */}
      <div className="absolute top-4 right-4 bg-gray-800 bg-opacity-90 p-2 rounded flex flex-col gap-2">
        <button
          onClick={() => setZoom((z) => Math.min(10, z * 1.2))}
          className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded"
        >
          +
        </button>
        <div className="text-center text-xs">{Math.round(zoom * 100)}%</div>
        <button
          onClick={() => setZoom((z) => Math.max(0.1, z / 1.2))}
          className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded"
        >
          -
        </button>
        <button
          onClick={() => {
            setZoom(1);
            setPan({ x: 0, y: 0 });
          }}
          className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs"
        >
          Reset
        </button>
      </div>

      {/* Level indicator */}
      <div className="absolute bottom-4 right-4 bg-gray-800 bg-opacity-90 px-3 py-1 rounded text-xs">
        Level: {level} / {imageInfo.num_levels - 1}
      </div>
    </div>
  );
};
