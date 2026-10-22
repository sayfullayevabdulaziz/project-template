import { describe, expect, it } from 'vitest';

import { makeListSearchSchema, toQuery } from './search';

const schema = makeListSearchSchema(['name', 'created_at']);

describe('makeListSearchSchema', () => {
  it('falls back to limit 20 when out of range', () => {
    expect(schema.parse({ limit: '9999' }).limit).toBe(20);
  });

  it('accepts a valid limit and defaults the rest', () => {
    expect(schema.parse({ limit: 50 })).toMatchObject({ limit: 50, offset: 0 });
    expect(schema.parse({}).limit).toBe(20);
  });

  it('falls back to offset 0 when negative', () => {
    expect(schema.parse({ offset: -1 }).offset).toBe(0);
  });

  it('drops a sort key that is not allowed', () => {
    expect(schema.parse({ sort: 'bogus' }).sort).toBeUndefined();
    expect(schema.parse({ sort: '-bogus' }).sort).toBeUndefined();
  });

  it('keeps allowed ascending and descending sort', () => {
    expect(schema.parse({ sort: '-name' }).sort).toBe('-name');
    expect(schema.parse({ sort: 'name' }).sort).toBe('name');
  });

  it('keeps q verbatim', () => {
    expect(schema.parse({ q: '%' }).q).toBe('%');
  });
});

describe('toQuery', () => {
  it('defaults sort and omits empty q', () => {
    expect(toQuery({ limit: 20, offset: 0 })).toEqual({
      limit: 20,
      offset: 0,
      sort: '-created_at',
    });
    expect(toQuery({ limit: 20, offset: 0, q: '' })).toEqual({
      limit: 20,
      offset: 0,
      sort: '-created_at',
    });
  });

  it('passes sort and q through', () => {
    expect(toQuery({ limit: 10, offset: 20, sort: 'name', q: 'a' })).toEqual({
      limit: 10,
      offset: 20,
      sort: 'name',
      q: 'a',
    });
  });
});
