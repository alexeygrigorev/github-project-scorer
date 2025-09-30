import os
import re

from pathlib import Path
from typing import List, Dict, Optional

import pathspec
import nbformat

from nbconvert import MarkdownExporter
from nbconvert.preprocessors import ClearOutputPreprocessor


class NotebookMarkdownFormatter:
    """Converts Jupyter notebook content to markdown format."""

    def __init__(self):
        self.exporter = MarkdownExporter()
        self.exporter.register_preprocessor(ClearOutputPreprocessor(), enabled=True)

    def format(self, raw_notebook: str) -> str:
        nb_parsed = nbformat.reads(
            raw_notebook,
            as_version=nbformat.NO_CONVERT,
        )
        md_body, _ = self.exporter.from_notebook_node(nb_parsed)
        return md_body


class AnalyzerTools:
    """Tools for analyzing files in a repository"""
    
    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path)
        self.gitignore_spec = self._load_gitignore()
        self.notebook_formatter = NotebookMarkdownFormatter()
    
    def _load_gitignore(self) -> Optional[pathspec.PathSpec]:
        """Load .gitignore patterns if file exists"""
        gitignore_path = self.repo_path / '.gitignore'
        if gitignore_path.exists():
            with open(gitignore_path, 'r', encoding='utf-8', errors='ignore') as f:
                patterns = f.read().splitlines()
            return pathspec.PathSpec.from_lines('gitwildmatch', patterns)
        return None
    
    def list_files(self, 
                   extensions: Optional[List[str]] = None,
                   exclude_patterns: Optional[List[str]] = None,
                   max_files: int = 1000) -> List[str]:
        """
        Get complete file list for repository overview.
        Use a reasonable limit like max_files=100 for initial overview.
        
        Args:
            extensions: File extensions to include (e.g., ['.py', '.js'])
            exclude_patterns: Additional patterns to exclude
            max_files: Maximum number of files to return (default 1000, suggest 100 for overview)
            
        Returns:
            List of relative file paths from repository root
        """
        files = []
        exclude_patterns = exclude_patterns or []
        
        # Default exclusions
        default_excludes = [
            '__pycache__', '.git', 'node_modules', '.venv', 'venv',
            '.pytest_cache', '.mypy_cache', 'dist', 'build'
        ]
        exclude_patterns.extend(default_excludes)
        
        # Image and binary file extensions to exclude
        binary_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', '.svg',
            '.ico', '.pdf', '.zip', '.tar', '.gz', '.rar', '.7z',
            '.exe', '.dll', '.so', '.dylib', '.bin', '.dat',
            '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac',
            '.woff', '.woff2', '.ttf', '.otf', '.eot',
            '.psd', '.ai', '.sketch', '.fig'
        }
        
        for root, dirs, filenames in os.walk(self.repo_path):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
            
            for filename in filenames:
                file_path = Path(root) / filename
                relative_path = file_path.relative_to(self.repo_path)
                
                # Skip if matches gitignore
                if self.gitignore_spec and self.gitignore_spec.match_file(str(relative_path)):
                    continue
                
                # Skip if matches exclude patterns
                if any(pattern in str(file_path) for pattern in exclude_patterns):
                    continue
                
                # Filter by extensions
                if extensions and file_path.suffix not in extensions:
                    continue
                
                # Skip binary files (images, videos, etc.)
                if file_path.suffix.lower() in binary_extensions:
                    continue
                
                files.append(str(file_path.relative_to(self.repo_path)))
                
                if len(files) >= max_files:
                    break
        
        return files[:max_files]
    
    def read_file(self, file_path: str, max_lines: int = 1000) -> str:
        """
        Read complete file content. Use this first for documentation and specific files.
        More efficient than searching when you know the file path.
        
        Args:
            file_path: Relative path from repository root (e.g., "README.md", "docs/setup.md")
            max_lines: Maximum number of lines to read
            
        Returns:
            Complete file content as string. For .ipynb files, returns markdown format with cleared outputs.
        """
        try:
            # Convert relative path to absolute path
            if isinstance(file_path, str):
                full_path = self.repo_path / file_path
            else:
                # Handle legacy Path objects
                if file_path.is_absolute():
                    full_path = file_path
                else:
                    full_path = self.repo_path / file_path
            
            # Check if it's a notebook file
            if full_path.suffix.lower() == '.ipynb':
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_notebook = f.read()
                
                # Convert notebook to markdown and clear outputs
                markdown_content = self.notebook_formatter.format(raw_notebook)
                
                # Apply line limit to markdown content
                lines = markdown_content.split('\n')
                if len(lines) > max_lines:
                    lines = lines[:max_lines]
                    lines.append(f"\n... (notebook truncated after {max_lines} lines)")
                
                return '\n'.join(lines)
            
            else:
                # Regular file reading
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            lines.append(f"\n... (truncated after {max_lines} lines)")
                            break
                        lines.append(line.rstrip())
                    return '\n'.join(lines)
                    
        except Exception as e:
            return f"Error reading file {file_path}: {e}"
    
    def _grep_files(self, 
                   patterns: List[str], 
                   extensions: Optional[List[str]] = None,
                   case_sensitive: bool = False,
                   max_results: int = 100,
                   max_files: int = 100) -> Dict[str, Dict[str, List[str]]]:
        """
        Search for multiple patterns across files. Use only when you need to search across many files.
        For documentation criteria, prefer reading README.md directly with read_file().
        
        Args:
            patterns: List of regex patterns to search for
            extensions: File extensions to search in
            case_sensitive: Whether search should be case sensitive
            max_results: Maximum number of matches to return per pattern
            max_files: Maximum number of files to return per pattern
            
        Returns:
            Dictionary mapping patterns to {file_path: [matching_lines]}
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        compiled_patterns = [(p, re.compile(p, flags)) for p in patterns]
        
        # Initialize results structure: {pattern: {file: [matches]}}
        results = {pattern: {} for pattern in patterns}
        pattern_counts = {pattern: 0 for pattern in patterns}
        pattern_file_counts = {pattern: 0 for pattern in patterns}
        
        files = self.list_files(extensions=extensions)
        
        for file_path_str in files:
            full_path = self.repo_path / file_path_str
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_matches = {pattern: [] for pattern in patterns}
                    
                    for line_num, line in enumerate(f, 1):
                        for pattern, regex in compiled_patterns:
                            if pattern_counts[pattern] >= max_results:
                                continue
                            
                            if regex.search(line):
                                file_matches[pattern].append(f"Line {line_num}: {line.strip()}")
                                pattern_counts[pattern] += 1
                    
                    # Add file matches to results (respecting max_files limit)
                    for pattern in patterns:
                        if file_matches[pattern]:
                            if pattern_file_counts[pattern] < max_files:
                                results[pattern][file_path_str] = file_matches[pattern]
                                pattern_file_counts[pattern] += 1
            except Exception:
                continue
        
        return results

    def find_files_by_name(self, pattern: str) -> List[str]:
        """
        Find files matching name pattern(s). Use VERY SPARINGLY - only when you don't know file locations.
        Prefer using list_files() to see all files, then read specific files.
        
        Args:
            pattern: Filename pattern to match. Supports:
                - Single pattern: "README*" or "*.md"
                - Multiple patterns with |: "README*|LICENSE*|*.md"
            
        Returns:
            List of relative file paths matching any of the patterns
        """
        import fnmatch
        files = self.list_files()
        
        # Split patterns by | symbol
        patterns = [p.strip() for p in pattern.split('|')]
        
        matched_files = []
        for f in files:
            filename_lower = Path(f).name.lower()
            if any(fnmatch.fnmatch(filename_lower, p.lower()) for p in patterns):
                matched_files.append(f)
        
        return matched_files
    
    def search_content(self, 
                      patterns, 
                      extensions: Optional[List[str]] = None,
                      case_sensitive: bool = False,
                      max_results: int = 50,
                      max_files: int = 20):
        """
        Search for text patterns across repository files. Use sparingly - only when you need to find 
        specific content across many files. For checking documentation, use read_file() instead.
        
        Args:
            patterns: Single pattern string OR list of patterns to search for
            extensions: Optional list of file extensions to search (e.g., ['.py', '.md'])
            case_sensitive: Whether search should be case sensitive (default: False)
            max_results: Maximum number of matching lines to return per pattern (default: 50)
            max_files: Maximum number of files to return per pattern (default: 20)
            
        Returns:
            If single pattern: Dictionary mapping file paths to lists of matching lines
            If multiple patterns: Dictionary mapping patterns to {file_path: [matching_lines]}
        """
        # Handle single pattern for backward compatibility
        if isinstance(patterns, str):
            results = self._grep_files([patterns], extensions, case_sensitive, max_results, max_files)
            # Return flat structure for single pattern
            return results[patterns] if patterns in results else {}
        
        # Handle multiple patterns
        return self._grep_files(patterns, extensions, case_sensitive, max_results, max_files)
    
    def get_project_summary(self) -> Dict[str, any]:
        """
        Get a high-level summary of the repository structure and key files.
        Use this as a first step to understand the project before detailed analysis.
        
        Returns:
            Dictionary containing:
            - 'total_files': int - total number of files
            - 'file_types': dict - count of files by extension
            - 'key_files': list - important files (README, config, etc.)
            - 'directories': list - main directory structure
            - 'has_tests': bool - whether test files are present
            - 'has_docs': bool - whether documentation exists
        """
        all_files = self.list_files()
        
        # Count file types
        file_types = {}
        key_files = []
        directories = set()
        
        for file_path in all_files:
            path = Path(file_path)
            
            # Count by extension
            ext = path.suffix.lower() or 'no_extension'
            file_types[ext] = file_types.get(ext, 0) + 1
            
            # Track directories (top level only)
            if '/' in file_path or '\\' in file_path:
                top_dir = str(path.parts[0]) if path.parts else ''
                if top_dir:
                    directories.add(top_dir)
            
            # Identify key files
            name_lower = path.name.lower()
            if any(key in name_lower for key in [
                'readme', 'license', 'requirements', 'setup.py', 'pyproject.toml',
                'package.json', 'docker', 'makefile', '.env', 'config'
            ]):
                key_files.append(file_path)
        
        # Check for tests and docs
        has_tests = any('test' in f.lower() for f in all_files)
        has_docs = any(any(doc in f.lower() for doc in ['readme', 'doc', 'docs']) for f in all_files)
        
        return {
            'total_files': len(all_files),
            'file_types': dict(sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:10]),
            'key_files': key_files,
            'directories': sorted(list(directories)),
            'has_tests': has_tests,
            'has_docs': has_docs
        }