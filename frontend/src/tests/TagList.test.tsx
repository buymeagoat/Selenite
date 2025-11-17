import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { TagList } from '../components/tags/TagList';

const mockTags = [
  { id: 1, name: 'interviews', color: '#0F3D2E', job_count: 5 },
  { id: 2, name: 'marketing', color: '#B5543A', job_count: 12 },
  { id: 3, name: 'research', color: '#C9A227', job_count: 0 }
];

describe('TagList', () => {
  it('renders tag list with all tags', () => {
    render(<TagList tags={mockTags} onEdit={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.getByText('interviews')).toBeInTheDocument();
    expect(screen.getByText('marketing')).toBeInTheDocument();
    expect(screen.getByText('research')).toBeInTheDocument();
  });

  it('displays job count for each tag', () => {
    render(<TagList tags={mockTags} onEdit={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('shows color dot for each tag', () => {
    render(<TagList tags={mockTags} onEdit={vi.fn()} onDelete={vi.fn()} />);
    const colorDots = screen.getAllByTestId('tag-color-dot');
    expect(colorDots).toHaveLength(3);
  });

  it('calls onEdit when edit button clicked', () => {
    const handleEdit = vi.fn();
    render(<TagList tags={mockTags} onEdit={handleEdit} onDelete={vi.fn()} />);
    const editButtons = screen.getAllByRole('button', { name: /edit/i });
    fireEvent.click(editButtons[0]);
    expect(handleEdit).toHaveBeenCalledWith(1);
  });

  it('calls onDelete when delete button clicked', () => {
    const handleDelete = vi.fn();
    render(<TagList tags={mockTags} onEdit={vi.fn()} onDelete={handleDelete} />);
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    fireEvent.click(deleteButtons[1]);
    expect(handleDelete).toHaveBeenCalledWith(2);
  });

  it('shows empty state when no tags', () => {
    render(<TagList tags={[]} onEdit={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.getByText(/no tags created yet/i)).toBeInTheDocument();
  });

  it('renders as table on desktop', () => {
    render(<TagList tags={mockTags} onEdit={vi.fn()} onDelete={vi.fn()} />);
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  it('displays tag names in correct order', () => {
    render(<TagList tags={mockTags} onEdit={vi.fn()} onDelete={vi.fn()} />);
    const tagNames = screen.getAllByTestId('tag-name');
    expect(tagNames[0]).toHaveTextContent('interviews');
    expect(tagNames[1]).toHaveTextContent('marketing');
    expect(tagNames[2]).toHaveTextContent('research');
  });
});
