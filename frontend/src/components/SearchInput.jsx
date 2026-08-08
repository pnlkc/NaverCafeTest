import React from 'react';
import { Search } from 'lucide-react';

/**
 * 검색 입력 필드 공통 컴포넌트
 * @param {{ placeholder: string, value: string, onChange: function, focusColor?: string }} props
 */
function SearchInput({ placeholder, value, onChange, focusColor = 'focus:border-indigo-500' }) {
  return (
    <div className="relative w-full md:w-64">
      <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
      <input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        className={`w-full pl-9 pr-4 py-2 bg-slate-900/80 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none ${focusColor} transition-colors`}
      />
    </div>
  );
}

export default SearchInput;
