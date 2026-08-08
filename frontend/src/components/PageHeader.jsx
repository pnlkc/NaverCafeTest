import React from 'react';

/**
 * 페이지 상단 헤더 공통 컴포넌트 (타이틀 + 설명 + 우측 액션 슬롯)
 * @param {{ title: string, description: string, children?: React.ReactNode }} props
 */
function PageHeader({ title, description, children }) {
  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h2 className="text-2xl font-bold text-white">{title}</h2>
        <p className="text-slate-400 text-sm mt-1">{description}</p>
      </div>
      {children}
    </div>
  );
}

export default PageHeader;
