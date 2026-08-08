import React from 'react';
import { getFriendlyCategory, getFriendlyStatus } from '../utils';

/**
 * 로그/이력 아이템 행 컴포넌트
 * @param {{ actionType: string, message: string, status: string, timestamp: string, showFullTimestamp?: boolean }} props
 */
function LogItem({ actionType, message, status, timestamp, showFullTimestamp = false }) {
  const cat = getFriendlyCategory(actionType);
  const st = getFriendlyStatus(status);
  // 대시보드 간략 모드에서는 시:분:초만, 전체 로그 페이지에서는 풀 타임스탬프
  const displayTime = showFullTimestamp ? timestamp : (timestamp?.split(' ')[1] || '');

  return (
    <div className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800/80 flex items-center justify-between text-xs hover:border-slate-700 transition-all">
      <div className="flex items-center gap-3">
        <span className={`px-2.5 py-1 rounded-lg text-xs font-semibold shrink-0 ${cat.color}`}>
          {cat.label}
        </span>
        <span className="text-slate-200 font-medium">{message}</span>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <span className={`badge ${st.badge}`}>{st.label}</span>
        <span className={`text-slate-500 ${showFullTimestamp ? 'font-mono' : ''}`}>{displayTime}</span>
      </div>
    </div>
  );
}

export default LogItem;
