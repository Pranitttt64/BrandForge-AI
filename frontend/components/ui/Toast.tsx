"use client";

import { useState, useCallback, useEffect, createContext, useContext } from "react";

type ToastType = "success" | "error" | "info";

type Toast = {
  id: number;
  message: string;
  type: ToastType;
};

type ToastContextType = {
  showToast: (message: string, type?: ToastType) => void;
};

const ToastContext = createContext<ToastContextType>({ showToast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  let counter = 0;

  const showToast = useCallback((message: string, type: ToastType = "info") => {
    const id = Date.now() + (counter++);
    setToasts(prev => [...prev, { id, message, type }]);
  }, []);

  const removeToast = useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 pointer-events-none">
        {toasts.map(toast => (
          <ToastItem key={toast.id} toast={toast} onDismiss={removeToast} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: number) => void }) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), 3000);
    return () => clearTimeout(timer);
  }, [toast.id, onDismiss]);

  const colors = {
    success: "border-emerald-500/30 text-emerald-400",
    error: "border-red-500/30 text-red-400",
    info: "border-amber-500/30 text-amber-400",
  };

  const icons = {
    success: "✓",
    error: "✕",
    info: "i",
  };

  return (
    <div
      className={`pointer-events-auto flex items-center gap-3 bg-[#111] border ${colors[toast.type]} rounded-xl px-4 py-3 font-mono text-sm shadow-lg animate-slide-up min-w-[280px]`}
    >
      <span className="w-6 h-6 rounded-full bg-current/10 flex items-center justify-center text-xs font-bold">
        {icons[toast.type]}
      </span>
      <span className="text-gray-300">{toast.message}</span>
    </div>
  );
}
