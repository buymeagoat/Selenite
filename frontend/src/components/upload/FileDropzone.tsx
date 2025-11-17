import React from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileAudio, FileVideo, X } from 'lucide-react';

interface FileDropzoneProps {
  onFileSelect: (file: File) => void;
  accept: string;
  maxSize: number; // bytes
  selectedFile?: File | null;
  error?: string;
}

export const FileDropzone: React.FC<FileDropzoneProps> = ({
  onFileSelect,
  maxSize,
  selectedFile,
  error
}) => {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'audio/*': ['.mp3', '.wav', '.m4a', '.flac', '.ogg'],
      'video/*': ['.mp4', '.avi', '.mov', '.mkv']
    },
    maxSize,
    multiple: false,
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        onFileSelect(acceptedFiles[0]);
      }
    }
  });

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (file: File) => {
    if (file.type.startsWith('audio/')) {
      return <FileAudio className="w-8 h-8 text-pine-mid" />;
    }
    if (file.type.startsWith('video/')) {
      return <FileVideo className="w-8 h-8 text-pine-mid" />;
    }
    return <Upload className="w-8 h-8 text-pine-mid" />;
  };

  if (selectedFile) {
    return (
      <div className="border-2 border-gray-200 rounded-lg p-6 min-h-[200px] flex flex-col items-center justify-center bg-white">
        {getFileIcon(selectedFile)}
        <div className="mt-4 text-center">
          <p className="text-pine-deep font-medium">{selectedFile.name}</p>
          <p className="text-sm text-pine-mid mt-1">
            {formatFileSize(selectedFile.size)} • {selectedFile.type || 'Unknown type'}
          </p>
        </div>
        <button
          type="button"
          onClick={() => onFileSelect(null as any)}
          className="mt-4 text-sm text-forest-green hover:text-pine-deep flex items-center gap-1"
        >
          <X className="w-4 h-4" />
          Change file
        </button>
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={`dropzone border-2 border-dashed rounded-lg p-8 min-h-[200px] flex flex-col items-center justify-center cursor-pointer transition-colors ${
        isDragActive
          ? 'border-forest-green bg-sage-light'
          : error
          ? 'border-red-300 bg-red-50'
          : 'border-gray-300 bg-white hover:border-gray-400'
      }`}
      data-testid="file-dropzone"
    >
      <input {...getInputProps()} />
      
      {error ? (
        <>
          <X className="w-12 h-12 text-red-500 mb-4" />
          <p className="text-red-600 text-center font-medium">{error}</p>
        </>
      ) : (
        <>
          <Upload className="w-12 h-12 text-pine-mid mb-4" />
          {isDragActive ? (
            <p className="text-pine-deep font-medium text-center">
              Drop file here
            </p>
          ) : (
            <>
              <p className="text-pine-deep font-medium text-center">
                Drag & drop file here, or click to browse
              </p>
              <p className="text-sm text-pine-mid mt-2 text-center">
                Supports audio and video files up to {formatFileSize(maxSize)}
              </p>
            </>
          )}
        </>
      )}
    </div>
  );
};
