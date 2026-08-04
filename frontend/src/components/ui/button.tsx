import type { ButtonHTMLAttributes, ReactNode } from 'react';

type ButtonVariant = 'default' | 'ghost' | 'outline';
type ButtonSize = 'default' | 'sm' | 'icon';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  children: ReactNode;
}

const variantStyles: Record<ButtonVariant, Record<string, string>> = {
  default: {
    background: 'var(--accent)',
    color: '#fff',
    border: '1px solid var(--accent)',
  },
  ghost: {
    background: 'transparent',
    color: 'var(--text-primary)',
    border: '1px solid transparent',
  },
  outline: {
    background: 'transparent',
    color: 'var(--text-primary)',
    border: '1px solid var(--border)',
  },
};

const sizeStyles: Record<ButtonSize, Record<string, string | number>> = {
  default: { height: 32, padding: '0 12px', fontSize: 12 },
  sm: { height: 24, padding: '0 8px', fontSize: 11 },
  icon: { height: 28, width: 28, padding: 0, fontSize: 12 },
};

export function Button({
  variant = 'default',
  size = 'default',
  children,
  style,
  ...props
}: ButtonProps) {
  const v = variantStyles[variant];
  const s = sizeStyles[size];

  return (
    <button
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 4,
        borderRadius: 4,
        cursor: 'pointer',
        border: v.border,
        background: v.background,
        color: v.color,
        ...s,
        ...style,
      }}
      {...props}
    >
      {children}
    </button>
  );
}
