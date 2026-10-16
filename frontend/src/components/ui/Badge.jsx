const variants = {
  default: 'badge-default',
  success: 'badge-success',
  warning: 'badge-warning',
  info: 'badge-info',
  muted: 'badge-muted',
}

export function Badge({ variant = 'default', className = '', ...props }) {
  const variantClass = variants[variant] || variants.default
  return (
    <span className={`theme-badge ${variantClass} ${className}`.trim()} {...props} />
  )
}
