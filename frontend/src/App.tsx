/**
 * Main App Component
 */

import React, { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { experimentApi, metadataApi } from './api';
import { PlateBrowser } from './components/PlateBrowser';
import { ImageViewer } from './components/ImageViewer';
import { ChannelControls } from './components/ChannelControls';
import { MaskControls } from './components/MaskControls';
import { ViewerControls } from './components/ViewerControls';
import type { ChannelState, MaskState, IntensityMode } from './types';

const queryClient = new QueryClient();

function AppContent() {
  const [selectedExperiment, setSelectedExperiment] = useState<string>('');
  const [selectedSequence, setSelectedSequence] = useState<string>('');
  const [selectedWell, setSelectedWell] = useState<string>('');

  // Channel and mask states
  const [channelStates, setChannelStates] = useState<Record<string, ChannelState>>({});
  const [maskStates, setMaskStates] = useState<Record<string, MaskState>>({});
  const [intensityMode, setIntensityMode] = useState<IntensityMode>('normalized');
  const [showComposite, setShowComposite] = useState(true);

  // Fetch experiments
  const { data: experiments } = useQuery({
    queryKey: ['experiments'],
    queryFn: experimentApi.listExperiments,
  });

  // Fetch sequences
  const { data: sequences } = useQuery({
    queryKey: ['sequences', selectedExperiment],
    queryFn: () => experimentApi.listSequences(selectedExperiment),
    enabled: !!selectedExperiment,
  });

  // Fetch plate metadata
  const { data: plateMetadata } = useQuery({
    queryKey: ['plate', selectedExperiment, selectedSequence],
    queryFn: () => metadataApi.getPlateMetadata(selectedExperiment, selectedSequence),
    enabled: !!selectedExperiment && !!selectedSequence,
  });

  // Fetch image info when well is selected
  const { data: imageInfo } = useQuery({
    queryKey: ['image', selectedExperiment, selectedSequence, selectedWell],
    queryFn: () =>
      metadataApi.getImageInfo(selectedExperiment, selectedSequence, selectedWell),
    enabled: !!selectedExperiment && !!selectedSequence && !!selectedWell,
  });

  // Initialize channel and mask states when image info loads
  useEffect(() => {
    if (imageInfo) {
      // Initialize channel states
      const newChannelStates: Record<string, ChannelState> = {};
      imageInfo.channels.forEach((ch) => {
        newChannelStates[ch.name] = {
          visible: true,
          opacity: 1.0,
        };
      });
      setChannelStates(newChannelStates);

      // Initialize mask states
      const newMaskStates: Record<string, MaskState> = {};
      imageInfo.masks.forEach((mask) => {
        newMaskStates[mask.name] = {
          visible: false,
          opacity: 0.5,
        };
      });
      setMaskStates(newMaskStates);
    }
  }, [imageInfo]);

  // Auto-select first experiment
  useEffect(() => {
    if (experiments && experiments.length > 0 && !selectedExperiment) {
      setSelectedExperiment(experiments[0].experiment_id);
    }
  }, [experiments, selectedExperiment]);

  // Auto-select first sequence
  useEffect(() => {
    if (sequences && sequences.length > 0 && !selectedSequence) {
      setSelectedSequence(sequences[0].sequence_id);
    }
  }, [sequences, selectedSequence]);

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <h1 className="text-2xl font-bold">PICA Microscopy Viewer</h1>
        <p className="text-sm text-gray-400 mt-1">
          High-performance OME-TIFF and OME-Zarr viewer
        </p>
      </header>

      {/* Experiment/Sequence selectors */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-3 flex gap-4">
        <div>
          <label className="text-xs text-gray-400 block mb-1">Experiment</label>
          <select
            value={selectedExperiment}
            onChange={(e) => {
              setSelectedExperiment(e.target.value);
              setSelectedSequence('');
              setSelectedWell('');
            }}
            className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
          >
            <option value="">Select...</option>
            {experiments?.map((exp) => (
              <option key={exp.experiment_id} value={exp.experiment_id}>
                {exp.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs text-gray-400 block mb-1">Sequence</label>
          <select
            value={selectedSequence}
            onChange={(e) => {
              setSelectedSequence(e.target.value);
              setSelectedWell('');
            }}
            disabled={!selectedExperiment}
            className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm disabled:opacity-50"
          >
            <option value="">Select...</option>
            {sequences?.map((seq) => (
              <option key={seq.sequence_id} value={seq.sequence_id}>
                {seq.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main content */}
      <div className="flex h-[calc(100vh-180px)]">
        {/* Left sidebar - Plate browser */}
        <div className="w-96 bg-gray-800 border-r border-gray-700 overflow-y-auto">
          {plateMetadata ? (
            <PlateBrowser
              plateMetadata={plateMetadata}
              selectedWell={selectedWell}
              onWellSelect={setSelectedWell}
            />
          ) : (
            <div className="p-4 text-gray-400 text-sm">
              Select an experiment and sequence to view plate layout.
            </div>
          )}
        </div>

        {/* Center - Image viewer */}
        <div className="flex-1 bg-black">
          {imageInfo && selectedWell ? (
            <ImageViewer
              experiment={selectedExperiment}
              sequence={selectedSequence}
              well={selectedWell}
              imageInfo={imageInfo}
              channelStates={channelStates}
              maskStates={maskStates}
              intensityMode={intensityMode}
              showComposite={showComposite}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              Select a well to view image
            </div>
          )}
        </div>

        {/* Right sidebar - Controls */}
        <div className="w-80 bg-gray-800 border-l border-gray-700 overflow-y-auto p-4 space-y-4">
          {imageInfo ? (
            <>
              <ViewerControls
                showComposite={showComposite}
                intensityMode={intensityMode}
                onCompositeChange={setShowComposite}
                onIntensityModeChange={setIntensityMode}
              />

              <ChannelControls
                channels={imageInfo.channels}
                channelStates={channelStates}
                onChannelStateChange={(channel, state) => {
                  setChannelStates((prev) => ({
                    ...prev,
                    [channel]: state,
                  }));
                }}
              />

              <MaskControls
                masks={imageInfo.masks}
                maskStates={maskStates}
                onMaskStateChange={(mask, state) => {
                  setMaskStates((prev) => ({
                    ...prev,
                    [mask]: state,
                  }));
                }}
              />

              {/* Image info */}
              <div className="p-4 bg-gray-800 rounded-lg text-xs">
                <h3 className="font-bold mb-2">Image Info</h3>
                <div className="space-y-1 text-gray-400">
                  <div>Well: {imageInfo.well_id}</div>
                  <div>
                    Size: {imageInfo.shape[1]} × {imageInfo.shape[0]}
                  </div>
                  <div>Levels: {imageInfo.num_levels}</div>
                  <div>Format: {imageInfo.format.toUpperCase()}</div>
                </div>
              </div>
            </>
          ) : (
            <div className="text-gray-400 text-sm">
              Select a well to view controls
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}

export default App;
