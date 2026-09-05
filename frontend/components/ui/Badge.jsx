export default function Badge({ children, variant = 'blue', className = '' }) {
  const variants = {
    blue: 'bg-blue-50 text-blue-600 border border-blue-200',
    green: 'bg-green-50 text-green-600 border border-green-200',
    red: 'bg-red-50 text-red-500 border border-red-200',
    orange: 'bg-orange-50 text-orange-500 border border-orange-200',
    navy: 'bg-[#0b1f3a] text-white',
  };

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 px-3 py-1
        text-[10.5px] font-semibold tracking-widest uppercase rounded-full
        ${variants[variant] ?? variants.blue}
        ${className}
      `}
    >
      {children}
    </span>
  );
}
