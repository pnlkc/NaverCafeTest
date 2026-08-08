import React from 'react';

/**
 * 대시보드 메트릭 카드 공통 컴포넌트
 * @param {{
 *   title: string,
 *   value: number,
 *   unit: string,
 *   icon: React.ElementType,
 *   colorScheme: { hover: string, text: string, iconBg: string, iconText: string, iconBorder: string, intervalText: string },
 *   intervalLabel: string,
 *   schedulerBadge: React.ReactNode,
 *   onClick: function
 * }} props
 */
function MetricCard({ title, value, unit, icon: Icon, colorScheme, intervalLabel, schedulerBadge, onClick }) {
  return (
    <div
      onClick={onClick}
      className={`card-metric cursor-pointer ${colorScheme.hover} transition-all hover:scale-[1.02] group`}
      title={`클릭 시 상세 페이지로 이동합니다.`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className={`text-xs font-semibold text-slate-400 ${colorScheme.text} transition-colors`}>
          {title}
        </span>
        <div className={`p-2 rounded-xl ${colorScheme.iconBg} ${colorScheme.iconText} border ${colorScheme.iconBorder} ${colorScheme.iconBgHover || ''} transition-all`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="text-3xl font-extrabold text-white mb-1">
        {value}<span className="text-sm font-normal text-slate-400 ml-1">{unit}</span>
      </div>
      <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-800/80 text-[11px]">
        <span className={`${colorScheme.intervalText} font-medium`}>{intervalLabel}</span>
        {schedulerBadge}
      </div>
    </div>
  );
}

export default MetricCard;
