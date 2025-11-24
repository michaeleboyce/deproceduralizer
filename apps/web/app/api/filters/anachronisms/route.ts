import { createFilterHandler, filterQueries } from '@/lib/api/filters';

/**
 * GET /api/filters/anachronisms
 *
 * Returns list of unique anachronism severity levels that have results
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
    resultField: 'severityLevels',
    buildQuery: filterQueries.anachronismSeverities,
    transformResult: (rows) => rows.map((row: any) => row.overall_severity).filter(Boolean),
});
