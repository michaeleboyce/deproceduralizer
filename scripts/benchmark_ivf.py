#!/usr/bin/env python3
"""
Benchmark IVF (Inverted File Index) vector search performance.

This script benchmarks the performance of similarity search queries
to help optimize database indexes and query patterns.

Usage:
  python scripts/benchmark_ivf.py --queries 100 --similarity-threshold 0.7
"""

import argparse
import os
import sys
import time
import psycopg2
import statistics
from typing import List, Tuple
import random


def get_random_section_ids(cursor, jurisdiction: str, count: int) -> List[str]:
    """Get random section IDs for benchmarking."""
    cursor.execute("""
        SELECT id
        FROM sections
        WHERE jurisdiction = %s
        ORDER BY RANDOM()
        LIMIT %s
    """, (jurisdiction, count))
    return [row[0] for row in cursor.fetchall()]


def benchmark_similarity_query(
    cursor,
    section_id: str,
    jurisdiction: str,
    min_similarity: float
) -> Tuple[float, int]:
    """
    Benchmark a single similarity query.

    Returns:
        Tuple of (query_time_ms, result_count)
    """
    start_time = time.perf_counter()

    cursor.execute("""
        SELECT section_b, similarity
        FROM section_similarities
        WHERE jurisdiction = %s
          AND section_a = %s
          AND similarity >= %s
        ORDER BY similarity DESC
        LIMIT 20
    """, (jurisdiction, section_id, min_similarity))

    results = cursor.fetchall()
    end_time = time.perf_counter()

    query_time_ms = (end_time - start_time) * 1000
    result_count = len(results)

    return query_time_ms, result_count


def benchmark_bidirectional_similarity_query(
    cursor,
    section_id: str,
    jurisdiction: str,
    min_similarity: float
) -> Tuple[float, int]:
    """
    Benchmark a bidirectional similarity query (section as A or B).

    Returns:
        Tuple of (query_time_ms, result_count)
    """
    start_time = time.perf_counter()

    cursor.execute("""
        SELECT
            CASE
                WHEN section_a = %s THEN section_b
                ELSE section_a
            END as related_section,
            similarity
        FROM section_similarities
        WHERE jurisdiction = %s
          AND (section_a = %s OR section_b = %s)
          AND similarity >= %s
        ORDER BY similarity DESC
        LIMIT 20
    """, (section_id, jurisdiction, section_id, section_id, min_similarity))

    results = cursor.fetchall()
    end_time = time.perf_counter()

    query_time_ms = (end_time - start_time) * 1000
    result_count = len(results)

    return query_time_ms, result_count


def benchmark_join_query(
    cursor,
    section_id: str,
    jurisdiction: str,
    min_similarity: float
) -> Tuple[float, int]:
    """
    Benchmark a similarity query with section details join.

    Returns:
        Tuple of (query_time_ms, result_count)
    """
    start_time = time.perf_counter()

    cursor.execute("""
        SELECT s.id, s.citation, s.heading, sim.similarity
        FROM section_similarities sim
        JOIN sections s ON (sim.jurisdiction = s.jurisdiction AND sim.section_b = s.id)
        WHERE sim.jurisdiction = %s
          AND sim.section_a = %s
          AND sim.similarity >= %s
        ORDER BY sim.similarity DESC
        LIMIT 20
    """, (jurisdiction, section_id, min_similarity))

    results = cursor.fetchall()
    end_time = time.perf_counter()

    query_time_ms = (end_time - start_time) * 1000
    result_count = len(results)

    return query_time_ms, result_count


