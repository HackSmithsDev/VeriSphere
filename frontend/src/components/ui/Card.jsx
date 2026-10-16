export function Card({ as: Component = 'section', className = '', ...props }) {
  return <Component className={`panel ${className}`.trim()} {...props} />
}
