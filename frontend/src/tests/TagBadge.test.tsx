import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { TagBadge } from '../components/tags/TagBadge';

const mockTag = { id: 1, name: 'interviews', color: '#0F3D2E' };

describe('TagBadge', () => {
  it('renders tag name', () => {
    render(<TagBadge tag={mockTag} />);
    expect(screen.getByText('interviews')).toBeInTheDocument();
  });

  it('applies tag color as background', () => {
    render(<TagBadge tag={mockTag} />);
    const badge = screen.getByText('interviews');
    expect(badge).toHaveStyle({ backgroundColor: '#0F3D2E' });
  });

  it('renders with small size', () => {
    render(<TagBadge tag={mockTag} size="sm" />);
    const badge = screen.getByText('interviews');
    expect(badge).toHaveClass('text-xs', 'px-2', 'py-1');
  });

  it('renders with medium size by default', () => {
    render(<TagBadge tag={mockTag} />);
    const badge = screen.getByText('interviews');
    expect(badge).toHaveClass('text-sm', 'px-3', 'py-1');
  });

  it('shows remove button when onRemove provided', () => {
    render(<TagBadge tag={mockTag} onRemove={vi.fn()} />);
    expect(screen.getByRole('button', { name: /remove/i })).toBeInTheDocument();
  });

  it('does not show remove button when onRemove not provided', () => {
    render(<TagBadge tag={mockTag} />);
    expect(screen.queryByRole('button', { name: /remove/i })).not.toBeInTheDocument();
  });

  it('calls onRemove with tag id when X clicked', () => {
    const handleRemove = vi.fn();
    render(<TagBadge tag={mockTag} onRemove={handleRemove} />);
    const removeBtn = screen.getByRole('button', { name: /remove/i });
    fireEvent.click(removeBtn);
    expect(handleRemove).toHaveBeenCalledWith(1);
  });

  it('is clickable when onClick provided', () => {
    const handleClick = vi.fn();
    render(<TagBadge tag={mockTag} onClick={handleClick} />);
    const badge = screen.getByText('interviews');
    fireEvent.click(badge);
    expect(handleClick).toHaveBeenCalledWith(1);
  });

  it('adds cursor-pointer class when onClick provided', () => {
    render(<TagBadge tag={mockTag} onClick={vi.fn()} />);
    const badge = screen.getByText('interviews');
    expect(badge).toHaveClass('cursor-pointer');
  });

  it('does not add cursor-pointer when onClick not provided', () => {
    render(<TagBadge tag={mockTag} />);
    const badge = screen.getByText('interviews');
    expect(badge).not.toHaveClass('cursor-pointer');
  });
});
