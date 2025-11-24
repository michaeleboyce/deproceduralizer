'use client';

import { useState, useEffect, useCallback } from 'react';

/**
 * Hook for managing hierarchical title/chapter filters with auto-loading.
 * Automatically loads titles on mount and chapters when title changes.
 */
export function useFilters() {
    // Filter state
    const [selectedTitle, setSelectedTitle] = useState('');
    const [selectedChapter, setSelectedChapter] = useState('');

    // Available options
    const [availableTitles, setAvailableTitles] = useState<string[]>([]);
    const [availableChapters, setAvailableChapters] = useState<string[]>([]);

    // Loading state
    const [loadingTitles, setLoadingTitles] = useState(false);
    const [loadingChapters, setLoadingChapters] = useState(false);

    // Load titles on mount
    useEffect(() => {
        loadTitles();
    }, []);

    // Load chapters when title changes
    useEffect(() => {
        if (selectedTitle) {
            loadChapters(selectedTitle);
        } else {
            setAvailableChapters([]);
            setSelectedChapter('');
        }
    }, [selectedTitle]);

    const loadTitles = async () => {
        setLoadingTitles(true);
        try {
            const response = await fetch('/api/filters/titles');
            const data = await response.json();
            setAvailableTitles(data.titles || []);
        } catch (err) {
            console.error('Failed to load titles:', err);
            setAvailableTitles([]);
        } finally {
            setLoadingTitles(false);
        }
    };

    const loadChapters = async (title: string) => {
        setLoadingChapters(true);
        try {
            const response = await fetch(`/api/filters/chapters?title=${encodeURIComponent(title)}`);
            const data = await response.json();
            setAvailableChapters(data.chapters || []);
        } catch (err) {
            console.error('Failed to load chapters:', err);
            setAvailableChapters([]);
        } finally {
            setLoadingChapters(false);
        }
    };

    const setTitle = useCallback((title: string) => {
        setSelectedTitle(title);
        // Clear chapter when title changes
        if (title !== selectedTitle) {
            setSelectedChapter('');
        }
    }, [selectedTitle]);

    const setChapter = useCallback((chapter: string) => {
        setSelectedChapter(chapter);
    }, []);

    const clearFilters = useCallback(() => {
        setSelectedTitle('');
        setSelectedChapter('');
        setAvailableChapters([]);
    }, []);

    /**
     * Get filter params for API calls
     */
    const getFilterParams = useCallback(() => {
        const params = new URLSearchParams();
        if (selectedTitle) params.append('title', selectedTitle);
        if (selectedChapter) params.append('chapter', selectedChapter);
        return params;
    }, [selectedTitle, selectedChapter]);

    /**
     * Check if any filters are active
     */
    const hasActiveFilters = selectedTitle || selectedChapter;

    return {
        // Current values
        selectedTitle,
        selectedChapter,

        // Setters
        setTitle,
        setChapter,
        clearFilters,

        // Available options
        availableTitles,
        availableChapters,

        // Loading states
        loadingTitles,
        loadingChapters,

        // Utilities
        getFilterParams,
        hasActiveFilters,

        // For direct control if needed
        setSelectedTitle,
        setSelectedChapter,
    };
}

export type UseFiltersReturn = ReturnType<typeof useFilters>;
