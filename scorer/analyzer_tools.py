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
                   pattern: str, 
                   extensions: Optional[List[str]] = None,
                   case_sensitive: bool = False,
                   max_results: int = 100) -> Dict[str, List[str]]:
        """
        Search for patterns across multiple files. Use only when you need to search across many files.
        For documentation criteria, prefer reading README.md directly with read_file().
        
        Args:
            pattern: Regex pattern to search for
            extensions: File extensions to search in
            case_sensitive: Whether search should be case sensitive
            max_results: Maximum number of matches to return
            
        Returns:
            Dictionary mapping relative file paths to lists of matching lines
        """
        results = {}
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)
        
        files = self.list_files(extensions=extensions)
        match_count = 0
        
        for file_path_str in files:
            if match_count >= max_results:
                break
                
            full_path = self.repo_path / file_path_str
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    matches = []
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            matches.append(f"Line {line_num}: {line.strip()}")
                            match_count += 1
                            if match_count >= max_results:
                                break
                    
                    if matches:
                        results[file_path_str] = matches
            except Exception:
                continue
        
        return results

    def find_files_by_name(self, pattern: str) -> List[str]:
        """
        Find files matching a name pattern. Use to locate unknown file paths.
        
        Args:
            pattern: Filename pattern to match (e.g., "README*", "*.md")
            
        Returns:
            List of relative file paths matching the pattern
        """
        import fnmatch
        files = self.list_files()
        return [f for f in files if fnmatch.fnmatch(Path(f).name.lower(), pattern.lower())]