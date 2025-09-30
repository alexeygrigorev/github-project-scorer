import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
from pathlib import Path

from scorer.repository_manager import RepositoryManager


class TestURLParsing:
    """Test URL parsing functionality"""
    
    def test_parse_https_basic(self):
        """Test parsing basic HTTPS URL"""
        manager = RepositoryManager()
        canonical, subfolder = manager.parse_github_url("https://github.com/user/repo")
        
        assert canonical == "https://github.com/user/repo.git"
        assert subfolder is None
    
    def test_parse_https_with_git(self):
        """Test parsing HTTPS URL with .git extension"""
        manager = RepositoryManager()
        canonical, subfolder = manager.parse_github_url("https://github.com/user/repo.git")
        
        assert canonical == "https://github.com/user/repo.git"
        assert subfolder is None
    
    def test_parse_https_with_trailing_slash(self):
        """Test parsing HTTPS URL with trailing slash"""
        manager = RepositoryManager()
        canonical, subfolder = manager.parse_github_url("https://github.com/alexeygrigorev/aihero/")
        
        assert canonical == "https://github.com/alexeygrigorev/aihero.git"
        assert subfolder is None
    
    def test_parse_https_with_tree_main(self):
        """Test parsing HTTPS URL with /tree/main (no subfolder) - uses URL as-is"""
        manager = RepositoryManager()
        canonical, subfolder = manager.parse_github_url("https://github.com/alexeygrigorev/aihero/tree/main")
        
        # URL patterns with /tree/branch but no subfolder are treated as-is
        # They won't clone correctly, so this URL format should be avoided
        assert canonical == "https://github.com/alexeygrigorev/aihero.git"
        assert subfolder is None
    
    def test_parse_https_with_subfolder(self):
        """Test parsing HTTPS URL with subfolder path"""
        manager = RepositoryManager()
        canonical, subfolder = manager.parse_github_url("https://github.com/alexeygrigorev/aihero/tree/main/code")
        
        assert canonical == "https://github.com/alexeygrigorev/aihero.git"
        assert subfolder == "code"
    
    def test_parse_https_with_deep_subfolder(self):
        """Test parsing HTTPS URL with deep subfolder path"""
        manager = RepositoryManager()
        canonical, subfolder = manager.parse_github_url("https://github.com/user/repo/tree/main/path/to/folder")
        
        assert canonical == "https://github.com/user/repo.git"
        assert subfolder == "path/to/folder"
    
    def test_parse_ssh_basic(self):
        """Test parsing SSH URL (git@)"""
        manager = RepositoryManager()
        canonical, subfolder = manager.parse_github_url("git@github.com:alexeygrigorev/aihero.git")
        
        assert canonical == "https://github.com/alexeygrigorev/aihero.git"
        assert subfolder is None
    
    def test_parse_ssh_without_git(self):
        """Test parsing SSH URL without .git"""
        manager = RepositoryManager()
        canonical, subfolder = manager.parse_github_url("git@github.com:user/repo")
        
        assert canonical == "https://github.com/user/repo.git"
        assert subfolder is None


