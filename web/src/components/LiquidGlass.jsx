export default function LiquidGlass({ children, className = '', as: Tag = 'div', ...props }) {
  return (
    <Tag className={`liquid-glass ${className}`} {...props}>
      {children}
    </Tag>
  );
}
