import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock
import json

from models import ScoredCriteria, ChecklistCriteria, ScoreLevel, ChecklistItem
from analyzer_tools import AnalyzerTools


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_repo_structure(temp_directory):
    """Create a sample repository structure for testing"""
    repo_path = Path(temp_directory)
    
    # Create main files
    (repo_path / "README.md").write_text("# Test Project\nThis is a test repository.")
    (repo_path / "main.py").write_text("def main():\n    print('Hello, World!')")
    (repo_path / "requirements.txt").write_text("requests>=2.25.0\npandas>=1.3.0")
    
    # Create source directory
    src_dir = repo_path / "src"
    src_dir.mkdir()
    (src_dir / "__init__.py").write_text("")
    (src_dir / "utils.py").write_text("def helper_function():\n    return 'helper'")
    (src_dir / "models.py").write_text("class DataModel:\n    pass")
    
    # Create tests directory
    tests_dir = repo_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("")
    (tests_dir / "test_main.py").write_text("def test_main():\n    assert True")
    (tests_dir / "test_utils.py").write_text("def test_helper():\n    assert True")
    
    # Create docs directory
    docs_dir = repo_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "api.md").write_text("# API Documentation")
    
    # Create a Jupyter notebook
    notebook_content = {
        "cells": [
            {
                "cell_type": "markdown",
                "source": ["# Data Analysis Notebook"]
            },
            {
                "cell_type": "code",
                "source": ["import pandas as pd\ndf = pd.DataFrame({'A': [1, 2, 3]})"],
                "outputs": []
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 4
    }
    (repo_path / "analysis.ipynb").write_text(json.dumps(notebook_content))
    
    # Create config files
    (repo_path / ".gitignore").write_text("__pycache__/\n*.pyc\n.env")
    (repo_path / "pyproject.toml").write_text("[project]\nname = 'test-project'")
    
    return str(repo_path)


@pytest.fixture
def sample_scored_criteria():
    """Create sample scored criteria for testing"""
    return ScoredCriteria(
        name="Code Quality",
        description="Assess the overall code quality of the project",
        max_score=10,
        score_levels=[
            ScoreLevel(score=0, description="No code quality measures"),
            ScoreLevel(score=3, description="Basic code structure"),
            ScoreLevel(score=6, description="Good code quality"),
            ScoreLevel(score=10, description="Excellent code quality")
        ]
    )


@pytest.fixture
def sample_checklist_criteria():
    """Create sample checklist criteria for testing"""
    return ChecklistCriteria(
        name="Project Structure",
        description="Check if project has essential structural elements",
        max_score=10,
        items=[
            ChecklistItem(description="Has README file", points=3),
            ChecklistItem(description="Has test files", points=3),
            ChecklistItem(description="Has source code organization", points=2),
            ChecklistItem(description="Has documentation", points=2)
        ]
    )


@pytest.fixture
def mock_analyzer_tools():
    """Create a mock AnalyzerTools instance"""
    mock_analyzer = Mock(spec=AnalyzerTools)
    
    # Mock common methods
    mock_analyzer.list_files.return_value = [
        {"name": "README.md", "type": "file"},
        {"name": "main.py", "type": "file"},
        {"name": "src/utils.py", "type": "file"},
        {"name": "tests/test_main.py", "type": "file"}
    ]
    
    mock_analyzer.read_file.return_value = "Mock file content"
    mock_analyzer.grep_files.return_value = ["main.py:1:def main():"]
    mock_analyzer.find_files_by_name.return_value = [{"name": "README.md", "type": "file"}]
    
    return mock_analyzer


@pytest.fixture
def analyzer_tools_with_repo(sample_repo_structure):
    """Create real AnalyzerTools instance with sample repository"""
    return AnalyzerTools(sample_repo_structure)


@pytest.fixture
def mock_pricing_config(temp_directory):
    """Create a mock pricing configuration file"""
    pricing_content = """
models:
  gpt-4:
    input: 0.03
    output: 0.06
  gpt-3.5-turbo:
    input: 0.001
    output: 0.002
  claude-3:
    input: 0.015
    output: 0.075
"""
    pricing_file = Path(temp_directory) / "pricing.yaml"
    pricing_file.write_text(pricing_content)
    return str(pricing_file)


@pytest.fixture
def sample_criteria_yaml(temp_directory):
    """Create a sample criteria YAML file"""
    criteria_content = """
- name: "Code Quality"
  description: "Assess overall code quality"
  type: "scored"
  max_score: 10
  score_levels:
    - score: 0
      description: "No code quality measures"
    - score: 5
      description: "Basic code quality"
    - score: 10
      description: "Excellent code quality"

- name: "Project Structure"
  description: "Check project structure elements"
  type: "checklist"
  max_score: 8
  items:
    - description: "Has README"
      points: 3
    - description: "Has tests"
      points: 3
    - description: "Has documentation"
      points: 2
"""
    criteria_file = Path(temp_directory) / "criteria.yaml"
    criteria_file.write_text(criteria_content)
    return str(criteria_file)


@pytest.fixture
def mock_agent_result():
    """Create a mock agent result for testing"""
    result = Mock()
    result.output = Mock()
    result.output.score = 7
    result.output.reasoning = "Good implementation with minor issues"
    result.output.evidence = ["Found README.md", "Found test files"]
    result.output.completed_items = [0, 1]  # For checklist results
    
    # Mock usage tracking
    usage = Mock()
    usage.input_tokens = 1000
    usage.output_tokens = 500
    result.usage.return_value = usage
    
    return result


@pytest.fixture
def sample_evaluation_results():
    """Create sample evaluation results for testing"""
    from models import EvaluationResult
    
    return [
        EvaluationResult(
            criteria_name="Code Quality",
            criteria_type="scored",
            score=7,
            max_score=10,
            reasoning="Good code quality with room for improvement",
            evidence=["Well-structured files", "Some documentation missing"]
        ),
        EvaluationResult(
            criteria_name="Testing",
            criteria_type="checklist",
            score=6,
            max_score=8,
            reasoning="Basic testing present",
            evidence=["Unit tests found", "Integration tests missing"]
        )
    ]


@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Automatically cleanup any temporary files created during tests"""
    yield
    # Cleanup any temp files that might have been created
    import glob
    temp_files = glob.glob("test_*")
    for file in temp_files:
        try:
            if Path(file).is_file():
                Path(file).unlink()
            elif Path(file).is_dir():
                shutil.rmtree(file)
        except (OSError, PermissionError):
            pass


# Markers for different test types
pytestmark = [
    pytest.mark.unit,  # Mark all tests as unit tests by default
]