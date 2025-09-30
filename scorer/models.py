import yaml

from typing import List, Union
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ScoreLevel:
    """Represents a single score level in a criteria"""
    score: int
    description: str


@dataclass
class ScoredCriteria:
    """Criteria with numeric scoring (0-N points)"""
    name: str
    score_levels: List[ScoreLevel]
    max_score: int
    
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
    """Criteria with checklist items"""
    name: str
    items: List[ChecklistItem]
    max_score: int
    
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
    """Load evaluation criteria from YAML file"""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    criteria = []
    
    for criteria_data in data.get('criteria', []):
        criteria_type = criteria_data.get('type', '').lower()
        
        if criteria_type == 'scored':
            # Scored criteria - explicit type
            if 'score_levels' not in criteria_data:
                raise ValueError(f"Scored criteria '{criteria_data.get('name')}' missing 'score_levels'")
            
            score_levels = [
                ScoreLevel(score=level['score'], description=level['description'])
                for level in criteria_data['score_levels']
            ]
            max_score = max(level.score for level in score_levels)
            criteria.append(ScoredCriteria(
                name=criteria_data['name'],
                score_levels=score_levels,
                max_score=max_score
            ))
            
        elif criteria_type == 'checklist':
            # Checklist criteria - explicit type
            if 'items' not in criteria_data:
                raise ValueError(f"Checklist criteria '{criteria_data.get('name')}' missing 'items'")
            
            items = [
                ChecklistItem(description=item['description'], points=item['points'])
                for item in criteria_data['items']
            ]
            max_score = sum(item.points for item in items)
            criteria.append(ChecklistCriteria(
                name=criteria_data['name'],
                items=items,
                max_score=max_score
            ))
            
        elif 'score_levels' in criteria_data:
            # Fallback: Scored criteria (backward compatibility)
            print(f"Warning: Criteria '{criteria_data.get('name')}' missing explicit type, assuming 'scored'")
            score_levels = [
                ScoreLevel(score=level['score'], description=level['description'])
                for level in criteria_data['score_levels']
            ]
            max_score = max(level.score for level in score_levels)
            criteria.append(ScoredCriteria(
                name=criteria_data['name'],
                score_levels=score_levels,
                max_score=max_score
            ))
            
        elif 'items' in criteria_data:
            # Fallback: Checklist criteria (backward compatibility)
            print(f"Warning: Criteria '{criteria_data.get('name')}' missing explicit type, assuming 'checklist'")
            items = [
                ChecklistItem(description=item['description'], points=item['points'])
                for item in criteria_data['items']
            ]
            max_score = sum(item.points for item in items)
            criteria.append(ChecklistCriteria(
                name=criteria_data['name'],
                items=items,
                max_score=max_score
            ))
            
        else:
            raise ValueError(f"Unknown criteria type or missing required fields for '{criteria_data.get('name')}'. "
                           f"Expected type 'scored' with 'score_levels' or type 'checklist' with 'items'")
    
    return criteria