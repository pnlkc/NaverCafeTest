import React from 'react';

/**
 * 사이드바 내비게이션 버튼 공통 컴포넌트
 * @param {{
 *   icon: React.ElementType,
 *   label: string,
 *   isActive: boolean,
 *   isCollapsed: boolean,
 *   onClick: function,
 *   badge?: { value: number, bgColor: string, textColor: string, borderColor: string },
 *   badgeDotColor?: string
 * }} props
 */
function SidebarNavButton({ icon: Icon, label, isActive, isCollapsed, onClick, badge, badgeDotColor }) {
  return (
    <button
      onClick={onClick}
      title={isCollapsed ? (badge ? `${label} (${badge.value})` : label) : undefined}
      className={`w-full flex items-center relative ${isCollapsed ? 'justify-center py-3' : 'gap-3 px-4 py-3'} rounded-xl font-medium text-sm transition-all duration-200 ${
        isActive
          ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30 font-semibold'
          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
      }`}
    >
      <Icon className="w-4 h-4 shrink-0" />
      {!isCollapsed && (
        <>
          <span className="whitespace-nowrap shrink-0">{label}</span>
          {badge && badge.value > 0 && (
            <span className={`ml-auto px-2 py-0.5 text-xs ${badge.bgColor} ${badge.textColor} rounded-full border ${badge.borderColor} font-bold shrink-0`}>
              {badge.value}
            </span>
          )}
        </>
      )}
      {isCollapsed && badge && badge.value > 0 && badgeDotColor && (
        <span className={`absolute top-2 right-2 w-2 h-2 ${badgeDotColor} rounded-full animate-pulse`}></span>
      )}
    </button>
  );
}

export default SidebarNavButton;
