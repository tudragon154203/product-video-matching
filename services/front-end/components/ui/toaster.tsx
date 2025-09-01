'use client'

import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from '@/components/ui/toast'
import { useToast } from '@/components/ui/use-toast'
import { useAutoAnimateList } from '@/lib/hooks/useAutoAnimateList'

export function Toaster() {
  const { toasts } = useToast()
  const { parentRef: toastListRef } = useAutoAnimateList<HTMLDivElement>()

  return (
    <ToastProvider>
      <div ref={toastListRef}>
        {toasts.map(function ({ id, title, description, action, ...props }) {
          return (
            <Toast key={id} {...props}>
              <div className="grid gap-1">
                {title && <ToastTitle>{title}</ToastTitle>}
                {description && (
                  <ToastDescription>{description}</ToastDescription>
                )}
              </div>
              {action}
              <ToastClose />
            </Toast>
          )
        })}
      </div>
      <ToastViewport />
    </ToastProvider>
  )
}
