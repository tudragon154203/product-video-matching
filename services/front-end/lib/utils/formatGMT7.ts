import { format as formatDate } from 'date-fns';

/**
 * Format ISO date string to localized string in GMT+7 timezone
 */
export function formatGMT7(iso?: string): string {
  if (!iso) {
    return '';
  }
  
  try {
    // Parse the ISO date and add 7 hours to GMT+7
    const date = new Date(iso);
    const gmt7Time = new Date(date.getTime() + (7 * 60 * 60 * 1000));
    
    // Format as date and time
    return formatDate(gmt7Time, 'MMM dd, yyyy HH:mm');
  } catch (error) {
    console.error('Error formatting GMT+7 date:', error);
    return '';
  }
}