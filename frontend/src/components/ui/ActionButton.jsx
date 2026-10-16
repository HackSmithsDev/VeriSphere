import { forwardRef } from 'react'

const ActionButton = forwardRef(function ActionButton(
  { className = '', variant = 'primary', type = 'button', ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={`button button-${variant} ${className}`.trim()}
      {...props}
    />
  )
})

export { ActionButton }
