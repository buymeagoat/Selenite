import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { SearchBar } from '../components/common/SearchBar';

// Use fake timers for debounce behavior tests

describe('SearchBar', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it('renders with placeholder text', () => {
    render(<SearchBar value="" onChange={vi.fn()} placeholder="Search jobs" />);
    const input = screen.getByPlaceholderText('Search jobs');
    expect(input).toBeInTheDocument();
  });

  it('shows search icon', () => {
    render(<SearchBar value="" onChange={vi.fn()} />);
    expect(screen.getByTestId('search-icon')).toBeInTheDocument();
  });

  it('does not show clear button when value empty', () => {
    render(<SearchBar value="" onChange={vi.fn()} />);
    expect(screen.queryByRole('button', { name: /clear/i })).not.toBeInTheDocument();
  });

  it('shows clear button when value provided', () => {
    render(<SearchBar value="hello" onChange={vi.fn()} />);
    expect(screen.getByRole('button', { name: /clear/i })).toBeInTheDocument();
  });

  it('calls onClear and onChange with empty string when clear clicked', () => {
    const handleChange = vi.fn();
    const handleClear = vi.fn();
    render(<SearchBar value="query" onChange={handleChange} onClear={handleClear} />);
    const clearBtn = screen.getByRole('button', { name: /clear/i });
    fireEvent.click(clearBtn);
    expect(handleClear).toHaveBeenCalledTimes(1);
    // Clear should invoke onChange synchronously with '' (no debounce)
    expect(handleChange).toHaveBeenCalledWith('');
  });

  it('debounces onChange calls by 300ms when typing', () => {
    const handleChange = vi.fn();
    render(<SearchBar value="" onChange={handleChange} />);
    const input = screen.getByRole('searchbox');

    fireEvent.change(input, { target: { value: 'h' } });
    fireEvent.change(input, { target: { value: 'he' } });
    fireEvent.change(input, { target: { value: 'hel' } });
    fireEvent.change(input, { target: { value: 'hell' } });
    fireEvent.change(input, { target: { value: 'hello' } });

    // No calls before timer advance
    expect(handleChange).not.toHaveBeenCalled();

    vi.advanceTimersByTime(299);
    expect(handleChange).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1);
    expect(handleChange).toHaveBeenCalledTimes(1);
    expect(handleChange).toHaveBeenCalledWith('hello');
  });

  it('shows loading spinner and hides clear button when isLoading is true', () => {
    render(<SearchBar value="data" onChange={vi.fn()} isLoading />);
    expect(screen.getByTestId('search-loading')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /clear/i })).not.toBeInTheDocument();
  });

  it('updates when external value prop changes', () => {
    const { rerender } = render(<SearchBar value="first" onChange={vi.fn()} />);
    expect((screen.getByRole('searchbox') as HTMLInputElement).value).toBe('first');
    rerender(<SearchBar value="second" onChange={vi.fn()} />);
    expect((screen.getByRole('searchbox') as HTMLInputElement).value).toBe('second');
  });

  it('calls onChange immediately on clear (no debounce) then debounces further typing', () => {
    const handleChange = vi.fn();
    render(<SearchBar value="abc" onChange={handleChange} />);
    const clearBtn = screen.getByRole('button', { name: /clear/i });
    fireEvent.click(clearBtn);
    expect(handleChange).toHaveBeenCalledWith('');

    const input = screen.getByRole('searchbox');
    fireEvent.change(input, { target: { value: 'x' } });
    vi.advanceTimersByTime(300);
    expect(handleChange).toHaveBeenCalledWith('x');
  });
});
