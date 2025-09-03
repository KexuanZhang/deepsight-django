import { useState, useEffect } from "react"

const TOAST_LIMIT = 1

export interface ToastProps {
  id?: string;
  title?: string;
  description?: string;
  variant?: 'default' | 'destructive';
  duration?: number;
  action?: React.ReactNode;
  dismiss?: () => void;
  [key: string]: any;
}

interface ToastState {
  toasts: ToastProps[];
}

type ToastListener = (state: ToastState) => void;

let count = 0
function generateId(): string {
  count = (count + 1) % Number.MAX_VALUE
  return count.toString()
}

const toastStore = {
  state: {
    toasts: [],
  } as ToastState,
  listeners: [] as ToastListener[],
  
  getState: (): ToastState => toastStore.state,
  
  setState: (nextState: ToastState | ((prevState: ToastState) => ToastState)) => {
    if (typeof nextState === 'function') {
      toastStore.state = nextState(toastStore.state)
    } else {
      toastStore.state = { ...toastStore.state, ...nextState }
    }
    
    toastStore.listeners.forEach(listener => listener(toastStore.state))
  },
  
  subscribe: (listener: ToastListener) => {
    toastStore.listeners.push(listener)
    return () => {
      toastStore.listeners = toastStore.listeners.filter(l => l !== listener)
    }
  }
}

export const toast = ({ ...props }: ToastProps) => {
  const id = generateId()

  const update = (props: Partial<ToastProps>) =>
    toastStore.setState((state) => ({
      ...state,
      toasts: state.toasts.map((t) =>
        t.id === id ? { ...t, ...props } : t
      ),
    }))

  const dismiss = () => toastStore.setState((state) => ({
    ...state,
    toasts: state.toasts.filter((t) => t.id !== id),
  }))

  toastStore.setState((state) => ({
    ...state,
    toasts: [
      { ...props, id, dismiss },
      ...state.toasts,
    ].slice(0, TOAST_LIMIT),
  }))

  return {
    id,
    dismiss,
    update,
  }
}

export function useToast() {
  const [state, setState] = useState<ToastState>(toastStore.getState())
  
  useEffect(() => {
    const unsubscribe = toastStore.subscribe((state: ToastState) => {
      setState(state)
    })
    
    return unsubscribe
  }, [])
  
  useEffect(() => {
    const timeouts: ReturnType<typeof setTimeout>[] = []

    state.toasts.forEach((toastItem) => {
      if (toastItem.duration === Infinity) {
        return
      }

      const timeout = setTimeout(() => {
        toastItem.dismiss?.()
      }, toastItem.duration || 5000)

      timeouts.push(timeout)
    })

    return () => {
      timeouts.forEach((timeout) => clearTimeout(timeout))
    }
  }, [state.toasts])

  return {
    toast,
    toasts: state.toasts,
  }
}
