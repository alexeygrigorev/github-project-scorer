import yaml

from typing import List, Union, Literal
from dataclasses import dataclass
from pathlib import Path
from pydantic import BaseModel


class EvaluationItem(BaseModel):
    """Represents a single item in a criteria"""
    points: int
    description: str


class EvaluationCriterion(BaseModel):
    """A single evaluation criterion"""
    name: str
    kind: Literal["single", "checklist"]
    items: List[EvaluationItem]
    comment: str | None = None


class EvaluationCriteria(BaseModel):
    """Container for all evaluation criteria"""
    criteria: List[EvaluationCriterion]


# Legacy dataclasses for backward compatibility
@dataclass
class ScoreLevel:
    """Represents a single score level in a criteria"""
    score: int
    description: str


@dataclass
class ScoredCriteria:
    """Criteria with numeric scoring (0-N points) - maps to kind='single'"""
    name: str
    score_levels: List[ScoreLevel]
    max_score: int
    comment: str | None = None
    
    @property
    def type(self) -> str:
        return "scored"


@dataclass
class ChecklistItem:
    """Single item in a checklist criteria"""
    description: str
    points: int


@dataclass
class ChecklistCriteria:
    """Criteria with checklist items - maps to kind='checklist'"""
    name: str
    items: List[ChecklistItem]
    max_score: int
    comment: str | None = None
    
    @property
    def type(self) -> str:
        return "checklist"


@dataclass
class EvaluationResult:
    """Result of evaluating a single criteria"""
    criteria_name: str
    criteria_type: str
    score: int
    max_score: int
    reasoning: str
    evidence: List[str]


@dataclass 
class ScoredCriteriaResult:
    """Result from a scored criteria agent"""
    score: int
    reasoning: str
    evidence: List[str]


@dataclass
class ChecklistResult:
    """Result from a checklist criteria agent"""
    completed_items: List[int]  # Indices of completed items
    reasoning: str
    evidence: List[str]


@dataclass
class ProjectEvaluation:
    """Complete evaluation results for a project"""
    project_url: str
    project_path: Path
    total_score: int
    max_total_score: int
    results: List[EvaluationResult]
    improvements: List[str]


def load_criteria_from_yaml(yaml_path: Path) -> List[Union[ScoredCriteria, ChecklistCriteria]]:
    """Load evaluation criteria from YAML file using new simplified schema"""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        criteria_raw = yaml.safe_load(f)
    
    # Parse using Pydantic model
    criteria_model = EvaluationCriteria.model_validate(criteria_raw)
    
    # Convert to legacy dataclass format for backward compatibility
    result = []
    for criterion in criteria_model.criteria:
        if criterion.kind == "single":
            # Convert to ScoredCriteria
            score_levels = [
                ScoreLevel(score=item.points, description=item.description)
                for item in criterion.items
            ]
            max_score = max(level.score for level in score_levels) if score_levels else 0
            result.append(ScoredCriteria(
                name=criterion.name,
                score_levels=score_levels,
                max_score=max_score,
                comment=criterion.comment
            ))
        elif criterion.kind == "checklist":
            # Convert to ChecklistCriteria
            items = [
                ChecklistItem(description=item.description, points=item.points)
                for item in criterion.items
            ]
            max_score = sum(item.points for item in items)
            result.append(ChecklistCriteria(
                name=criterion.name,
                items=items,
                max_score=max_score,
                comment=criterion.comment
            ))
    
    return result