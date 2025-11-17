import React from 'react';
import { render, screen, within, waitFor, fireEvent } from '@testing-library/react';
import { act } from 'react';
import userEvent from '@testing-library/user-event';
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

  it('shows autocomplete dropdown when typing', async () => {
    render(<TagInput availableTags={mockTags} selectedTags={[]} onChange={vi.fn()} onCreate={vi.fn()} />);
    const input = screen.getByRole('textbox');
    await userEvent.type(input, 'inter');
    expect(screen.getByText('interviews')).toBeInTheDocument();
  });

  it('filters autocomplete results based on input', async () => {
    render(<TagInput availableTags={mockTags} selectedTags={[]} onChange={vi.fn()} onCreate={vi.fn()} />);
    const input = screen.getByRole('textbox');
    await userEvent.type(input, 'mar');
    expect(screen.getByText('marketing')).toBeInTheDocument();
    expect(screen.queryByText('interviews')).not.toBeInTheDocument();
  });

  it('selects tag from dropdown and adds to selected', async () => {
      const handleChange = vi.fn();
      render(<TagInput availableTags={mockTags} selectedTags={[]} onChange={handleChange} onCreate={vi.fn()} />);
      const input = screen.getByRole('textbox');
      await act(async () => {
        fireEvent.change(input, { target: { value: 'research' } });
      });
      const researchOption = screen.getByText('research');
      await act(async () => {
        fireEvent.click(researchOption);
      });
      expect(handleChange).toHaveBeenCalledWith([3]);
    });

  it('displays selected tags as pills', () => {
    render(<TagInput availableTags={mockTags} selectedTags={[1, 2]} onChange={vi.fn()} onCreate={vi.fn()} />);
    expect(screen.getByText('interviews')).toBeInTheDocument();
    expect(screen.getByText('marketing')).toBeInTheDocument();
  });

  it('removes tag when X clicked on pill', async () => {
    const handleChange = vi.fn();
    render(<TagInput availableTags={mockTags} selectedTags={[1, 2]} onChange={handleChange} onCreate={vi.fn()} />);
    const removeButtons = screen.getAllByRole('button', { name: /remove/i });
    await userEvent.click(removeButtons[0]);
    expect(handleChange).toHaveBeenCalledWith([2]);
  });

  it('shows create option when no matching tags', async () => {
    render(<TagInput availableTags={mockTags} selectedTags={[]} onChange={vi.fn()} onCreate={vi.fn()} />);
    const input = screen.getByRole('textbox');
    await userEvent.type(input, 'newtagname');
    expect(screen.getByText(/create new tag:/i)).toBeInTheDocument();
  });

  it('calls onCreate when create option selected', async () => {
      const handleCreate = vi.fn().mockResolvedValue({ id: 4, name: 'newtagname', color: '#000000' });
      render(<TagInput availableTags={mockTags} selectedTags={[]} onChange={vi.fn()} onCreate={handleCreate} />);
      const input = screen.getByRole('textbox');
      await act(async () => {
        fireEvent.change(input, { target: { value: 'newtagname' } });
      });
      const createOption = screen.getByText(/create new tag:/i);
      await act(async () => {
        fireEvent.click(createOption);
      });
      expect(handleCreate).toHaveBeenCalledWith('newtagname');
    });

  it('calls onCreate and adds new tag when Enter pressed with no match', async () => {
    const handleCreate = vi.fn().mockResolvedValue({ id: 4, name: 'urgent', color: '#FF0000' });
    const handleChange = vi.fn();
    render(<TagInput availableTags={mockTags} selectedTags={[]} onChange={handleChange} onCreate={handleCreate} />);
    const input = screen.getByRole('textbox');
    await userEvent.type(input, 'urgent{enter}');
    expect(handleCreate).toHaveBeenCalledWith('urgent');
  });

  it('does not show already selected tags in dropdown', async () => {
    render(<TagInput availableTags={mockTags} selectedTags={[1]} onChange={vi.fn()} onCreate={vi.fn()} />);
    const input = screen.getByRole('textbox');
    await userEvent.type(input, 'i');
    const dropdown = screen.getByTestId('tag-dropdown');
    expect(within(dropdown).queryByText('interviews')).not.toBeInTheDocument();
  });

  it('clears input after selecting tag', async () => {
      render(<TagInput availableTags={mockTags} selectedTags={[]} onChange={vi.fn()} onCreate={vi.fn()} />);
      const input = screen.getByRole('textbox') as HTMLInputElement;
      await act(async () => {
        fireEvent.change(input, { target: { value: 'research' } });
      });
      await act(async () => {
        fireEvent.click(screen.getByText('research'));
      });
      expect(input.value).toBe('');
    });
});
