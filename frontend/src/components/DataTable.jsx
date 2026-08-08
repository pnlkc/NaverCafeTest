import React from 'react';

/**
 * 글래스패널 데이터 테이블 공통 컴포넌트
 * @param {{
 *   columns: Array<{ key: string, label: string }>,
 *   data: Array,
 *   emptyMessage: string,
 *   renderRow: function(item, index): React.ReactNode
 * }} props
 */
function DataTable({ columns, data, emptyMessage, renderRow }) {
  return (
    <div className="glass-panel p-6">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400 text-xs uppercase">
              {columns.map(col => (
                <th key={col.key} className="pb-3 font-semibold">{col.label}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="py-8 text-center text-slate-500">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((item, idx) => renderRow(item, idx))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default DataTable;
