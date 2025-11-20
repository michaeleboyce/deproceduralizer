import { NextResponse } from 'next/server';
import { neon } from '@neondatabase/serverless';
import { getCurrentJurisdiction } from '@/lib/config';

const sql = neon(process.env.DATABASE_URL!);

export async function GET(request: Request) {
  try {
    const jurisdiction = getCurrentJurisdiction();

    // Fetch all structure nodes for the jurisdiction
    // LEFT JOIN with sections to verify which structure nodes have actual section content
    const structures = await sql`
      SELECT
        str.id,
        str.parent_id,
        str.level,
        str.label,
        str.heading,
        str.ordinal,
        CASE WHEN s.id IS NOT NULL THEN true ELSE false END as has_section,
        s.id as section_id
      FROM structure str
      LEFT JOIN sections s ON (
        s.jurisdiction = str.jurisdiction
        AND s.id = str.id
      )
      WHERE str.jurisdiction = ${jurisdiction}
      ORDER BY str.ordinal ASC
    `;

    // Build hierarchical tree structure
    const tree = buildTree(structures);

    return NextResponse.json({
      success: true,
      tree,
      total: structures.length
    });
  } catch (error) {
    console.error('Error fetching structure:', error);
    return NextResponse.json(
      { success: false, error: 'Failed to fetch structure' },
      { status: 500 }
    );
  }
}

interface StructureNode {
  id: string;
  parent_id: string | null;
  level: string;
  label: string;
  heading: string;
  ordinal: number;
  has_section: boolean;
  section_id: string | null;
  children?: StructureNode[];
}

function buildTree(nodes: any[]): StructureNode[] {
  const nodeMap = new Map<string, StructureNode>();
  const rootNodes: StructureNode[] = [];

  // First pass: create map of all nodes
  nodes.forEach(node => {
    nodeMap.set(node.id, { ...node, children: [] });
  });

  // Second pass: build tree structure
  nodes.forEach(node => {
    const currentNode = nodeMap.get(node.id)!;
    if (node.parent_id === null) {
      rootNodes.push(currentNode);
    } else {
      const parentNode = nodeMap.get(node.parent_id);
      if (parentNode) {
        parentNode.children!.push(currentNode);
      }
    }
  });

  return rootNodes;
}
