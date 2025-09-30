import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from analyzer_tools import AnalyzerTools, NotebookMarkdownFormatter


class TestAnalyzerToolsBasic:
    def setup_method(self):
        """Set up test environment with mock repository"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create test files
        (self.temp_path / "README.md").write_text("# Test Project\nThis is a test.")
        (self.temp_path / "main.py").write_text("print('hello world')")
        (self.temp_path / "test.py").write_text("def test_function():\n    pass")
        
        # Create subdirectory
        subdir = self.temp_path / "src"
        subdir.mkdir()
        (subdir / "module.py").write_text("class TestClass:\n    pass")
        
        self.analyzer = AnalyzerTools(str(self.temp_path))
    
    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_analyzer_init(self):
        """Test AnalyzerTools initialization"""
        assert self.analyzer.repo_path == Path(self.temp_path)
    
    def test_read_file_text(self):
        """Test reading a text file"""
        content = self.analyzer.read_file("README.md")
        
        assert "# Test Project" in content
        assert "This is a test." in content
    
    def test_read_file_python(self):
        """Test reading a Python file"""
        content = self.analyzer.read_file("main.py")
        
        assert "print('hello world')" in content
    
    def test_read_file_nonexistent(self):
        """Test reading non-existent file"""
        content = self.analyzer.read_file("nonexistent.txt")
        
        assert "Error reading file" in content or "not found" in content.lower()
    
    def test_invalid_repository_path(self):
        """Test analyzer with invalid repository path"""
        analyzer = AnalyzerTools("/nonexistent/path")
        
        # Should handle gracefully
        content = analyzer.read_file("any_file.txt")
        assert "Error reading file" in content or "not found" in content.lower()


class TestNotebookMarkdownFormatterBasic:
    def test_format_simple_notebook(self):
        """Test formatting a simple notebook"""
        notebook_content = """{"cells": [{"cell_type": "markdown", "source": ["# Test Notebook\\n", "This is a test."]}, {"cell_type": "code", "source": ["print('hello')\\n", "x = 1"], "outputs": []}], "metadata": {}, "nbformat": 4, "nbformat_minor": 4}"""
        
        formatter = NotebookMarkdownFormatter()
        result = formatter.format(notebook_content)
        
        assert "# Test Notebook" in result
        assert "This is a test." in result
        assert "print('hello')" in result
        assert "x = 1" in result
    
    def test_format_empty_notebook(self):
        """Test formatting empty notebook"""
        notebook_content = """{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 4}"""
        
        formatter = NotebookMarkdownFormatter()
        result = formatter.format(notebook_content)
        
        # Should not crash and return some result
        assert isinstance(result, str)