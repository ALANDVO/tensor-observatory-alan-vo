import { Loader2 } from 'lucide-react';

interface LoadingProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function Loading({ size = 'md', className = '' }: LoadingProps) {
  const sizeMap = { sm: 16, md: 24, lg: 32 };
  return (
    <div className={`flex items-center justify-center ${className}`}>
      <Loader2 className={`h-${sizeMap[size]} w-${sizeMap[size]} animate-spin text-primary-600`} />
    </div>
  );
}

export function LoadingFullScreen() {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/80 backdrop-blur-sm">
      <Loading size="lg" />
    </div>
  );
}