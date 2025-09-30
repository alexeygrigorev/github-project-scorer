import shutil
import tempfile
import re

from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import git
from git import Repo


class RepositoryManager:
    """Manages cloning and cleanup of GitHub repositories"""
    
    def __init__(self, base_temp_dir: Optional[Path] = None):
        self.base_temp_dir = base_temp_dir or Path(tempfile.gettempdir())
        self.cloned_repos: list[Path] = []
    
    def parse_github_url(self, url: str) -> Tuple[str, Optional[str]]:
        """
        Parse various GitHub URL formats and extract canonical repo URL and subfolder path.
        
        Supported formats:
        - https://github.com/user/repo
        - https://github.com/user/repo.git
        - https://github.com/user/repo/tree/branch/path/to/folder
        - https://github.com/user/repo/tree/main
        - git@github.com:user/repo.git
        - git@github.com:user/repo
        
        Returns:
            Tuple of (canonical_clone_url, subfolder_path)
            e.g., ("https://github.com/user/repo.git", "path/to/folder")
        """
        url = url.strip()
        
        # Handle git@ SSH URLs
        ssh_match = re.match(r'git@github.com:([^/]+)/(.+?)(?:\.git)?$', url)
        if ssh_match:
            user, repo = ssh_match.groups()
            # Convert to HTTPS for cloning
            return f"https://github.com/{user}/{repo}.git", None
        
        # Handle HTTPS URLs
        # Pattern: https://github.com/user/repo[.git][/tree/branch][/path/to/folder]
        https_match = re.match(
            r'https://github.com/([^/]+)/([^/]+?)(?:\.git)?(?:/tree/[^/]+)?(?:/(.+))?/?$',
            url
        )
        if https_match:
            user, repo, subfolder = https_match.groups()
            canonical_url = f"https://github.com/{user}/{repo}.git"
            return canonical_url, subfolder
        
        # If no pattern matches, try to use as-is
        # Remove trailing .git if present for consistency
        if url.endswith('.git'):
            return url, None
        else:
            return f"{url.rstrip('/')}.git", None
    
    def clone_repository(self, repo_url: str, target_dir: Optional[Path] = None) -> Path:
        """
        Clone a GitHub repository to a temporary directory, or return path if it's already local.
        Supports subfolder paths in URLs.
        
        Args:
            repo_url: GitHub repository URL (various formats) or local filesystem path
            target_dir: Optional target directory, if None will use temp dir
            
        Returns:
            Path to the repository root or subfolder (either cloned or local)
        """
        # Check if this is a local filesystem path
        local_path = Path(repo_url)
        if local_path.exists() and local_path.is_dir():
            print(f"Using local repository: {local_path}")
            return local_path.resolve()
        
        # Parse the GitHub URL
        canonical_url, subfolder = self.parse_github_url(repo_url)
        
        # It's a URL, proceed with cloning
        if target_dir is None:
            # Create a unique temporary directory based on repo name
            repo_name = self._extract_repo_name(canonical_url)
            target_dir = self.base_temp_dir / f"github_scorer_{repo_name}"
        
        # Remove existing directory if it exists
        if target_dir.exists():
            try:
                shutil.rmtree(target_dir)
            except PermissionError:
                # On Windows, git files can be read-only. Try to handle this.
                import stat
                import os
                def handle_remove_readonly(func, path, exc):
                    if os.path.exists(path):
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                
                shutil.rmtree(target_dir, onerror=handle_remove_readonly)
        
        try:
            print(f"Cloning repository: {canonical_url}")
            if subfolder:
                print(f"Will use subfolder: {subfolder}")
            
            repo = Repo.clone_from(canonical_url, target_dir, depth=1)
            self.cloned_repos.append(target_dir)
            
            # If there's a subfolder, return the subfolder path
            if subfolder:
                subfolder_path = target_dir / subfolder
                if not subfolder_path.exists():
                    raise ValueError(f"Subfolder '{subfolder}' does not exist in repository")
                print(f"Using subfolder: {subfolder_path}")
                return subfolder_path
            
            print(f"Repository cloned to: {target_dir}")
            return target_dir
        except git.exc.GitCommandError as e:
            raise ValueError(f"Failed to clone repository {canonical_url}: {e}")
    
    def _extract_repo_name(self, repo_url: str) -> str:
        """Extract repository name from URL"""
        parsed = urlparse(repo_url)
        path = parsed.path.strip('/')
        if path.endswith('.git'):
            path = path[:-4]
        return path.replace('/', '_')
    
    def cleanup(self):
        """Clean up all cloned repositories"""
        for repo_path in self.cloned_repos:
            if repo_path.exists():
                try:
                    shutil.rmtree(repo_path)
                    print(f"Cleaned up: {repo_path}")
                except OSError as e:
                    print(f"Warning: Could not clean up {repo_path}: {e}")
        self.cloned_repos.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()