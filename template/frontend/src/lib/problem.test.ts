import { toast } from 'sonner';
import { describe, expect, it, vi } from 'vitest';

import { problem } from '@/test/fixtures';

import { getProblem, showProblem } from './problem';

describe('getProblem', () => {
  it('reads title, detail and status from a problem+json body', () => {
    expect(getProblem(problem(404, 'Not found', 'No such item'))).toEqual({
      title: 'Not found',
      detail: 'No such item',
      status: 404,
    });
  });

  it('turns a FastAPI 422 body into a validation error', () => {
    expect(getProblem({ detail: [{ msg: 'x' }] })).toEqual({
      title: 'Validation error',
      detail: 'x',
    });
  });

  it.each([['<html>502 Bad Gateway</html>'], [undefined], [null], [{}]])(
    'falls back to a generic title for %j',
    (err) => {
      expect(getProblem(err)).toEqual({ title: 'Unexpected error' });
    },
  );
});

describe('showProblem', () => {
  it('toasts the problem title with its detail', () => {
    const error = vi.spyOn(toast, 'error');
    showProblem(problem(409, 'Conflict', 'Name taken'));
    expect(error).toHaveBeenCalledWith('Conflict', { description: 'Name taken' });
    error.mockRestore();
  });
});
