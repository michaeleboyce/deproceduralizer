import { NextResponse } from 'next/server';
import { neon } from '@neondatabase/serverless';
import { getCurrentJurisdiction } from '@/lib/config';

const sql = neon(process.env.DATABASE_URL!);

export async function GET(request: Request) {
  try {
    const jurisdiction = getCurrentJurisdiction();

    // Fetch all structure nodes for the jurisdiction
    const structures = await sql`
      SELECT
        id,
        parent_id,
        level,
        label,
        heading,
        ordinal
      FROM structure
      WHERE jurisdiction = ${jurisdiction}
      ORDER BY ordinal ASC
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
