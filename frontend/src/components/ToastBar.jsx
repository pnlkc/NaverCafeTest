import React from 'react';
import { CheckCircle, AlertTriangle } from 'lucide-react';

/**
 * 상단 알림/액션 결과 토스트 바
 * @param {{ status: { type: 'success'|'error', message: string } | null }} props
 */
function ToastBar({ status }) {
  if (!status) return null;

  const isSuccess = status.type === 'success';

  return (
    <div className={`px-6 py-3 border-b flex items-center gap-3 text-sm font-medium transition-all ${
      isSuccess
        ? 'bg-emerald-950/80 border-emerald-800/60 text-emerald-200'
        : 'bg-rose-950/80 border-rose-800/60 text-rose-200'
    }`}>
      {isSuccess
        ? <CheckCircle className="w-4 h-4 text-emerald-400" />
        : <AlertTriangle className="w-4 h-4 text-rose-400" />
      }
      <span>{status.message}</span>
    </div>
  );
}

export default ToastBar;
