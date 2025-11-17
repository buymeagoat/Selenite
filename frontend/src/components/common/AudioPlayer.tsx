import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, Volume2, Download } from 'lucide-react';

interface AudioPlayerProps {
  src: string;
  filename: string;
  duration: number; // seconds
  onTimeUpdate?: (currentTime: number) => void;
}

export const AudioPlayer: React.FC<AudioPlayerProps> = ({
  src,
  filename,
  duration,
  onTimeUpdate
}) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(1);
  const [playbackRate, setPlaybackRate] = useState(1);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
      if (onTimeUpdate) {
        onTimeUpdate(audio.currentTime);
      }
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [onTimeUpdate]);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    if (!audio) return;

    const newTime = parseFloat(e.target.value);
    audio.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    if (!audio) return;

    const newVolume = parseFloat(e.target.value);
    audio.volume = newVolume;
    setVolume(newVolume);
  };

  const handleSpeedChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const audio = audioRef.current;
    if (!audio) return;

    const newRate = parseFloat(e.target.value);
    audio.playbackRate = newRate;
    setPlaybackRate(newRate);
  };

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = src;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="bg-sage-light rounded-lg p-4">
      <audio ref={audioRef} src={src} preload="metadata" />
      
      {/* Filename */}
      <div className="text-sm font-medium text-pine-deep mb-3">
        {filename}
      </div>

      {/* Controls Row */}
      <div className="flex items-center gap-4 mb-2">
        {/* Play/Pause Button */}
        <button
          type="button"
          onClick={togglePlay}
          aria-label={isPlaying ? 'Pause' : 'Play'}
          className="w-10 h-10 flex items-center justify-center bg-forest-green text-white rounded-full hover:bg-pine-deep transition-colors"
        >
          {isPlaying ? (
            <Pause className="w-5 h-5" />
          ) : (
            <Play className="w-5 h-5 ml-0.5" />
          )}
        </button>

        {/* Time Display */}
        <div className="text-sm text-pine-mid whitespace-nowrap">
          {formatTime(currentTime)} / {formatTime(duration)}
        </div>

        {/* Speed Selector */}
        <select
          value={playbackRate}
          onChange={handleSpeedChange}
          aria-label="Speed"
          className="text-sm px-2 py-1 border border-gray-300 rounded bg-white text-pine-deep focus:outline-none focus:ring-2 focus:ring-forest-green"
        >
          <option value="0.5">0.5x</option>
          <option value="0.75">0.75x</option>
          <option value="1">1x</option>
          <option value="1.25">1.25x</option>
          <option value="1.5">1.5x</option>
          <option value="2">2x</option>
        </select>

        {/* Volume Control */}
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Volume2 className="w-4 h-4 text-pine-mid flex-shrink-0" />
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={volume}
            onChange={handleVolumeChange}
            aria-label="Volume"
            className="w-full max-w-24"
          />
        </div>

        {/* Download Button */}
        <button
          type="button"
          onClick={handleDownload}
          aria-label="Download"
          className="p-2 text-pine-mid hover:text-forest-green transition-colors"
        >
          <Download className="w-5 h-5" />
        </button>
      </div>

      {/* Seek Bar */}
      <input
        type="range"
        min="0"
        max={duration}
        step="0.1"
        value={currentTime}
        onChange={handleSeek}
        aria-label="Seek"
        className="w-full"
      />
    </div>
  );
};
