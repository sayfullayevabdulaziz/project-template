import { http, HttpResponse } from 'msw';

import { adminUser } from './fixtures';

export const apiUrl = (path: string) => `http://api.test/api/admin${path}`;

export const defaultHandlers = [
  http.post(apiUrl('/auth/login'), () =>
    HttpResponse.json({ access_token: 't-login', token_type: 'bearer', expires_in: 900 }),
  ),
  http.post(apiUrl('/auth/refresh'), () =>
    HttpResponse.json({ access_token: 't-refreshed', token_type: 'bearer', expires_in: 900 }),
  ),
  http.post(apiUrl('/auth/logout'), () => new HttpResponse(null, { status: 204 })),
  http.get(apiUrl('/users/me'), () => HttpResponse.json(adminUser)),
  http.get(apiUrl('/items'), () => HttpResponse.json({ items: [], total: 0 })),
  http.get(apiUrl('/users'), () => HttpResponse.json({ items: [], total: 0 })),
];
