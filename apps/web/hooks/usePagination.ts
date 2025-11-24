'use client';

import { useState, useCallback, useMemo } from 'react';

interface PaginationOptions {
    initialPage?: number;
    initialLimit?: number;
}

/**
 * Hook for managing pagination state.
 */
export function usePagination(options: PaginationOptions = {}) {
    const { initialPage = 1, initialLimit = 50 } = options;

    const [currentPage, setCurrentPage] = useState(initialPage);
    const [limit, setLimit] = useState(initialLimit);
    const [totalItems, setTotalItems] = useState(0);

    const totalPages = useMemo(() => {
        return Math.ceil(totalItems / limit) || 1;
    }, [totalItems, limit]);

    const offset = useMemo(() => {
        return (currentPage - 1) * limit;
    }, [currentPage, limit]);

    const nextPage = useCallback(() => {
        if (currentPage < totalPages) {
            setCurrentPage((prev) => prev + 1);
        }
    }, [currentPage, totalPages]);

    const prevPage = useCallback(() => {
        if (currentPage > 1) {
            setCurrentPage((prev) => prev - 1);
        }
    }, [currentPage]);

    const goToPage = useCallback((page: number) => {
        const validPage = Math.max(1, Math.min(page, totalPages));
        setCurrentPage(validPage);
    }, [totalPages]);

    const reset = useCallback(() => {
        setCurrentPage(initialPage);
    }, [initialPage]);

    /**
     * Get pagination params for API calls
     */
    const getPaginationParams = useCallback(() => {
        const params = new URLSearchParams();
        params.append('page', currentPage.toString());
        params.append('limit', limit.toString());
        params.append('offset', offset.toString());
        return params;
    }, [currentPage, limit, offset]);

    const canGoNext = currentPage < totalPages;
    const canGoPrev = currentPage > 1;

    return {
        // Current state
        currentPage,
        limit,
        offset,
        totalItems,
        totalPages,

        // Navigation
        nextPage,
        prevPage,
        goToPage,
        reset,

        // Setters
        setCurrentPage,
        setLimit,
        setTotalItems,

        // Utilities
        getPaginationParams,
        canGoNext,
        canGoPrev,
    };
}

export type UsePaginationReturn = ReturnType<typeof usePagination>;
