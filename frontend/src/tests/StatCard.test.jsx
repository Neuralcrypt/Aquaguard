import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatCard from '../components/StatCard';

describe('StatCard', () => {
  it('shows label, value, unit and note', () => {
    render(<StatCard label="Today's consumption" value="120" unit="L" note="Today" />);
    expect(screen.getByText("Today's consumption")).toBeInTheDocument();
    expect(screen.getByText('120')).toBeInTheDocument();
    expect(screen.getByText('L')).toBeInTheDocument();
    expect(screen.getByText('Today')).toBeInTheDocument();
  });
});
