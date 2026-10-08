import { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

export default function Dialog({ title, children, onClose, busy = false, placement = 'center', dark = false, size = 'md' }) {
  const titleId = useId();
  const panel = useRef(null);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  useEffect(() => {
    const previous = document.activeElement;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    panel.current?.focus();
    const handleKey = (event) => {
      if (event.key === 'Escape' && !busy) closeRef.current();
      if (event.key !== 'Tab') return;
      const items = [...panel.current.querySelectorAll('button:not(:disabled), a[href], input:not(:disabled), textarea:not(:disabled), select:not(:disabled), [tabindex="0"]')];
      const first = items[0], last = items.at(-1);
      if (!first) { event.preventDefault(); return; }
      if (event.shiftKey && (document.activeElement === first || document.activeElement === panel.current)) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || document.activeElement === panel.current)) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', handleKey);
    return () => {
      document.body.style.overflow = overflow;
      document.removeEventListener('keydown', handleKey);
      if (previous instanceof HTMLElement) previous.focus();
    };
  }, [busy]);

  return createPortal(<div className={`fixed inset-0 z-50 flex bg-ink/45 backdrop-blur-xs ${placement === 'left' ? 'items-stretch justify-start' : 'items-center justify-center p-3 sm:p-6'}`} onMouseDown={(event) => { if (event.target === event.currentTarget && !busy) onClose(); }}><section ref={panel} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1} className={`flex flex-col shadow-2xl outline-none ${placement === 'left' ? 'h-full w-72' : `max-h-[calc(100dvh-1.5rem)] w-full rounded-2xl ${size === 'lg' ? 'max-w-3xl' : 'max-w-xl'}`} ${dark ? 'bg-ink text-white' : 'bg-white text-ink'}`}><div className={`flex items-center justify-between gap-3 border-b px-6 py-5 ${dark ? 'border-white/10' : 'border-slate-100'}`}><h2 id={titleId} className="text-lg font-semibold">{title}</h2><button type="button" className={`rounded-lg p-2 ${dark ? 'text-slate-400 hover:bg-white/10' : 'text-muted hover:bg-slate-100'}`} onClick={onClose} disabled={busy} aria-label="Cerrar ventana"><X size={20} /></button></div><div className="flex min-h-0 flex-1 flex-col overflow-y-auto">{children}</div></section></div>, document.body);
}
