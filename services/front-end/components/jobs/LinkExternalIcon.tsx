import React from 'react';
import { ExternalLink } from 'lucide-react';

interface LinkExternalIconProps {
  className?: string;
}

export function LinkExternalIcon({ className = '' }: LinkExternalIconProps) {
  return <ExternalLink className={`h-4 w-4 inline ${className}`} />;
}