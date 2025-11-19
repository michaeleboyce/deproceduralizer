import json
import sys
from pathlib import Path

def load_pairs(filepath):
    pairs = set()
    with open(filepath) as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            # Store as tuple of sorted IDs to handle directionality
            pair = tuple(sorted((data['section_a'], data['section_b'])))
            pairs.add(pair)
    return pairs

def compare_results(flat_path, ivf_path):
    flat_pairs = load_pairs(flat_path)
    ivf_pairs = load_pairs(ivf_path)
    
    common = flat_pairs.intersection(ivf_pairs)
    missing_in_ivf = flat_pairs - ivf_pairs
    extra_in_ivf = ivf_pairs - flat_pairs
    
    recall = len(common) / len(flat_pairs) if flat_pairs else 0
    
    print(f"Flat pairs: {len(flat_pairs)}")
    print(f"IVF pairs:  {len(ivf_pairs)}")
    print(f"Common:     {len(common)}")
    print(f"Recall:     {recall:.2%}")
    print(f"Missing in IVF: {len(missing_in_ivf)}")
    print(f"Extra in IVF:   {len(extra_in_ivf)}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_benchmarks.py <flat_ndjson> <ivf_ndjson>")
        sys.exit(1)
    
    compare_results(sys.argv[1], sys.argv[2])
