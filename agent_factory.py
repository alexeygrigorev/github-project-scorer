import inspect
from typing import List, Union, Dict
from pathlib import Path

from pydantic_ai import Agent
from pydantic import BaseModel

from models import ScoredCriteria, ChecklistCriteria
from github_analyzer_tools import GithubAnalyzerTools


class AnalysisContext(BaseModel):
    """Context passed to evaluation agents"""

    repo_path: Path
    file_analyzer: GithubAnalyzerTools
    project_files: List[Path]
    config_files: Dict[str, Path]
    file_stats: Dict[str, int]
    readme_content: str = ""

    class Config:
        arbitrary_types_allowed = True


def get_instance_methods(instance):
    """
    Get all public methods from an instance.

    Args:
        instance: The instance to get methods from.

    Returns:
        list: A list of method objects from the instance that don't start with underscore.
    """
    methods = []
    for name, member in inspect.getmembers(instance, predicate=inspect.ismethod):
        if not name.startswith("_"):
            methods.append(member)
    return methods


# Unified system instructions for all evaluation agents
SYSTEM_INSTRUCTIONS = """You are an expert software engineer and technical evaluator specializing in assessing GitHub repositories against specific quality criteria.

Your mission is to thoroughly evaluate a GitHub repository and provide accurate scoring/assessment based on the provided criteria.

## Evaluation Strategy

1. **Start Smart**: For documentation-focused criteria (problem description, setup instructions), start with README and documentation files
2. **Be Proportional**: Match investigation depth to criteria complexity - simple criteria need simple evidence
3. **Read Documentation**: Find and read README files, documentation, and project descriptions  
4. **Examine Code**: For technical criteria, look at source files to understand implementation quality
5. **Check Configuration**: For setup/deployment criteria, review build files and configurations
6. **Look for Evidence**: Find specific examples that support your decision

## Investigation Guidelines

- **Start with the obvious**: For "problem description" → check README first, other docs second
- **Be efficient**: Don't over-investigate simple criteria that can be answered from documentation  
- **Scale complexity**: Simple criteria = quick investigation, complex criteria = thorough analysis
- **Focus on relevance**: Only examine files directly related to the criteria being evaluated

## Scoring Guidelines

- **Be thorough but proportional**: Don't rush to conclusions, but match effort to criteria complexity
- **Be evidence-based**: Your reasoning must cite specific files, code snippets, or observations
- **Be fair**: Consider the project's scope and purpose when evaluating
- **Be specific**: Provide concrete examples from the repository to justify your decision

## Investigation Process

1. First, understand what you're looking for based on the criteria
2. Plan your investigation strategy (which files to check, what to search for)
3. Use tools systematically to gather evidence - tool docstrings will guide you on usage
4. Cross-reference findings across multiple files when necessary
5. Form a conclusion based on comprehensive but proportional analysis

Remember: The quality of your evaluation depends on the depth of your investigation. Don't accept surface-level observations, but also don't over-investigate simple criteria that can be answered quickly."""


def create_user_prompt(criteria: Union[ScoredCriteria, ChecklistCriteria], context: AnalysisContext) -> str:
    """Create task-specific user prompt based on criteria type"""
    
    if isinstance(criteria, ScoredCriteria):
        # Scored criteria prompt
        score_levels_text = "\n".join([
            f"  {level.score} points: {level.description}" 
            for level in criteria.score_levels
        ])
        
        return f"""Evaluate this GitHub repository against the following criteria:

## Criteria: {criteria.name}

### Scoring Levels:
{score_levels_text}

### Repository Information:
- Repository path: {context.repo_path}
- Project type: Analyze the codebase to determine

### Your Task:
1. **Investigate appropriately** using the available file analysis tools
2. **Gather concrete evidence** from files, code, documentation, and configuration
3. **Assign a score** from 0 to {criteria.max_score} based on the scoring levels
4. **Provide detailed reasoning** explaining your score with specific examples
5. **List evidence** with file names and relevant content snippets

Begin your evaluation by planning which files and aspects to investigate, then systematically gather evidence to support your scoring decision."""

    elif isinstance(criteria, ChecklistCriteria):
        # Checklist criteria prompt
        items_text = "\n".join([
            f"  Item {i}: {item.description} ({item.points} points)"
            for i, item in enumerate(criteria.items)
        ])
        
        return f"""Evaluate this GitHub repository against the following checklist criteria:

## Criteria: {criteria.name}

### Checklist Items:
{items_text}

### Repository Information:
- Repository path: {context.repo_path}
- Project type: Analyze the codebase to determine

### Your Task:
1. **Systematically check each item** in the checklist using file analysis tools
2. **Gather verification evidence** for each item you mark as completed
3. **Return the indices** (0-based) of items that are completed/present
4. **Provide reasoning** explaining which items are completed and why
5. **Document evidence** with specific file names and content that proves completion

Begin by analyzing the project structure, then systematically verify each checklist item with concrete evidence."""

    else:
        raise ValueError(f"Unknown criteria type: {type(criteria)}")


def create_evaluation_agent(model_string: str, file_analyzer: GithubAnalyzerTools, output_type) -> Agent:
    """Create a unified evaluation agent for both scored and checklist criteria"""
    
    tools = get_instance_methods(file_analyzer)
    
    agent = Agent(
        model=model_string,
        output_type=output_type,
        tools=tools,
        system_prompt=SYSTEM_INSTRUCTIONS
    )
    
    return agent