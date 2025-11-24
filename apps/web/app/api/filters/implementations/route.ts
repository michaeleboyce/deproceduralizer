import { createFilterHandler, filterQueries } from '@/lib/api/filters';

/**
 * GET /api/filters/implementations
 *
 * Returns list of unique implementation complexity levels that have results
 * matching the provided filters
 *
 * Query params:
 * - jurisdiction: string (default: "dc")
 * - title: string (optional) - filter by title
 * - chapter: string (optional) - filter by chapter
 * - hasReporting: boolean (optional) - filter by reporting requirement
 * - query: string (optional) - full-text search query
 */
export const GET = createFilterHandler({
    type: 'complex',
    resultField: 'complexityLevels',
    buildQuery: filterQueries.implementationComplexities,
    transformResult: (rows) => rows.map((row: any) => row.overall_complexity).filter(Boolean),
});
