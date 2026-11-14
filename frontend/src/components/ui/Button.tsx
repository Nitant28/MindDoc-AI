import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { Link, type LinkProps } from 'react-router-dom';
import { cx } from '../../lib/cx';
import { Icon, type IconName } from './Icon';
import { Spinner } from './Spinner';

export type ButtonVariant = 'primary' | 'secondary' | 'tonal' | 'ghost' | 'danger' | 'danger-ghost';
export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg' | 'icon' | 'icon-sm';

const BASE =
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full font-medium tracking-[0.01em] transition-[background-color,border-color,color,box-shadow] duration-150 select-none active:scale-[0.98] disabled:pointer-events-none disabled:opacity-40';

const VARIANTS: Record<ButtonVariant, string> = {
  primary: 'bg-accent text-accent-fg hover:bg-accent-hover hover:elevation-1',
  secondary: 'border border-line-strong bg-transparent text-accent-soft hover:bg-accent/[0.08] hover:border-line-strong',
  tonal: 'bg-accent-container text-accent-on-container hover:elevation-1',
  ghost: 'text-muted hover:bg-fg/[0.06] hover:text-fg',
  danger: 'bg-rose-600 text-white hover:bg-rose-500 hover:elevation-1',
  'danger-ghost': 'text-rose-600 hover:bg-rose-500/10 dark:text-rose-400',
};

const SIZES: Record<ButtonSize, string> = {
  xs: 'h-7 px-3 text-xs',
  sm: 'h-8 px-3.5 text-[13px]',
  md: 'h-10 px-5 text-sm',
  lg: 'h-12 px-6 text-[15px]',
  icon: 'h-10 w-10',
  'icon-sm': 'h-8 w-8',
};

const ICON_SIZE: Record<ButtonSize, string> = {
  xs: 'h-3.5 w-3.5',
  sm: 'h-4 w-4',
  md: 'h-4 w-4',
  lg: 'h-4 w-4',
  icon: 'h-[18px] w-[18px]',
  'icon-sm': 'h-3.5 w-3.5',
};

export function buttonClass(variant: ButtonVariant = 'secondary', size: ButtonSize = 'md', extra?: string): string {
  return cx(BASE, VARIANTS[variant], SIZES[size], extra);
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: IconName;
  iconRight?: IconName;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'secondary', size = 'md', loading = false, icon, iconRight, className, children, disabled, type = 'button', ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={buttonClass(variant, size, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <Spinner size={size === 'xs' || size === 'icon-sm' ? 'xs' : 'sm'} /> : icon ? <Icon name={icon} className={ICON_SIZE[size]} /> : null}
      {children}
      {iconRight ? <Icon name={iconRight} className={ICON_SIZE[size]} /> : null}
    </button>
  );
});

export interface LinkButtonProps extends LinkProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: IconName;
  children?: ReactNode;
}

export function LinkButton({ variant = 'secondary', size = 'md', icon, className, children, ...rest }: LinkButtonProps) {
  return (
    <Link className={buttonClass(variant, size, typeof className === 'string' ? className : undefined)} {...rest}>
      {icon ? <Icon name={icon} className={ICON_SIZE[size]} /> : null}
      {children}
    </Link>
  );
}

export default Button;
