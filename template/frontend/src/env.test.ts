import { describe, expect, it } from 'vitest';

import { parseEnv } from './env';

describe('parseEnv', () => {
  it('defaults VITE_API_BASE_URL to empty string', () => {
    expect(parseEnv({})).toEqual({ VITE_API_BASE_URL: '' });
  });

  it('accepts a valid url', () => {
    expect(parseEnv({ VITE_API_BASE_URL: 'https://x.test' })).toEqual({
      VITE_API_BASE_URL: 'https://x.test',
    });
  });

  it('rejects a non-url', () => {
    expect(() => parseEnv({ VITE_API_BASE_URL: 'not a url' })).toThrow();
  });
});
