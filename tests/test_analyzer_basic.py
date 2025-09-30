import tempfile
import shutil
from pathlib import Path

from scorer.analyzer_tools import AnalyzerTools, NotebookMarkdownFormatter


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


class TestMultiplePatterns:
    def setup_method(self):
        """Set up test environment with various files"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create test files with different patterns
        (self.temp_path / "README.md").write_text("# Project\nimport pandas\nimport numpy")
        (self.temp_path / "LICENSE").write_text("MIT License")
        (self.temp_path / "setup.py").write_text("import setuptools\nimport numpy")
        (self.temp_path / "requirements.txt").write_text("pandas\nnumpy\nscikit-learn")
        (self.temp_path / "main.py").write_text("import pandas as pd\nimport sklearn")
        (self.temp_path / "config.yaml").write_text("name: test")
        
        # Create subdirectory
        subdir = self.temp_path / "src"
        subdir.mkdir()
        (subdir / "module.py").write_text("import pandas\nimport torch")
        (subdir / "README.txt").write_text("Module docs")
        
        self.analyzer = AnalyzerTools(str(self.temp_path))
    
    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_find_files_by_name_single_pattern(self):
        """Test finding files with single pattern"""
        files = self.analyzer.find_files_by_name("README*")
        
        assert len(files) == 2
        assert any("README.md" in f for f in files)
        assert any("README.txt" in f for f in files)
    
    def test_find_files_by_name_multiple_patterns(self):
        """Test finding files with multiple patterns using |"""
        files = self.analyzer.find_files_by_name("README*|LICENSE*|*.yaml")
        
        assert len(files) == 4
        assert any("README.md" in f for f in files)
        assert any("README.txt" in f for f in files)
        assert any("LICENSE" in f for f in files)
        assert any("config.yaml" in f for f in files)
    
    def test_find_files_by_name_wildcard_patterns(self):
        """Test finding files with wildcard patterns"""
        files = self.analyzer.find_files_by_name("*.py|*.txt")
        
        assert len(files) >= 3
        assert any("setup.py" in f for f in files)
        assert any("main.py" in f for f in files)
        assert any("module.py" in f for f in files)
        assert any("README.txt" in f for f in files)
    
    def test_search_content_single_pattern(self):
        """Test searching content with single pattern (backward compatibility)"""
        results = self.analyzer.search_content("import pandas")
        
        assert isinstance(results, dict)
        assert len(results) >= 2
        assert any("README.md" in f for f in results)
        assert any("main.py" in f or "module.py" in f for f in results)
    
    def test_search_content_multiple_patterns(self):
        """Test searching content with multiple patterns"""
        results = self.analyzer.search_content(["import pandas", "import numpy", "import sklearn"])
        
        assert isinstance(results, dict)
        assert "import pandas" in results
        assert "import numpy" in results
        assert "import sklearn" in results
        
        # Check that each pattern has results
        assert len(results["import pandas"]) >= 2
        assert len(results["import numpy"]) >= 1
        assert len(results["import sklearn"]) >= 1
    
    def test_search_content_multiple_patterns_with_extensions(self):
        """Test searching multiple patterns with file extension filter"""
        results = self.analyzer.search_content(
            ["import pandas", "import sklearn"],
            extensions=['.py']
        )
        
        assert "import pandas" in results
        assert "import sklearn" in results
        
        # Should only find in .py files, not in README.md
        for pattern_results in results.values():
            for file_path in pattern_results.keys():
                assert file_path.endswith('.py')
    
    def test_search_content_no_matches(self):
        """Test searching for patterns with no matches"""
        results = self.analyzer.search_content(["nonexistent_pattern", "another_missing"])
        
        assert "nonexistent_pattern" in results
        assert "another_missing" in results
        assert len(results["nonexistent_pattern"]) == 0
        assert len(results["another_missing"]) == 0
    
    def test_search_content_max_files_limit(self):
        """Test that max_files parameter limits number of files returned"""
        # Create many files with the same pattern
        for i in range(10):
            (self.temp_path / f"test_{i}.py").write_text(f"import pandas\n# File {i}")
        
        # Search with max_files=3
        results = self.analyzer.search_content("import pandas", max_files=3)
        
        # Should return at most 3 files
        assert len(results) <= 3
        assert len(results) > 0
    
    def test_search_content_max_results_limit(self):
        """Test that max_results parameter limits number of matches"""
        # Create a file with many matching lines
        many_imports = "\n".join([f"import pandas  # Line {i}" for i in range(100)])
        (self.temp_path / "many_imports.py").write_text(many_imports)
        
        # Search with max_results=5
        results = self.analyzer.search_content("import pandas", max_results=5)
        
        # Should return at most 5 matches total
        total_matches = sum(len(matches) for matches in results.values())
        assert total_matches <= 5
        assert total_matches > 0


class TestNotebookMarkdownFormatterBasic:
    def test_format_simple_notebook(self):
        """Test formatting a simple notebook"""
        notebook_content = """{
            "cells": [
                {
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": ["# Test Notebook\\n", "This is a test."]
                },
                {
                    "cell_type": "code",
                    "metadata": {},
                    "source": ["print('hello')\\n", "x = 1"],
                    "outputs": [],
                    "execution_count": null
                }
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3"
                }
            },
            "nbformat": 4,
            "nbformat_minor": 4
        }"""
        
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