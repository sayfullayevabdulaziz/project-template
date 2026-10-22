import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ItemForm, type ItemFormValues } from './item-form';

function setup(over: { defaultValues?: ItemFormValues; onSubmit?: () => Promise<void> } = {}) {
  const onSubmit = vi.fn(over.onSubmit ?? (() => Promise.resolve()));
  render(<ItemForm submitLabel="Save" onSubmit={onSubmit} defaultValues={over.defaultValues} />);
  return { onSubmit, user: userEvent.setup() };
}

describe('ItemForm', () => {
  it('blocks an empty name', async () => {
    const { onSubmit, user } = setup();
    await user.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByText('Name is required')).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('blocks a 201-char name', async () => {
    const { onSubmit, user } = setup();
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'a'.repeat(201) } });
    await user.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByText(/at most 200/)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('blocks a 2001-char description', async () => {
    const { onSubmit, user } = setup();
    await user.type(screen.getByLabelText('Name'), 'Widget');
    fireEvent.change(screen.getByLabelText('Description'), { target: { value: 'a'.repeat(2001) } });
    await user.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByText(/at most 2000/)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('submits valid values', async () => {
    const { onSubmit, user } = setup();
    await user.type(screen.getByLabelText('Name'), 'Widget');
    await user.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledOnce());
    expect(onSubmit).toHaveBeenCalledWith({ name: 'Widget', description: '', is_published: false });
  });

  it('populates defaultValues', () => {
    setup({ defaultValues: { name: 'Gadget', description: 'Shiny', is_published: true } });
    expect(screen.getByLabelText('Name')).toHaveValue('Gadget');
    expect(screen.getByLabelText('Description')).toHaveValue('Shiny');
    expect(screen.getByLabelText('Published')).toBeChecked();
  });

  it('disables the button while submitting', async () => {
    let finish!: () => void;
    const { user } = setup({ onSubmit: () => new Promise<void>((r) => (finish = r)) });
    await user.type(screen.getByLabelText('Name'), 'Widget');
    await user.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled());
    finish();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Save' })).toBeEnabled());
  });
});
