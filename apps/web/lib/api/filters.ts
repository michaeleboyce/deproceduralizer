import { NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { sections } from '@/db/schema';
import { eq, and, sql, SQL } from 'drizzle-orm';
import { getCurrentJurisdiction, validateJurisdiction } from '@/lib/config';
import { apiError, extractFilterParams } from './utils';

/**
 * Configuration for simple filter routes that select a single field from sections table
 */
interface SimpleFilterConfig {
    type: 'simple';
    resultField: string;
    selectField: typeof sections.titleLabel | typeof sections.chapterLabel;
}

/**
 * Configuration for complex filter routes with joins and custom SQL
 */
interface ComplexFilterConfig {
    type: 'complex';
    resultField: string;
    buildQuery: (params: {
        jurisdiction: string;
        title: string | null;
        chapter: string | null;
        hasReporting: boolean;
        query: string | null;
    }) => SQL;
    transformResult?: (rows: any[]) => any[];
}

type FilterConfig = SimpleFilterConfig | ComplexFilterConfig;

/**
 * Creates a filter route handler based on configuration.
 * Handles common patterns like jurisdiction, title/chapter filtering, and error handling.
 */
export function createFilterHandler(config: FilterConfig) {
    return async function GET(request: Request) {
        try {
            const { searchParams } = new URL(request.url);
            const jurisdiction = validateJurisdiction(searchParams.get('jurisdiction')) || getCurrentJurisdiction();
            const { title, chapter, hasReporting, query } = extractFilterParams(searchParams);

            if (config.type === 'simple') {
                // Simple query using Drizzle ORM
                const conditions: SQL[] = [eq(sections.jurisdiction, jurisdiction)];

                if (title && title.trim()) {
                    conditions.push(eq(sections.titleLabel, title));
                }

                const results = await db
                    .selectDistinct({ value: config.selectField })
                    .from(sections)
                    .where(and(...conditions))
                    .orderBy(config.selectField);

                return NextResponse.json({
                    [config.resultField]: results.map((r) => r.value).filter(Boolean),
                });
            } else {
                // Complex query using raw SQL
                const sqlQuery = config.buildQuery({
                    jurisdiction,
                    title,
                    chapter,
                    hasReporting,
                    query,
                });

                const result = await db.execute(sqlQuery);
                const rows = config.transformResult
                    ? config.transformResult(result.rows as any[])
                    : result.rows;

                return NextResponse.json({
                    [config.resultField]: rows,
                });
            }
        } catch (error) {
            console.error(`Failed to fetch ${config.resultField}:`, error);
            return apiError(`Failed to fetch ${config.resultField}`, 500);
        }
    };
}

/**
 * Pre-built query builders for complex filter routes
 */
export const filterQueries = {
    obligations: (params: {
        jurisdiction: string;
        title: string | null;
        chapter: string | null;
        hasReporting: boolean;
        query: string | null;
    }) => sql`
        SELECT DISTINCT obl.category
        FROM obligations obl
        INNER JOIN sections s ON (
            s.jurisdiction = obl.jurisdiction
            AND s.id = obl.section_id
        )
        WHERE obl.jurisdiction = ${params.jurisdiction}
        ${params.title && params.title.trim() ? sql`AND s.title_label = ${params.title}` : sql``}
        ${params.chapter && params.chapter.trim() ? sql`AND s.chapter_label = ${params.chapter}` : sql``}
        ${params.hasReporting ? sql`AND s.has_reporting = true` : sql``}
        ${params.query && params.query.trim() ? sql`AND s.text_fts @@ plainto_tsquery('english', ${params.query})` : sql``}
        ORDER BY obl.category
    `,

    anachronismSeverities: (params: {
        jurisdiction: string;
        title: string | null;
        chapter: string | null;
        hasReporting: boolean;
        query: string | null;
    }) => sql`
        SELECT DISTINCT sa.overall_severity
        FROM section_anachronisms sa
        INNER JOIN sections s ON (
            s.jurisdiction = sa.jurisdiction
            AND s.id = sa.section_id
        )
        WHERE sa.jurisdiction = ${params.jurisdiction}
        AND sa.has_anachronism = true
        AND sa.overall_severity IS NOT NULL
        ${params.title && params.title.trim() ? sql`AND s.title_label = ${params.title}` : sql``}
        ${params.chapter && params.chapter.trim() ? sql`AND s.chapter_label = ${params.chapter}` : sql``}
        ${params.hasReporting ? sql`AND s.has_reporting = true` : sql``}
        ${params.query && params.query.trim() ? sql`AND s.text_fts @@ plainto_tsquery('english', ${params.query})` : sql``}
        ORDER BY sa.overall_severity
    `,

    implementationComplexities: (params: {
        jurisdiction: string;
        title: string | null;
        chapter: string | null;
        hasReporting: boolean;
        query: string | null;
    }) => sql`
        SELECT DISTINCT pi.overall_complexity
        FROM section_pahlka_implementations pi
        INNER JOIN sections s ON (
            s.jurisdiction = pi.jurisdiction
            AND s.id = pi.section_id
        )
        WHERE pi.jurisdiction = ${params.jurisdiction}
        AND pi.has_implementation_issues = true
        AND pi.overall_complexity IS NOT NULL
        ${params.title && params.title.trim() ? sql`AND s.title_label = ${params.title}` : sql``}
        ${params.chapter && params.chapter.trim() ? sql`AND s.chapter_label = ${params.chapter}` : sql``}
        ${params.hasReporting ? sql`AND s.has_reporting = true` : sql``}
        ${params.query && params.query.trim() ? sql`AND s.text_fts @@ plainto_tsquery('english', ${params.query})` : sql``}
        ORDER BY pi.overall_complexity
    `,
};
