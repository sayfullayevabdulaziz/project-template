import { describe, expect, it } from 'vitest';

import { safeRedirect } from './redirect';

describe('safeRedirect', () => {
  it('keeps same-origin paths', () => {
    expect(safeRedirect('/items?x=1')).toBe('/items?x=1');
  });

  it.each(['//evil.com', 'https://evil.com', '/\\evil.com', '', undefined])('rejects %j', (v) => {
    expect(safeRedirect(v)).toBe('/');
  });
});
