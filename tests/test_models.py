import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import yaml

from scorer.models import (
    ScoredCriteria, 
    ChecklistCriteria, 
    ScoreLevel, 
    ChecklistItem, 
    EvaluationResult,
    ProjectEvaluation,
    load_criteria_from_yaml
)


class TestScoredCriteria:
    def test_scored_criteria_creation(self):
        """Test creating a ScoredCriteria object"""
        score_levels = [
            ScoreLevel(score=0, description="No implementation"),
            ScoreLevel(score=5, description="Basic implementation"),
            ScoreLevel(score=10, description="Full implementation")
        ]
        
        criteria = ScoredCriteria(
            name="Test Criteria",
            score_levels=score_levels,
            max_score=10
        )
        
        assert criteria.name == "Test Criteria"
        assert criteria.max_score == 10
        assert len(criteria.score_levels) == 3
        assert criteria.score_levels[0].score == 0
        assert criteria.score_levels[2].score == 10
        assert criteria.type == "scored"


class TestChecklistCriteria:
    def test_checklist_criteria_creation(self):
        """Test creating a ChecklistCriteria object"""
        items = [
            ChecklistItem(description="Has README", points=2),
            ChecklistItem(description="Has tests", points=3),
            ChecklistItem(description="Has documentation", points=5)
        ]
        
        criteria = ChecklistCriteria(
            name="Project Structure",
            items=items,
            max_score=10
        )
        
        assert criteria.name == "Project Structure"
        assert criteria.max_score == 10
        assert len(criteria.items) == 3
        assert sum(item.points for item in criteria.items) == 10
        assert criteria.type == "checklist"


class TestEvaluationResult:
    def test_evaluation_result_creation(self):
        """Test creating an EvaluationResult"""
        result = EvaluationResult(
            criteria_name="Test Criteria",
            criteria_type="scored",
            score=8,
            max_score=10,
            reasoning="Good implementation with minor issues",
            evidence=["Found README.md", "Found test files"]
        )
        
        assert result.criteria_name == "Test Criteria"
        assert result.score == 8
        assert result.max_score == 10
        assert "Good implementation" in result.reasoning
        assert len(result.evidence) == 2


class TestProjectEvaluation:
    def test_project_evaluation_creation(self):
        """Test creating a ProjectEvaluation"""
        results = [
            EvaluationResult(
                criteria_name="Test",
                criteria_type="scored",
                score=5,
                max_score=10,
                reasoning="Test",
                evidence=[]
            )
        ]
        
        evaluation = ProjectEvaluation(
            project_url="https://github.com/test/repo",
            project_path=Path("/test/path"),
            total_score=5,
            max_total_score=10,
            results=results,
            improvements=["Add more tests"]
        )
        
        assert evaluation.project_url == "https://github.com/test/repo"
        assert evaluation.total_score == 5
        assert evaluation.max_total_score == 10
        assert len(evaluation.results) == 1
        assert len(evaluation.improvements) == 1


class TestLoadCriteriaFromYaml:
    def setup_method(self):
        """Set up test files"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test files"""
        shutil.rmtree(self.temp_dir)
    
    def test_load_valid_scored_criteria(self):
        """Test loading valid scored criteria from YAML"""
        yaml_content = """
criteria:
  - name: "Code Quality"
    type: "scored"
    score_levels:
      - score: 0
        description: "No code quality measures"
      - score: 5
        description: "Basic code quality"
      - score: 10
        description: "Excellent code quality"
"""
        
        yaml_file = self.temp_path / "test_criteria.yaml"
        yaml_file.write_text(yaml_content)
        
        criteria = load_criteria_from_yaml(yaml_file)
        
        assert len(criteria) == 1
        assert isinstance(criteria[0], ScoredCriteria)
        assert criteria[0].name == "Code Quality"
        assert criteria[0].max_score == 10
        assert len(criteria[0].score_levels) == 3
    
    def test_load_valid_checklist_criteria(self):
        """Test loading valid checklist criteria from YAML"""
        yaml_content = """
criteria:
  - name: "Project Structure"
    type: "checklist"
    items:
      - description: "Has README"
        points: 3
      - description: "Has tests"
        points: 5
"""
        
        yaml_file = self.temp_path / "test_criteria.yaml"
        yaml_file.write_text(yaml_content)
        
        criteria = load_criteria_from_yaml(yaml_file)
        
        assert len(criteria) == 1
        assert isinstance(criteria[0], ChecklistCriteria)
        assert criteria[0].name == "Project Structure"
        assert criteria[0].max_score == 8
        assert len(criteria[0].items) == 2
    
    def test_load_invalid_file(self):
        """Test loading from non-existent file"""
        with pytest.raises(FileNotFoundError):
            load_criteria_from_yaml(Path("non_existent_file.yaml"))
    
    def test_load_invalid_yaml(self):
        """Test loading malformed YAML"""
        yaml_content = """
invalid: yaml: content:
  - missing: bracket
"""
        
        yaml_file = self.temp_path / "invalid.yaml"
        yaml_file.write_text(yaml_content)
        
        with pytest.raises(yaml.YAMLError):
            load_criteria_from_yaml(yaml_file)
    
    def test_load_missing_criteria_key(self):
        """Test loading YAML without criteria key"""
        yaml_content = """
other_data:
  - name: "Not criteria"
"""
        
        yaml_file = self.temp_path / "no_criteria.yaml"
        yaml_file.write_text(yaml_content)
        
        criteria = load_criteria_from_yaml(yaml_file)
        assert criteria == []


class TestScoreLevel:
    def test_score_level_creation(self):
        """Test creating a ScoreLevel"""
        level = ScoreLevel(score=5, description="Basic implementation")
        
        assert level.score == 5
        assert level.description == "Basic implementation"


class TestChecklistItem:
    def test_checklist_item_creation(self):
        """Test creating a ChecklistItem"""
        item = ChecklistItem(description="Has tests", points=3)
        
        assert item.description == "Has tests"
        assert item.points == 3