"use client";

import { useEffect, useRef, useMemo } from 'react';
import autoAnimate from '@formkit/auto-animate';

interface UseAutoAnimateListOptions {
  duration?: number;
  easing?: string;
  disrespectUserMotionPreference?: boolean;
}

export function useAutoAnimateList<T extends HTMLElement>(
  options: UseAutoAnimateListOptions = {}
) {
  const parentRef = useRef<T>(null);
  // Animations are enabled by default
  const isEnabled = useMemo(() => true, []);

  useEffect(() => {
    if (!parentRef.current || !isEnabled) return;

    const controller = autoAnimate(parentRef.current, {
      duration: options.duration ?? 250,
      easing: options.easing ?? 'ease-in-out',
      disrespectUserMotionPreference: options.disrespectUserMotionPreference ?? false,
    });

    return () => {
      try {
        controller?.destroy?.();
      } catch (_) {
        // no-op cleanup guard
      }
    };
  }, [isEnabled, options.duration, options.easing, options.disrespectUserMotionPreference]);

  return {
    parentRef,
    isEnabled,
  };
}

// Hook for animating individual list items
export function useAutoAnimateItem<T extends HTMLElement>(
  options: UseAutoAnimateListOptions = {}
) {
  const itemRef = useRef<T>(null);
  // Animations are enabled by default
  const isEnabled = useMemo(() => true, []);

  useEffect(() => {
    if (!itemRef.current || !isEnabled) return;

    const controller = autoAnimate(itemRef.current, {
      duration: options.duration ?? 200,
      easing: options.easing ?? 'ease-out',
      disrespectUserMotionPreference: options.disrespectUserMotionPreference ?? false,
    });

    return () => {
      try {
        controller?.destroy?.();
      } catch (_) {
        // no-op cleanup guard
      }
    };
  }, [isEnabled, options.duration, options.easing, options.disrespectUserMotionPreference]);

  return {
    itemRef,
    isEnabled,
  };
}
