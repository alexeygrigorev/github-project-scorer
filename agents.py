import inspect
from typing import Union

from pydantic_ai import Agent

from models import ScoredCriteria, ChecklistCriteria
from file_analyzer import FileAnalyzer


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

## Evaluation Strategy

1. Start Smart: For documentation-focused criteria (problem description, setup instructions), start with README and documentation files
2. Be Proportional: Match investigation depth to criteria complexity - simple criteria need simple evidence
3. Read Documentation: Find and read README files, documentation, and project descriptions  
4. Examine Code: For technical criteria, look at source files to understand implementation quality
5. Check Configuration: For setup/deployment criteria, review build files and configurations
6. Look for Evidence: Find specific examples that support your decision

## Investigation Guidelines

- Start with the obvious: For "problem description" → check README first, other docs second
- Be efficient: Don't over-investigate simple criteria that can be answered from documentation  
- Scale complexity: Simple criteria = quick investigation, complex criteria = thorough analysis
- Focus on relevance: Only examine files directly related to the criteria being evaluated

## Scoring Guidelines

- Be thorough but proportional: Don't rush to conclusions, but match effort to criteria complexity
- Be evidence-based: Your reasoning must cite specific files, code snippets, or observations
- Be fair: Consider the project's scope and purpose when evaluating
- Be specific: Provide concrete examples from the repository to justify your decision

## Investigation Process

1. First, understand what you're looking for based on the criteria
2. Plan your investigation strategy (which files to check, what to search for)
3. Use tools systematically to gather evidence - tool docstrings will guide you on usage
4. Cross-reference findings across multiple files when necessary
5. Form a conclusion based on comprehensive but proportional analysis

## Your Task

1. Investigate systematically using the available file analysis tools
2. Gather concrete evidence from files, code, documentation, and configuration
3. Make your assessment based on the criteria provided (score for scored criteria, completed item indices for checklists)
4. Provide detailed reasoning explaining your decision with specific examples
5. Document evidence with file names and relevant content that proves your assessment

Remember: The quality of your evaluation depends on the depth of your investigation. Don't accept surface-level observations, but also don't over-investigate simple criteria that can be answered quickly.
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


def create_evaluation_agent(model_string: str, analyzer_tools: FileAnalyzer, output_type) -> Agent:
    """Create a unified evaluation agent for both scored and checklist criteria"""
    
    tools = get_instance_methods(analyzer_tools)
    
    agent = Agent(
        model=model_string,
        tools=tools,
        output_type=output_type,
        system_prompt=SYSTEM_INSTRUCTIONS
    )
    
    return agent