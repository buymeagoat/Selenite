import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AudioPlayer } from '../components/common/AudioPlayer';

describe('AudioPlayer', () => {
  const mockOnTimeUpdate = vi.fn();

  beforeEach(() => {
    mockOnTimeUpdate.mockClear();
    // Mock HTML5 Audio
    window.HTMLMediaElement.prototype.play = vi.fn();
    window.HTMLMediaElement.prototype.pause = vi.fn();
  });

  it('renders player with filename', () => {
    render(
      <AudioPlayer
        src="https://example.com/audio.mp3"
        filename="test-audio.mp3"
        duration={180}
      />
    );
    
    expect(screen.getByText('test-audio.mp3')).toBeInTheDocument();
  });

  it('displays formatted duration', () => {
    render(
      <AudioPlayer
        src="https://example.com/audio.mp3"
        filename="test.mp3"
        duration={185} // 3:05
      />
    );
    
    expect(screen.getByText(/3:05/)).toBeInTheDocument();
  });

  it('shows play button initially', () => {
    render(
      <AudioPlayer
        src="https://example.com/audio.mp3"
        filename="test.mp3"
        duration={60}
      />
    );
    
    const playButton = screen.getByRole('button', { name: /play/i });
    expect(playButton).toBeInTheDocument();
  });

  it('toggles to pause button when playing', () => {
    render(
      <AudioPlayer
        src="https://example.com/audio.mp3"
        filename="test.mp3"
        duration={60}
      />
    );
    
    const playButton = screen.getByRole('button', { name: /play/i });
    fireEvent.click(playButton);
    
    expect(screen.getByRole('button', { name: /pause/i })).toBeInTheDocument();
  });

  it('renders speed selector with options', () => {
    render(
      <AudioPlayer
        src="https://example.com/audio.mp3"
        filename="test.mp3"
        duration={60}
      />
    );
    
    const speedSelect = screen.getByLabelText(/speed/i) as HTMLSelectElement;
    expect(speedSelect).toBeInTheDocument();
    expect(speedSelect.value).toBe('1');
  });

  it('changes playback speed when selected', () => {
    render(
      <AudioPlayer
        src="https://example.com/audio.mp3"
        filename="test.mp3"
        duration={60}
      />
    );
    
    const speedSelect = screen.getByLabelText(/speed/i) as HTMLSelectElement;
    fireEvent.change(speedSelect, { target: { value: '1.5' } });
    expect(speedSelect.value).toBe('1.5');
  });

  it('renders volume control', () => {
    render(
      <AudioPlayer
        src="https://example.com/audio.mp3"
        filename="test.mp3"
        duration={60}
      />
    );
    
    const volumeSlider = screen.getByRole('slider', { name: /volume/i });
    expect(volumeSlider).toBeInTheDocument();
  });

  it('renders download button', () => {
    render(
      <AudioPlayer
        src="https://example.com/audio.mp3"
        filename="test.mp3"
        duration={60}
      />
    );
    
    const downloadButton = screen.getByRole('button', { name: /download/i });
    expect(downloadButton).toBeInTheDocument();
  });

  it('renders seek bar', () => {
    render(
      <AudioPlayer
        src="https://example.com/audio.mp3"
        filename="test.mp3"
        duration={60}
      />
    );
    
    const seekBar = screen.getByRole('slider', { name: /seek/i });
    expect(seekBar).toBeInTheDocument();
  });
});
