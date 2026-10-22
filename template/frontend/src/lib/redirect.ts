/** Only same-origin absolute paths pass: rejects `//host`, `/\host` and full URLs (open redirect). */
export function safeRedirect(value: string | undefined): string {
  return value && /^\/(?![/\\])/.test(value) ? value : '/';
}
