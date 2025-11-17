import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { Settings } from '../pages/Settings';

// Mock child components
vi.mock('../components/tags/TagList', () => ({
  TagList: ({ tags, onEdit, onDelete }: any) => (
    <div data-testid="tag-list">
      {tags.map((t: any) => (
        <div key={t.id}>
          {t.name}
          <button onClick={() => onEdit(t.id)}>Edit</button>
          <button onClick={() => onDelete(t.id)}>Delete</button>
        </div>
      ))}
    </div>
  )
}));

describe('Settings', () => {
  it('renders all settings sections', () => {
    render(<Settings />);
    expect(screen.getByText(/account/i)).toBeInTheDocument();
    expect(screen.getByText(/default transcription options/i)).toBeInTheDocument();
    expect(screen.getByText(/performance/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /storage/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /tags/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /system/i })).toBeInTheDocument();
  });

  it('renders change password form', () => {
    render(<Settings />);
    expect(screen.getByLabelText(/current password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
  });

  it('renders default transcription options', () => {
    render(<Settings />);
    expect(screen.getByLabelText(/default model/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/default language/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/timestamps/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/speaker detection/i)).toBeInTheDocument();
  });

  it('renders performance settings', () => {
    render(<Settings />);
    expect(screen.getByLabelText(/max concurrent jobs/i)).toBeInTheDocument();
  });

  it('displays storage information', () => {
    render(<Settings />);
    expect(screen.getByText(/used space/i)).toBeInTheDocument();
    expect(screen.getByText(/location/i)).toBeInTheDocument();
    // Storage heading exists in the settings
    expect(screen.getByRole('heading', { name: /storage/i })).toBeInTheDocument();
  });

  it('renders tag list section', () => {
    render(<Settings />);
    // Tag list is mocked and renders with testid
    // Expand tags to render list if collapsible
    expect(screen.getByRole('heading', { name: /tags/i })).toBeInTheDocument();
  });

  it('renders system control buttons', () => {
    render(<Settings />);
    expect(screen.getByRole('button', { name: /restart server/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /shutdown server/i })).toBeInTheDocument();
  });

  it('submits password change form', () => {
    render(<Settings />);
    const currentPw = screen.getByLabelText(/current password/i);
    const newPw = screen.getByLabelText(/new password/i);
    const confirmPw = screen.getByLabelText(/confirm password/i);
    fireEvent.change(currentPw, { target: { value: 'oldpass' } });
    fireEvent.change(newPw, { target: { value: 'newpass123' } });
    fireEvent.change(confirmPw, { target: { value: 'newpass123' } });
    const saveBtn = screen.getAllByRole('button', { name: /save/i })[0];
    fireEvent.click(saveBtn);
    // Placeholder: Would check API call
  });

  it('saves default transcription options', () => {
    render(<Settings />);
    const modelSelect = screen.getByLabelText(/default model/i);
    fireEvent.change(modelSelect, { target: { value: 'large' } });
    const saveBtn = screen.getAllByRole('button', { name: /save/i })[1];
    fireEvent.click(saveBtn);
    // Placeholder: Would check API call
  });

  it('adjusts max concurrent jobs slider', () => {
    render(<Settings />);
    const slider = screen.getByLabelText(/max concurrent jobs/i) as HTMLInputElement;
    fireEvent.change(slider, { target: { value: '3' } });
    expect(slider.value).toBe('3');
  });
});
