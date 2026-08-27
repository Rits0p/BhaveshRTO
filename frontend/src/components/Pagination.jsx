import React from 'react';

export default function Pagination({ currentPage, totalItems, pageSize, onPageChange }) {
    const totalPages = Math.ceil(totalItems / pageSize);

    if (totalPages <= 1) return null;

    const getVisiblePages = () => {
        let start = Math.max(1, currentPage - 2);
        let end = Math.min(totalPages, currentPage + 2);

        if (currentPage <= 3) {
            end = Math.min(totalPages, 5);
        } else if (currentPage >= totalPages - 2) {
            start = Math.max(1, totalPages - 4);
        }

        return Array.from({ length: end - start + 1 }, (_, i) => start + i);
    };

    const visiblePages = getVisiblePages();

    return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderTop: '1px solid #e2e8f0', flexWrap: 'wrap', gap: 12 }}>
            <span style={{ fontSize: 13, color: '#64748b' }}>
                Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, totalItems)} of {totalItems} entries
            </span>
            <div style={{ display: 'flex', gap: 6 }}>
                <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    disabled={currentPage === 1}
                    onClick={() => onPageChange(currentPage - 1)}
                >
                    Previous
                </button>

                {visiblePages[0] > 1 && (
                    <>
                        <button type="button" className="btn btn-ghost btn-sm" onClick={() => onPageChange(1)}>1</button>
                        {visiblePages[0] > 2 && <span style={{ padding: '0 4px', color: '#94a3b8', alignSelf: 'center' }}>...</span>}
                    </>
                )}

                {visiblePages.map((page) => (
                    <button
                        key={page}
                        type="button"
                        className={`btn btn-sm ${currentPage === page ? 'btn-primary' : 'btn-ghost'}`}
                        style={currentPage === page ? { cursor: 'default' } : {}}
                        onClick={() => onPageChange(page)}
                    >
                        {page}
                    </button>
                ))}

                {visiblePages[visiblePages.length - 1] < totalPages && (
                    <>
                        {visiblePages[visiblePages.length - 1] < totalPages - 1 && <span style={{ padding: '0 4px', color: '#94a3b8', alignSelf: 'center' }}>...</span>}
                        <button type="button" className="btn btn-ghost btn-sm" onClick={() => onPageChange(totalPages)}>{totalPages}</button>
                    </>
                )}

                <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    disabled={currentPage === totalPages}
                    onClick={() => onPageChange(currentPage + 1)}
                >
                    Next
                </button>
            </div>
        </div>
    );
}
