import React from 'react';

/**
 * 필터 칩(토글 버튼) 그룹 공통 컴포넌트
 * @param {{
 *   chips: Array<{ key: string, label: string, count?: number, activeColor?: string, countBg?: string, countText?: string }>,
 *   activeKey: string,
 *   onSelect: function,
 *   allowToggleOff?: boolean,
 *   defaultKey?: string
 * }} props
 */
function FilterChipGroup({ chips, activeKey, onSelect, allowToggleOff = true, defaultKey = 'ALL' }) {
  const handleClick = (key) => {
    if (allowToggleOff && activeKey === key) {
      onSelect(defaultKey);
    } else {
      onSelect(key);
    }
  };

  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
      {chips.map(chip => {
        const isSelected = activeKey === chip.key;
        const activeColorClass = chip.activeColor || 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/30';
        const hasCount = chip.count !== undefined && chip.count !== null;

        return (
          <button
            key={chip.key}
            onClick={() => handleClick(chip.key)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-1.5 shrink-0 ${
              isSelected
                ? `${activeColorClass} shadow-lg ring-1 ring-white/20`
                : 'bg-slate-900/80 text-slate-400 hover:text-slate-200 border border-slate-800 hover:border-slate-700'
            }`}
          >
            <span>{chip.label}</span>
            {hasCount && (
              <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${
                isSelected
                  ? `${chip.countBg || 'bg-indigo-900/80'} ${chip.countText || 'text-indigo-200'}`
                  : 'bg-slate-800 text-slate-300'
              }`}>
                {chip.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

export default FilterChipGroup;

