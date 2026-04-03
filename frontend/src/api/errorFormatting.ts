/** Normalizes FastAPI ``detail`` (string or validation array) for display. */

export function formatErrorDetail(detail: unknown): string {
  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === 'object' && 'msg' in item && typeof (item as { msg: string }).msg === 'string') {
          return (item as { msg: string }).msg;
        }
        return JSON.stringify(item);
      })
      .join(' ');
  }
  return JSON.stringify(detail);
}
