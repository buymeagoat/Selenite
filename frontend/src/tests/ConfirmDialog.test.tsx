import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConfirmDialog } from '../components/modals/ConfirmDialog';

describe('ConfirmDialog', () => {
  const mockOnConfirm = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    mockOnConfirm.mockClear();
    mockOnCancel.mockClear();
  });

  it('does not render when isOpen is false', () => {
    render(
      <ConfirmDialog
        isOpen={false}
        title="Delete Item?"
        message="Are you sure?"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    expect(screen.queryByText('Delete Item?')).not.toBeInTheDocument();
  });

  it('renders dialog when isOpen is true', () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Delete Item?"
        message="Are you sure you want to delete this item?"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    expect(screen.getByText('Delete Item?')).toBeInTheDocument();
    expect(screen.getByText('Are you sure you want to delete this item?')).toBeInTheDocument();
  });

  it('shows default button text', () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Confirm Action"
        message="Please confirm"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    expect(screen.getByText('Cancel')).toBeInTheDocument();
    expect(screen.getByText('Confirm')).toBeInTheDocument();
  });

  it('shows custom button text when provided', () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Delete"
        message="Confirm deletion"
        confirmText="Delete Forever"
        cancelText="Go Back"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    expect(screen.getByText('Go Back')).toBeInTheDocument();
    expect(screen.getByText('Delete Forever')).toBeInTheDocument();
  });

  it('calls onCancel when cancel button is clicked', () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Delete"
        message="Are you sure?"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    fireEvent.click(screen.getByText('Cancel'));
    expect(mockOnCancel).toHaveBeenCalledTimes(1);
    expect(mockOnConfirm).not.toHaveBeenCalled();
  });

  it('calls onConfirm when confirm button is clicked', () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Delete"
        message="Are you sure?"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    fireEvent.click(screen.getByText('Confirm'));
    expect(mockOnConfirm).toHaveBeenCalledTimes(1);
    expect(mockOnCancel).not.toHaveBeenCalled();
  });

  it('applies danger variant styling', () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Delete"
        message="This is destructive"
        variant="danger"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    const confirmButton = screen.getByText('Confirm');
    expect(confirmButton).toHaveClass('bg-red-600');
  });

  it('applies warning variant styling', () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Warning"
        message="This is a warning"
        variant="warning"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    const confirmButton = screen.getByText('Confirm');
    expect(confirmButton).toHaveClass('bg-amber-500');
  });

  it('applies info variant styling', () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Info"
        message="This is informational"
        variant="info"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    const confirmButton = screen.getByText('Confirm');
    expect(confirmButton).toHaveClass('bg-forest-green');
  });
});
