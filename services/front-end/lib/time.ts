import { format } from 'date-fns';

export const GMT7_OFFSET = 7 * 60; // minutes

export function formatToGMT7(dateString: string | null): string {
  if (!dateString) return 'N/A';
  
  try {
    const date = new Date(dateString);
    return format(date, 'yyyy-MM-dd HH:mm:ss XXX');
  } catch (error) {
    return 'Invalid date';
  }
}

export function formatGMT7Time(dateString: string | null): string {
  if (!dateString) return 'N/A';
  
  try {
    const date = new Date(dateString);
    return format(date, 'HH:mm:ss');
  } catch (error) {
    return 'Invalid time';
  }
}