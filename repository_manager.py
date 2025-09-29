import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
import git
from git import Repo


class RepositoryManager:
    """Manages cloning and cleanup of GitHub repositories"""
    
    def __init__(self, base_temp_dir: Optional[Path] = None):
        self.base_temp_dir = base_temp_dir or Path(tempfile.gettempdir())
        self.cloned_repos: list[Path] = []
    
    def clone_repository(self, repo_url: str, target_dir: Optional[Path] = None) -> Path:
        """
        Clone a GitHub repository to a temporary directory
        
        Args:
            repo_url: GitHub repository URL
            target_dir: Optional target directory, if None will use temp dir
            
        Returns:
            Path to the cloned repository
        """
        if target_dir is None:
            # Create a unique temporary directory based on repo name
            repo_name = self._extract_repo_name(repo_url)
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
            print(f"Cloning repository: {repo_url}")
            repo = Repo.clone_from(repo_url, target_dir, depth=1)
            self.cloned_repos.append(target_dir)
            print(f"Repository cloned to: {target_dir}")
            return target_dir
        except git.exc.GitCommandError as e:
            raise ValueError(f"Failed to clone repository {repo_url}: {e}")
    
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