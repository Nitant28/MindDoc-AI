import { forwardRef, useId, useImperativeHandle, useLayoutEffect, useRef, type KeyboardEvent, type ReactNode } from 'react';
import { Button } from '../ui/Button';

interface ComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onStop: () => void;
  streaming: boolean;
  placeholder?: string;
  footer?: ReactNode;
}

const Composer = forwardRef<HTMLTextAreaElement | null, ComposerProps>(function Composer(
  { value, onChange, onSubmit, onStop, streaming, placeholder = 'Ask a question about your documents…', footer },
  ref,
) {
  const inner = useRef<HTMLTextAreaElement>(null);
  const id = useId();
  useImperativeHandle(ref, () => inner.current as HTMLTextAreaElement);

  useLayoutEffect(() => {
    const el = inner.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      if (!streaming && value.trim()) onSubmit();
    }
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (!streaming && value.trim()) onSubmit();
      }}
    >
      <div className="flex items-end gap-2 rounded-xl border border-line bg-surface p-2 shadow-sm transition-colors focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/20">
        <label htmlFor={id} className="sr-only">
          Message
        </label>
        <textarea
          id={id}
          ref={inner}
          rows={1}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          className="max-h-[200px] min-h-[2.25rem] flex-1 resize-none bg-transparent px-2 py-1.5 text-sm leading-relaxed text-fg placeholder:text-subtle focus:outline-none"
        />
        {streaming ? (
          <Button variant="secondary" size="icon" onClick={onStop} aria-label="Stop generating" title="Stop" icon="stop" />
        ) : (
          <Button type="submit" variant="primary" size="icon" disabled={!value.trim()} aria-label="Send message" title="Send (Enter)" icon="send" />
        )}
      </div>
      <div className="mt-1.5 flex flex-wrap items-center justify-between gap-2 px-1 text-[11px] text-subtle">
        <div className="min-w-0">{footer}</div>
        <span className="hidden sm:inline">
          <kbd>Enter</kbd> to send · <kbd>Shift</kbd>+<kbd>Enter</kbd> for a new line
        </span>
      </div>
    </form>
  );
});

export default Composer;
