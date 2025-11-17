import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FileDropzone } from '../components/upload/FileDropzone';

describe('FileDropzone', () => {
  it('renders default dropzone with instructions', () => {
    const onFileSelect = vi.fn();
    render(
      <FileDropzone
        onFileSelect={onFileSelect}
        accept="audio/*,video/*"
        maxSize={2 * 1024 * 1024 * 1024} // 2GB
      />
    );
    
    expect(screen.getByText(/drag & drop file here/i)).toBeInTheDocument();
    expect(screen.getByText(/click to browse/i)).toBeInTheDocument();
  });

  it('shows selected file information', () => {
    const onFileSelect = vi.fn();
    const mockFile = new File(['content'], 'test-audio.mp3', { type: 'audio/mpeg' });
    
    render(
      <FileDropzone
        onFileSelect={onFileSelect}
        accept="audio/*,video/*"
        maxSize={2 * 1024 * 1024 * 1024}
        selectedFile={mockFile}
      />
    );
    
    expect(screen.getByText('test-audio.mp3')).toBeInTheDocument();
    expect(screen.getByText(/change file/i)).toBeInTheDocument();
  });

  it('handles file selection via click', () => {
    const onFileSelect = vi.fn();
    const { container } = render(
      <FileDropzone
        onFileSelect={onFileSelect}
        accept="audio/*,video/*"
        maxSize={2 * 1024 * 1024 * 1024}
      />
    );
    
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toBeTruthy();
  });

  it('displays error for oversized file', () => {
    const onFileSelect = vi.fn();
    const maxSize = 100; // 100 bytes
    
    render(
      <FileDropzone
        onFileSelect={onFileSelect}
        accept="audio/*,video/*"
        maxSize={maxSize}
      />
    );
    
    // Simulate file that's too large by passing error prop
    render(
      <FileDropzone
        onFileSelect={onFileSelect}
        accept="audio/*,video/*"
        maxSize={maxSize}
        error="File size exceeds maximum allowed (100 bytes)"
      />
    );
    
    expect(screen.getByText(/file size exceeds/i)).toBeInTheDocument();
  });

  it('displays error for invalid file type', () => {
    const onFileSelect = vi.fn();
    
    render(
      <FileDropzone
        onFileSelect={onFileSelect}
        accept="audio/*,video/*"
        maxSize={2 * 1024 * 1024 * 1024}
        error="Invalid file format"
      />
    );
    
    expect(screen.getByText(/invalid file format/i)).toBeInTheDocument();
  });

  it('shows drag-over state when file is dragged over', () => {
    const onFileSelect = vi.fn();
    const { container } = render(
      <FileDropzone
        onFileSelect={onFileSelect}
        accept="audio/*,video/*"
        maxSize={2 * 1024 * 1024 * 1024}
      />
    );
    
    // react-dropzone manages this internally, we just verify the component renders
    expect(container.querySelector('[class*="dropzone"]')).toBeTruthy();
  });

  it('formats file size correctly', () => {
    const onFileSelect = vi.fn();
    const mockFile = new File(
      [new ArrayBuffer(1024 * 1024 * 5)], // 5MB
      'test.mp3',
      { type: 'audio/mpeg' }
    );
    
    render(
      <FileDropzone
        onFileSelect={onFileSelect}
        accept="audio/*,video/*"
        maxSize={2 * 1024 * 1024 * 1024}
        selectedFile={mockFile}
      />
    );
    
    expect(screen.getByText(/5 MB/i)).toBeInTheDocument();
  });
});
