import { NextResponse } from 'next/server';
import { db } from '@/lib/db';
import { sections, sectionRefs } from '@/db/schema';
import { eq, and, or, sql } from 'drizzle-orm';

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const jurisdiction = 'dc'; // Hardcoded for now
    const limit = parseInt(searchParams.get('limit') || '100');
    const centerId = searchParams.get('centerId');

    let nodes = [];
    let edges = [];

    if (centerId) {
        // Fetch ego network: center node + neighbors
        // 1. Get edges where centerId is source or target
        const relatedEdges = await db
            .select({
                source: sectionRefs.fromId,
                target: sectionRefs.toId,
            })
            .from(sectionRefs)
            .where(and(
                eq(sectionRefs.jurisdiction, jurisdiction),
                or(
                    eq(sectionRefs.fromId, centerId),
                    eq(sectionRefs.toId, centerId)
                )
            ))
            .limit(limit);

        // 2. Collect all unique node IDs from these edges
        const nodeIds = new Set<string>([centerId]);
        relatedEdges.forEach(e => {
            nodeIds.add(e.source);
            nodeIds.add(e.target);
        });

        // 3. Fetch node details for all collected IDs
        nodes = await db
            .select({
                id: sections.id,
                label: sections.citation,
                title: sections.heading,
                group: sections.titleLabel,
            })
            .from(sections)
            .where(and(
                eq(sections.jurisdiction, jurisdiction),
                sql`${sections.id} IN ${Array.from(nodeIds)}`
            ));

        edges = relatedEdges;
    } else {
        // Global graph (limited)
        nodes = await db
            .select({
                id: sections.id,
                label: sections.citation,
                title: sections.heading,
                group: sections.titleLabel, // Use Title as group for coloring
            })
            .from(sections)
            .where(eq(sections.jurisdiction, jurisdiction))
            .limit(limit);

        // Fetch edges (references)
        // We only want edges where both source and target are in our node set
        const nodeIds = nodes.map(n => n.id);

        const allEdges = await db
            .select({
                source: sectionRefs.fromId,
                target: sectionRefs.toId,
            })
            .from(sectionRefs)
            .where(and(
                eq(sectionRefs.jurisdiction, jurisdiction),
                // This is a simplification; for a perfect graph we'd filter by nodeIds in JS or complex query
                // For performance, let's just fetch a reasonable amount and filter in memory
            ))
            .limit(limit * 5);

        // Filter edges to ensure both ends exist in our nodes
        edges = allEdges.filter(e => nodeIds.includes(e.source) && nodeIds.includes(e.target));
    }

    return NextResponse.json({
        nodes: nodes.map(n => ({
            ...n,
            val: n.id === centerId ? 3 : 1, // Highlight center node
            color: n.id === centerId ? '#ef4444' : undefined // Red for center
        })),
        links: edges
    });
}
