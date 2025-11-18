'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';

interface AlertDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
}

const AlertDialogContext = React.createContext<{
  onOpenChange: (open: boolean) => void;
} | null>(null);

export function AlertDialog({ open, onOpenChange, children }: AlertDialogProps) {
  if (!open) return null;

  return (
    <AlertDialogContext.Provider value={{ onOpenChange }}>
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        <div
          className="fixed inset-0 bg-black/50"
          onClick={() => onOpenChange(false)}
        />
        <div className="relative z-50">{children}</div>
      </div>
    </AlertDialogContext.Provider>
  );
}

export function AlertDialogContent({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-background rounded-lg shadow-lg p-6 max-w-md w-full mx-4">
      {children}
    </div>
  );
}

export function AlertDialogHeader({ children }: { children: React.ReactNode }) {
  return <div className="space-y-2 mb-4">{children}</div>;
}

export function AlertDialogTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-lg font-semibold">{children}</h2>;
}

export function AlertDialogDescription({
  children,
  asChild,
}: {
  children: React.ReactNode;
  asChild?: boolean;
}) {
  if (asChild) {
    return <>{children}</>;
  }
  return <p className="text-sm text-muted-foreground">{children}</p>;
}

export function AlertDialogFooter({ children }: { children: React.ReactNode }) {
  return <div className="flex justify-end gap-2 mt-6">{children}</div>;
}

export function AlertDialogCancel({
  children,
  disabled,
}: {
  children: React.ReactNode;
  disabled?: boolean;
}) {
  const context = React.useContext(AlertDialogContext);
  
  return (
    <Button 
      variant="outline" 
      disabled={disabled} 
      type="button"
      onClick={() => context?.onOpenChange(false)}
    >
      {children}
    </Button>
  );
}

export function AlertDialogAction({
  children,
  onClick,
  disabled,
  className,
}: {
  children: React.ReactNode;
  onClick?: (e: React.MouseEvent) => void;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <Button onClick={onClick} disabled={disabled} className={className} type="button">
      {children}
    </Button>
  );
}