def print_statistics(name: str, times: List[float], counts: List[int]):
    """Print statistics for a benchmark run."""
    print(f"\n{name}:")
    print(f"  Queries:       {len(times)}")
    print(f"  Mean time:     {statistics.mean(times):.2f} ms")
    print(f"  Median time:   {statistics.median(times):.2f} ms")
    print(f"  Min time:      {min(times):.2f} ms")
    print(f"  Max time:      {max(times):.2f} ms")
    print(f"  Std dev:       {statistics.stdev(times) if len(times) > 1 else 0:.2f} ms")
    print(f"  P95:           {statistics.quantiles(times, n=20)[18]:.2f} ms")
    print(f"  P99:           {statistics.quantiles(times, n=100)[98]:.2f} ms")
    print(f"  Avg results:   {statistics.mean(counts):.1f}")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark IVF vector search performance"
    )
    parser.add_argument(
        '--queries',
        type=int,
        default=100,
        help='Number of queries to run for each benchmark (default: 100)'
    )
    parser.add_argument(
        '--similarity-threshold',
        type=float,
        default=0.7,
        help='Minimum similarity threshold (default: 0.7)'
    )
    parser.add_argument(
        '--jurisdiction',
        type=str,
        default='dc',
        help='Jurisdiction to benchmark (default: dc)'
    )
    parser.add_argument(
        '--warmup',
        type=int,
        default=10,
        help='Number of warmup queries before benchmarking (default: 10)'
    )

    args = parser.parse_args()

    # Get database connection
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("Error: DATABASE_URL environment variable not set", file=sys.stderr)
        sys.exit(1)

    print("=" * 70)
    print("IVF Vector Search Benchmark")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Jurisdiction:          {args.jurisdiction}")
    print(f"  Queries per benchmark: {args.queries}")
    print(f"  Similarity threshold:  {args.similarity_threshold}")
    print(f"  Warmup queries:        {args.warmup}")

    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()

    # Get database statistics
    cursor.execute("""
        SELECT COUNT(*) FROM section_similarities WHERE jurisdiction = %s
    """, (args.jurisdiction,))
    total_similarities = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM sections WHERE jurisdiction = %s
    """, (args.jurisdiction,))
    total_sections = cursor.fetchone()[0]

    print(f"\nDatabase statistics:")
    print(f"  Total sections:        {total_sections:,}")
    print(f"  Total similarities:    {total_similarities:,}")
    print(f"  Avg similarities/sec:  {total_similarities / total_sections:.1f}")

    # Get random section IDs for benchmarking
    print(f"\nGenerating {args.queries + args.warmup} random section IDs...")
    section_ids = get_random_section_ids(
        cursor,
        args.jurisdiction,
        args.queries + args.warmup
    )

    if len(section_ids) < args.queries + args.warmup:
        print(f"Warning: Only found {len(section_ids)} sections, reducing query count")
        args.queries = max(10, len(section_ids) - args.warmup)

    # Warmup phase
    print(f"\nWarmup phase ({args.warmup} queries)...")
    for section_id in section_ids[:args.warmup]:
        benchmark_similarity_query(cursor, section_id, args.jurisdiction, args.similarity_threshold)

    # Benchmark 1: Simple similarity query (section_a only)
    print(f"\nBenchmark 1: Simple similarity query (section_a = ?)...")
    simple_times = []
    simple_counts = []
    for section_id in section_ids[args.warmup:args.warmup + args.queries]:
        query_time, result_count = benchmark_similarity_query(
            cursor, section_id, args.jurisdiction, args.similarity_threshold
        )
        simple_times.append(query_time)
        simple_counts.append(result_count)

    # Benchmark 2: Bidirectional similarity query
    print(f"Benchmark 2: Bidirectional similarity query (section_a = ? OR section_b = ?)...")
    bidirectional_times = []
    bidirectional_counts = []
    for section_id in section_ids[args.warmup:args.warmup + args.queries]:
        query_time, result_count = benchmark_bidirectional_similarity_query(
            cursor, section_id, args.jurisdiction, args.similarity_threshold
        )
        bidirectional_times.append(query_time)
        bidirectional_counts.append(result_count)

    # Benchmark 3: Similarity query with join
    print(f"Benchmark 3: Similarity query with JOIN to sections...")
    join_times = []
    join_counts = []
    for section_id in section_ids[args.warmup:args.warmup + args.queries]:
        query_time, result_count = benchmark_join_query(
            cursor, section_id, args.jurisdiction, args.similarity_threshold
        )
        join_times.append(query_time)
        join_counts.append(result_count)

    # Print results
    print("\n" + "=" * 70)
    print("BENCHMARK RESULTS")
    print("=" * 70)

    print_statistics("Simple query (section_a only)", simple_times, simple_counts)
    print_statistics("Bidirectional query (section_a OR section_b)", bidirectional_times, bidirectional_counts)
    print_statistics("Query with JOIN", join_times, join_counts)

    # Performance comparison
    print("\n" + "=" * 70)
    print("PERFORMANCE COMPARISON")
    print("=" * 70)

    simple_mean = statistics.mean(simple_times)
    bidirectional_mean = statistics.mean(bidirectional_times)
    join_mean = statistics.mean(join_times)

    print(f"\nBidirectional vs Simple:")
    print(f"  Slowdown: {bidirectional_mean / simple_mean:.2f}x")
    print(f"\nJOIN vs Simple:")
    print(f"  Slowdown: {join_mean / simple_mean:.2f}x")
    print(f"\nJOIN vs Bidirectional:")
    print(f"  Slowdown: {join_mean / bidirectional_mean:.2f}x")

    # Index recommendations
    print("\n" + "=" * 70)
    print("INDEX RECOMMENDATIONS")
    print("=" * 70)

    cursor.execute("""
        SELECT tablename, indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'section_similarities'
        ORDER BY indexname
    """)
    indexes = cursor.fetchall()

    print("\nExisting indexes on section_similarities:")
    for tablename, indexname, indexdef in indexes:
        print(f"  - {indexname}")

    print("\nRecommended indexes (if not present):")
    recommended = [
        "CREATE INDEX idx_section_similarities_a ON section_similarities(jurisdiction, section_a, similarity);",
        "CREATE INDEX idx_section_similarities_b ON section_similarities(jurisdiction, section_b, similarity);",
    ]
    for idx in recommended:
        print(f"  {idx}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("✓ Benchmark Complete")
    print("=" * 70)


if __name__ == '__main__':
    main()