class TestRepositoryManager:
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init_default(self):
        """Test RepositoryManager initialization with defaults"""
        manager = RepositoryManager()
        
        assert manager.base_temp_dir is not None
        assert isinstance(manager.cloned_repos, list)
        assert len(manager.cloned_repos) == 0
    
    def test_init_with_base_dir(self):
        """Test RepositoryManager initialization with custom base directory"""
        manager = RepositoryManager(base_temp_dir=self.temp_path)
        
        assert manager.base_temp_dir == self.temp_path
        assert isinstance(manager.cloned_repos, list)
    
    def test_local_path_handling(self):
        """Test handling local directory paths"""
        # Create a test local directory
        local_dir = self.temp_path / "test_repo"
        local_dir.mkdir()
        (local_dir / "README.md").write_text("Test repository")
        
        manager = RepositoryManager()
        repo_path = manager.clone_repository(str(local_dir))
        
        # Should return the resolved path
        assert repo_path == local_dir.resolve()
        assert repo_path.exists()
        assert (repo_path / "README.md").exists()
    
    def test_local_path_nonexistent(self):
        """Test handling non-existent local path"""
        manager = RepositoryManager()
        
        # Should proceed to clone (and likely fail), not return local path
        nonexistent_path = "/definitely/nonexistent/path"
        
        # Since it's not a valid URL either, it should raise an exception
        with pytest.raises((ValueError, Exception)):
            manager.clone_repository(nonexistent_path)
    
    @patch('git.Repo.clone_from')
    def test_git_clone_success(self, mock_clone):
        """Test successful git cloning"""
        # Mock successful clone
        mock_repo = Mock()
        mock_clone.return_value = mock_repo
        
        manager = RepositoryManager(base_temp_dir=self.temp_path)
        repo_url = "https://github.com/example/repo.git"
        
        result = manager.clone_repository(repo_url)
        
        expected_target = self.temp_path / "github_scorer_example_repo"
        mock_clone.assert_called_once_with(repo_url, expected_target, depth=1)
        assert result == expected_target
        assert expected_target in manager.cloned_repos
    
    @patch('git.Repo.clone_from')
    def test_git_clone_failure(self, mock_clone):
        """Test git clone failure"""
        # Mock clone failure
        from git.exc import GitCommandError
        mock_clone.side_effect = GitCommandError("clone", "Clone failed")
        
        manager = RepositoryManager()
        repo_url = "https://github.com/example/nonexistent.git"
        
        with pytest.raises(ValueError, match="Failed to clone repository"):
            manager.clone_repository(repo_url)
    
    def test_extract_repo_name_github(self):
        """Test extracting repository name from GitHub URL"""
        manager = RepositoryManager()
        
        # Test various GitHub URL formats
        test_cases = [
            ("https://github.com/user/repo.git", "user_repo"),
            ("https://github.com/user/repo", "user_repo"),
            ("https://github.com/user/repo-name.git", "user_repo-name"),
        ]
        
        for url, expected_name in test_cases:
            name = manager._extract_repo_name(url)
            assert name == expected_name
    
    def test_extract_repo_name_special_chars(self):
        """Test extracting repository name with special characters"""
        manager = RepositoryManager()
        
        test_cases = [
            ("https://gitlab.com/user/project.git", "user_project"),
            ("https://bitbucket.org/user/repository", "user_repository"),
            ("https://custom-git.com/path/to/repo.git", "path_to_repo"),
        ]
        
        for url, expected_name in test_cases:
            name = manager._extract_repo_name(url)
            assert name == expected_name
    
    def test_extract_repo_name_edge_cases(self):
        """Test edge cases for repository name extraction"""
        manager = RepositoryManager()
        
        # Test edge cases
        edge_cases = [
            ("", ""),  # Empty string
            ("invalid-url", "invalid-url"),  # Invalid URL
            ("https://github.com/", ""),  # Incomplete URL
        ]
        
        for url, expected_name in edge_cases:
            name = manager._extract_repo_name(url)
            assert name == expected_name
    
    @patch('shutil.rmtree')
    def test_cleanup(self, mock_rmtree):
        """Test cleanup functionality"""
        manager = RepositoryManager()
        
        # Add some fake cloned repos
        fake_path1 = Path("/fake/path1")
        fake_path2 = Path("/fake/path2")
        manager.cloned_repos = [fake_path1, fake_path2]
        
        # Mock exists to return True
        with patch.object(Path, 'exists', return_value=True):
            manager.cleanup()
        
        # Should call rmtree for each repo
        assert mock_rmtree.call_count == 2
        assert len(manager.cloned_repos) == 0
    
    @patch('shutil.rmtree')
    def test_cleanup_with_errors(self, mock_rmtree):
        """Test cleanup with permission errors"""
        mock_rmtree.side_effect = OSError("Permission denied")
        
        manager = RepositoryManager()
        fake_path = Path("/fake/path")
        manager.cloned_repos = [fake_path]
        
        with patch.object(Path, 'exists', return_value=True):
            # Should not raise exception
            manager.cleanup()
        
        # Should still clear the list
        assert len(manager.cloned_repos) == 0
    
    def test_context_manager(self):
        """Test using RepositoryManager as context manager"""
        with patch.object(RepositoryManager, 'cleanup') as mock_cleanup:
            with RepositoryManager() as manager:
                assert isinstance(manager, RepositoryManager)
            
            # cleanup should be called when exiting context
            mock_cleanup.assert_called_once()
    
    def test_context_manager_with_exception(self):
        """Test context manager cleanup when exception occurs"""
        with patch.object(RepositoryManager, 'cleanup') as mock_cleanup:
            try:
                with RepositoryManager() as manager:
                    raise ValueError("Test exception")
            except ValueError:
                pass
            
            # cleanup should still be called after exception
            mock_cleanup.assert_called_once()
    
    @patch('git.Repo.clone_from')
    @patch('shutil.rmtree')
    def test_clone_with_existing_directory(self, mock_rmtree, mock_clone):
        """Test cloning when target directory already exists"""
        manager = RepositoryManager(base_temp_dir=self.temp_path)
        
        # Create directory that would conflict
        target_dir = self.temp_path / "github_scorer_example_repo"
        target_dir.mkdir()
        (target_dir / "existing.txt").write_text("existing content")
        
        # Mock clone to succeed
        mock_repo = Mock()
        mock_clone.return_value = mock_repo
        
        repo_url = "https://github.com/example/repo.git"
        result = manager.clone_repository(repo_url)
        
        # Should remove existing directory first
        mock_rmtree.assert_called_once_with(target_dir)
        mock_clone.assert_called_once_with(repo_url, target_dir, depth=1)
        assert result == target_dir


class TestRepositoryManagerEdgeCases:
    def test_extract_repo_name_complex_paths(self):
        """Test extracting repo names from complex URL paths"""
        manager = RepositoryManager()
        
        test_cases = [
            ("https://github.com/org/sub/repo.git", "org_sub_repo"),
            ("https://enterprise.git.com/team/project/repo", "team_project_repo"),
        ]
        
        for url, expected in test_cases:
            result = manager._extract_repo_name(url)
            assert result == expected
    
    def test_init_with_temp_dir_issues(self):
        """Test handling issues with temporary directory"""
        # Platform-agnostic test
        manager = RepositoryManager()
        
        # Should use some temp directory
        assert manager.base_temp_dir is not None
        assert isinstance(manager.base_temp_dir, Path)
    
    def test_local_path_edge_cases(self):
        """Test local path handling edge cases"""
        manager = RepositoryManager()
        
        # Test with non-existent path (should try to clone and fail)
        with pytest.raises((ValueError, Exception)):
            manager.clone_repository("/definitely/nonexistent/path/that/does/not/exist")
    
    @patch('git.Repo.clone_from')
    def test_clone_with_custom_target_dir(self, mock_clone):
        """Test cloning with custom target directory"""
        mock_repo = Mock()
        mock_clone.return_value = mock_repo
        
        manager = RepositoryManager()
        custom_target = Path("/custom/target/path")
        
        result = manager.clone_repository("https://github.com/user/repo.git", custom_target)
        
        mock_clone.assert_called_once_with("https://github.com/user/repo.git", custom_target, depth=1)
        assert result == custom_target
        assert custom_target in manager.cloned_repos