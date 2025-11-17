import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { TagInput } from '../components/tags/TagInput';

const mockTags = [
  { id: 1, name: 'interviews', color: '#0F3D2E' },
  { id: 2, name: 'marketing', color: '#B5543A' },
  { id: 3, name: 'research', color: '#C9A227' }
];

describe('TagInput', () => {
  it('renders input with placeholder', () => {
    render(<TagInput availableTags={mockTags} selectedTags={[]} onChange={vi.fn()} onCreate={vi.fn()} placeholder="Add tags" />);
    expect(screen.getByPlaceholderText('Add tags')).toBeInTheDocument();
  });

  it('shows autocomplete dropdown when typing', () => {
    render(<TagInput availableTags={mockTags} selectedTags={[]} onChange={vi.fn()} onCreate={vi.fn()} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'inter' } });
    expect(screen.getByText('interviews')).toBeInTheDocument();
  });

  it('filters autocomplete results based on input', () => {
    render(<TagInput availableTags={mockTags} selectedTags={[]} onChange={vi.fn()} onCreate={vi.fn()} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'mar' } });
    expect(screen.getByText('marketing')).toBeInTheDocument();
    expect(screen.queryByText('interviews')).not.toBeInTheDocument();
  });

  it('selects tag from dropdown and adds to selected', () => {
    const handleChange = vi.fn();
    render(<TagInput availableTags={mockTags} selectedTags={[]} onChange={handleChange} onCreate={vi.fn()} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'research' } });
    fireEvent.click(screen.getByText('research'));
    expect(handleChange).toHaveBeenCalledWith([3]);
  });

  it('displays selected tags as pills', () => {
    render(<TagInput availableTags={mockTags} selectedTags={[1, 2]} onChange={vi.fn()} onCreate={vi.fn()} />);
    expect(screen.getByText('interviews')).toBeInTheDocument();
    expect(screen.getByText('marketing')).toBeInTheDocument();
  });

  it('removes tag when X clicked on pill', () => {
    const handleChange = vi.fn();
    render(<TagInput availableTags={mockTags} selectedTags={[1, 2]} onChange={handleChange} onCreate={vi.fn()} />);
    const removeButtons = screen.getAllByRole('button', { name: /remove/i });
    fireEvent.click(removeButtons[0]);
    expect(handleChange).toHaveBeenCalledWith([2]);
  });

  it('shows create option when no matching tags', () => {
    render(<TagInput availableTags={mockTags} selectedTags={[]} onChange={vi.fn()} onCreate={vi.fn()} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'newtagname' } });
    expect(screen.getByText(/create new tag:/i)).toBeInTheDocument();
  });

  it('calls onCreate when create option selected', async () => {
    const handleCreate = vi.fn().mockResolvedValue({ id: 4, name: 'newtagname', color: '#000000' });
    const handleChange = vi.fn();
    render(<TagInput availableTags={mockTags} selectedTags={[]} onChange={handleChange} onCreate={handleCreate} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'newtagname' } });
    fireEvent.click(screen.getByText(/create new tag:/i));
    expect(handleCreate).toHaveBeenCalledWith('newtagname');
  });

  it('calls onCreate and adds new tag when Enter pressed with no match', async () => {
    const handleCreate = vi.fn().mockResolvedValue({ id: 4, name: 'urgent', color: '#FF0000' });
    const handleChange = vi.fn();
    render(<TagInput availableTags={mockTags} selectedTags={[]} onChange={handleChange} onCreate={handleCreate} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'urgent' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(handleCreate).toHaveBeenCalledWith('urgent');
  });

  it('does not show already selected tags in dropdown', () => {
    render(<TagInput availableTags={mockTags} selectedTags={[1]} onChange={vi.fn()} onCreate={vi.fn()} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'i' } });
    expect(screen.queryByText('interviews')).not.toBeInTheDocument();
  });

  it('clears input after selecting tag', () => {
    render(<TagInput availableTags={mockTags} selectedTags={[]} onChange={vi.fn()} onCreate={vi.fn()} />);
    const input = screen.getByRole('textbox') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'research' } });
    fireEvent.click(screen.getByText('research'));
    expect(input.value).toBe('');
  });
});
