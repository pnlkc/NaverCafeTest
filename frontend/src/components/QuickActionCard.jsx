import React from 'react';
import { ArrowRight } from 'lucide-react';

/**
 * 수동 실행 퀵 액션 카드 컴포넌트
 * @param {{ title: string, description: string, colorScheme: string, onClick: function, disabled: boolean }} props
 */
function QuickActionCard({ title, description, colorScheme = 'indigo', onClick, disabled = false }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`p-4 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-${colorScheme}-500/50 transition-all text-left group`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className={`font-semibold text-sm text-slate-200 group-hover:text-${colorScheme}-400 transition-colors`}>
          {title}
        </span>
        <ArrowRight className={`w-4 h-4 text-slate-500 group-hover:text-${colorScheme}-400 transition-colors`} />
      </div>
      <p className="text-xs text-slate-400">{description}</p>
    </button>
  );
}

export default QuickActionCard;
