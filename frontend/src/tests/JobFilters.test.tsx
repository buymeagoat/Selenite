import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { JobFilters } from '../components/jobs/JobFilters';

const tags = [
  { id: 1, name: 'interviews', color: '#0F3D2E' },
  { id: 2, name: 'marketing', color: '#B5543A' },
  { id: 3, name: 'research', color: '#C9A227' }
];

describe('JobFilters', () => {
  it('renders filter buttons', () => {
    render(<JobFilters currentFilters={{}} availableTags={tags} onFilterChange={vi.fn()} onReset={vi.fn()} />);
    expect(screen.getByRole('button', { name: /status/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /date/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /tags/i })).toBeInTheDocument();
  });

  it('opens status dropdown and shows options', () => {
    render(<JobFilters currentFilters={{}} availableTags={tags} onFilterChange={vi.fn()} onReset={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /status/i }));
    expect(screen.getByText('All')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
  });

  it('selecting a status calls onFilterChange', () => {
    const handleChange = vi.fn();
    render(<JobFilters currentFilters={{}} availableTags={tags} onFilterChange={handleChange} onReset={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /status/i }));
    fireEvent.click(screen.getByText('Completed'));
    expect(handleChange).toHaveBeenCalledWith({ status: 'completed' });
  });

  it('opens date range dropdown and shows options', () => {
    render(<JobFilters currentFilters={{}} availableTags={tags} onFilterChange={vi.fn()} onReset={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /date/i }));
    expect(screen.getByText('All Time')).toBeInTheDocument();
    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getByText('This Week')).toBeInTheDocument();
    expect(screen.getByText('This Month')).toBeInTheDocument();
    expect(screen.getByText('Custom Range')).toBeInTheDocument();
  });

  it('selecting a date range calls onFilterChange', () => {
    const handleChange = vi.fn();
    render(<JobFilters currentFilters={{}} availableTags={tags} onFilterChange={handleChange} onReset={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /date/i }));
    fireEvent.click(screen.getByText('Today'));
    expect(handleChange).toHaveBeenCalledWith({ dateRange: 'today' });
  });

  it('opens tags dropdown and shows tag checkboxes', () => {
    render(<JobFilters currentFilters={{}} availableTags={tags} onFilterChange={vi.fn()} onReset={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /tags/i }));
    tags.forEach(tag => {
      expect(screen.getByLabelText(tag.name)).toBeInTheDocument();
    });
  });

  it('selecting multiple tags updates filters and shows pills', () => {
    const handleChange = vi.fn();
    render(<JobFilters currentFilters={{}} availableTags={tags} onFilterChange={handleChange} onReset={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /tags/i }));
    fireEvent.click(screen.getByLabelText('interviews'));
    fireEvent.click(screen.getByLabelText('marketing'));
    // Called twice with incremental selections
    expect(handleChange).toHaveBeenNthCalledWith(1, { tags: [1] });
    expect(handleChange).toHaveBeenNthCalledWith(2, { tags: [1, 2] });
  });

  it('clear all button clears selected tags', () => {
    const handleChange = vi.fn();
    render(<JobFilters currentFilters={{ tags: [1,2] }} availableTags={tags} onFilterChange={handleChange} onReset={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /tags/i }));
    const clearAll = screen.getByRole('button', { name: /clear all/i });
    fireEvent.click(clearAll);
    expect(handleChange).toHaveBeenCalledWith({ tags: [] });
  });

  it('reset button appears only when filters applied', () => {
    const { rerender } = render(<JobFilters currentFilters={{}} availableTags={tags} onFilterChange={vi.fn()} onReset={vi.fn()} />);
    expect(screen.queryByRole('button', { name: /reset filters/i })).not.toBeInTheDocument();
    rerender(<JobFilters currentFilters={{ status: 'completed' }} availableTags={tags} onFilterChange={vi.fn()} onReset={vi.fn()} />);
    expect(screen.getByRole('button', { name: /reset filters/i })).toBeInTheDocument();
  });

  it('clicking reset clears all filters and calls onReset', () => {
    const handleReset = vi.fn();
    render(<JobFilters currentFilters={{ status: 'completed', dateRange: 'today', tags: [1] }} availableTags={tags} onFilterChange={vi.fn()} onReset={handleReset} />);
    const resetBtn = screen.getByRole('button', { name: /reset filters/i });
    fireEvent.click(resetBtn);
    expect(handleReset).toHaveBeenCalledTimes(1);
  });
});
