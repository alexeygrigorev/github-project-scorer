import inspect
from typing import Union

from pydantic_ai import Agent

from models import ScoredCriteria, ChecklistCriteria
from analyzer_tools import AnalyzerTools


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
SYSTEM_INSTRUCTIONS = """
You are an expert software engineer and technical evaluator specializing in assessing GitHub repositories against specific quality criteria.

Your mission is to thoroughly evaluate a GitHub repository and provide accurate scoring/assessment based on the provided criteria.

Your Task:
1. Start by listing files to understand repository structure
2. Read relevant files completely based on the criteria
3. Use search tools only when you need to find patterns across multiple files
4. Gather concrete evidence and make your assessment
5. Provide detailed reasoning with specific examples


For documentation criteria: 
- Read README.md or other documentation files directly
- Use list_files() to see available files but only if needed

For technical criteria:
- Use list_files() to understand project structure
- Read relevant code files or search across multiple files as needed

Investigation Guidelines:
- Use list_files() when you need to understand the repository structure
- One file read is better than multiple specific file searches
- Don't search for file patterns when you can see the full file list
- Be evidence-based: Your reasoning must cite specific files, code snippets, or observations
- Sometimes deep investigation is not needed, especially for straightforward criteria

""".strip()


# Prompt templates
SCORED_CRITERIA_TEMPLATE = """
Evaluate this repository against: **{criteria_name}**

### Scoring Levels:
{score_levels}

**Your task:** Investigate the repository and assign a score from 0 to {max_score} points based on the levels above. Provide your score with detailed reasoning and evidence.
""".strip()


CHECKLIST_CRITERIA_TEMPLATE = """
Evaluate this repository against: **{criteria_name}**

### Checklist Items:
{checklist_items}

**Your task:** Check each item systematically and return the indices (0-based) of completed items. For example, if items 0, 2, and 3 are completed, return [0, 2, 3]. Provide reasoning for each decision.
""".strip()


def create_scored_criteria_prompt(criteria: ScoredCriteria) -> str:
    """Create user prompt for scored criteria"""
    score_levels_text = "\n".join([
        f"  {level.score} points: {level.description}" 
        for level in criteria.score_levels
    ])
    
    return SCORED_CRITERIA_TEMPLATE.format(
        criteria_name=criteria.name,
        score_levels=score_levels_text,
        max_score=criteria.max_score
    )


def create_checklist_criteria_prompt(criteria: ChecklistCriteria) -> str:
    """Create user prompt for checklist criteria"""
    items_text = "\n".join([
        f"  Item {i}: {item.description} ({item.points} points)"
        for i, item in enumerate(criteria.items)
    ])
    
    return CHECKLIST_CRITERIA_TEMPLATE.format(
        criteria_name=criteria.name,
        checklist_items=items_text
    )


def create_user_prompt(criteria: Union[ScoredCriteria, ChecklistCriteria]) -> str:
    """Create task-specific user prompt based on criteria type (compatibility function)"""
    if isinstance(criteria, ScoredCriteria):
        return create_scored_criteria_prompt(criteria)
    elif isinstance(criteria, ChecklistCriteria):
        return create_checklist_criteria_prompt(criteria)
    else:
        raise ValueError(f"Unknown criteria type: {type(criteria)}")


def create_evaluation_agent(model_string: str, analyzer_tools: AnalyzerTools, output_type) -> Agent:
    """Create a unified evaluation agent for both scored and checklist criteria"""
    
    tools = get_instance_methods(analyzer_tools)
    
    agent = Agent(
        model=model_string,
        tools=tools,
        output_type=output_type,
        system_prompt=SYSTEM_INSTRUCTIONS
    )
    
    return agent