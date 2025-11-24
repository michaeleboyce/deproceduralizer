'use client';

import { useState, useCallback, useRef } from 'react';

interface UseApiDataOptions<T> {
    initialData?: T;
}

/**
 * Hook for managing API data fetching with loading/error states.
 * Handles race conditions by tracking request IDs.
 */
export function useApiData<T>(options: UseApiDataOptions<T> = {}) {
    const { initialData } = options;

    const [data, setData] = useState<T | undefined>(initialData);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Track request ID to handle race conditions
    const requestIdRef = useRef(0);

    /**
     * Fetch data from an API endpoint
     */
    const fetchData = useCallback(async (
        url: string,
        params?: URLSearchParams
    ): Promise<T | undefined> => {
        const currentRequestId = ++requestIdRef.current;

        setLoading(true);
        setError(null);

        try {
            const fullUrl = params ? `${url}?${params.toString()}` : url;
            const response = await fetch(fullUrl);

            // Check if this is still the latest request
            if (currentRequestId !== requestIdRef.current) {
                return undefined;
            }

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            // Check again after parsing
            if (currentRequestId !== requestIdRef.current) {
                return undefined;
            }

            setData(result);
            return result;
        } catch (err) {
            // Only set error if this is still the latest request
            if (currentRequestId === requestIdRef.current) {
                const errorMessage = err instanceof Error ? err.message : 'Unknown error';
                setError(errorMessage);
                console.error('API fetch error:', err);
            }
            return undefined;
        } finally {
            // Only update loading if this is still the latest request
            if (currentRequestId === requestIdRef.current) {
                setLoading(false);
            }
        }
    }, []);

    /**
     * Reset state to initial values
     */
    const reset = useCallback(() => {
        requestIdRef.current++;
        setData(initialData);
        setLoading(false);
        setError(null);
    }, [initialData]);

    /**
     * Manually update data without fetching
     */
    const updateData = useCallback((updater: T | ((prev: T | undefined) => T)) => {
        if (typeof updater === 'function') {
            setData((prev) => (updater as (prev: T | undefined) => T)(prev));
        } else {
            setData(updater);
        }
    }, []);

    return {
        data,
        loading,
        error,
        fetchData,
        reset,
        updateData,
        setData,
        setLoading,
        setError,
    };
}

export type UseApiDataReturn<T> = ReturnType<typeof useApiData<T>>;
