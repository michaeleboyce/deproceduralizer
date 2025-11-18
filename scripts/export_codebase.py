#!/usr/bin/env python3
"""
Export Codebase to Single File

This script exports the entire relevant codebase and documentation
into a single text file for easy sharing with LLMs or documentation.

Usage:
    python scripts/export_codebase.py
    python scripts/export_codebase.py --output exports/codebase-2024-01-01.txt
"""

import os
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Set


# File extensions to include
INCLUDE_EXTENSIONS = {
    '.py', '.md', '.txt', '.sql', '.sh', '.bash',
    '.ts', '.tsx', '.js', '.jsx', '.json', '.yaml', '.yml',
    '.css', '.html', '.gitignore', '.env.example'
}

# Directories to exclude (relative to project root)
EXCLUDE_DIRS = {
    '.venv', 'node_modules', '__pycache__', '.git', '.next',
    'data', 'dist', 'build', '.cache', '.turbo', '.vercel'
}

# File patterns to exclude
EXCLUDE_FILES = {
    '.DS_Store', '.state', '.ckpt', '.checkpoint',
    'package-lock.json', 'pnpm-lock.yaml', 'poetry.lock',
    '.env', '.env.local'  # Never export environment files with secrets
}


def should_include_file(file_path: Path, project_root: Path) -> bool:
    """Determine if a file should be included in the export."""
    # Check if in excluded directory
    try:
        relative = file_path.relative_to(project_root)
        for part in relative.parts:
            if part in EXCLUDE_DIRS:
                return False
    except ValueError:
        return False
    
    # Check filename
    if file_path.name in EXCLUDE_FILES:
        return False
    
    # Check extension
    if file_path.suffix not in INCLUDE_EXTENSIONS and file_path.suffix != '':
        return False
    
    # Special case: Makefile has no extension
    if file_path.name == 'Makefile':
        return True
    
    return True


def get_all_files(project_root: Path) -> List[Path]:
    """Get all files to include, sorted by path."""
    files = []
    for root, dirs, filenames in os.walk(project_root):
        # Modify dirs in-place to skip excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for filename in filenames:
            file_path = Path(root) / filename
            if should_include_file(file_path, project_root):
                files.append(file_path)
    
    return sorted(files)


def generate_tree_structure(project_root: Path, files: List[Path]) -> str:
    """Generate a tree-like directory structure."""
    lines = ["# Project Structure\n```"]
    
    # Build directory tree from files
    dirs_seen: Set[str] = set()
    
    for file_path in files:
        try:
            relative = file_path.relative_to(project_root)
            parts = relative.parts
            
            # Add parent directories
            for i in range(len(parts)):
                dir_path = str(Path(*parts[:i+1]))
                if dir_path not in dirs_seen:
                    indent = "  " * i
                    if i == len(parts) - 1:
                        # File
                        lines.append(f"{indent}├── {parts[i]}")
                    else:
                        # Directory
                        lines.append(f"{indent}├── {parts[i]}/")
                    dirs_seen.add(dir_path)
        except ValueError:
            continue
    
    lines.append("```\n")
    return "\n".join(lines)


def format_file_content(file_path: Path, project_root: Path) -> str:
    """Format a file's content with header."""
    try:
        relative_path = file_path.relative_to(project_root)
    except ValueError:
        relative_path = file_path
    
    separator = "=" * 80
    header = f"\n{separator}\n"
    header += f"FILE: {relative_path}\n"
    header += f"{separator}\n\n"
    
    try:
        content = file_path.read_text(encoding='utf-8')
        return header + content + "\n"
    except UnicodeDecodeError:
        return header + "[Binary file - content omitted]\n"
    except Exception as e:
        return header + f"[Error reading file: {e}]\n"


def export_codebase(project_root: Path, output_path: Path):
    """Export the entire codebase to a single file."""
    print(f"Scanning project: {project_root}")
    files = get_all_files(project_root)
    print(f"Found {len(files)} files to export")
    
    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with output_path.open('w', encoding='utf-8') as f:
        # Write header
        f.write("=" * 80 + "\n")
        f.write("DEPROCEDURALIZER - COMPLETE CODEBASE EXPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Project Root: {project_root}\n")
        f.write(f"Total Files: {len(files)}\n\n")
        
        # Write directory structure
        tree = generate_tree_structure(project_root, files)
        f.write(tree)
        f.write("\n\n")
        
        # Write file contents
        f.write("=" * 80 + "\n")
        f.write("FILE CONTENTS\n")
        f.write("=" * 80 + "\n")
        
        for i, file_path in enumerate(files, 1):
            print(f"Processing [{i}/{len(files)}]: {file_path.relative_to(project_root)}")
            content = format_file_content(file_path, project_root)
            f.write(content)
    
    print(f"\n✅ Export complete: {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.2f} KB")


def main():
    parser = argparse.ArgumentParser(
        description="Export deproceduralizer codebase to a single file"
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=None,
        help='Output file path (default: exports/codebase-YYYY-MM-DD.txt)'
    )
    parser.add_argument(
        '--project-root',
        type=Path,
        default=None,
        help='Project root directory (default: parent of scripts/)'
    )
    
    args = parser.parse_args()
    
    # Determine project root
    if args.project_root:
        project_root = args.project_root.resolve()
    else:
        # Assume script is in scripts/ directory
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d")
        output_path = project_root / "exports" / f"codebase-{timestamp}.txt"
    
    export_codebase(project_root, output_path)


if __name__ == "__main__":
    main()
