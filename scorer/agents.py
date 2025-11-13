import inspect
from typing import Union

from pydantic_ai import Agent

from scorer.models import ScoredCriteria, ChecklistCriteria
from scorer.analyzer_tools import AnalyzerTools


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
3. Search content across files ONLY when absolutely necessary
4. Gather concrete evidence and make your assessment
5. Provide detailed reasoning with specific examples

Tool Usage Guidelines:
- **get_project_summary()**: Use FIRST to get a high-level overview of the project
- **list_files()**: Use to see all files when you need the complete file list
- **read_file()**: Use to read specific files (README, config files, code files)
- **search_content(patterns)**: Use sparingly when searching patterns. Can accept a list of patterns to search multiple terms in ONE request
- **find_files_by_name(pattern)**: Use VERY SPARINGLY. Supports multiple patterns with | symbol (e.g., "README*|LICENSE*|*.md")

IMPORTANT: 
- Do NOT use find_files_by_name() repeatedly for the same purpose
- When searching for multiple file patterns, use | separator in ONE call: find_files_by_name("README*|*.md|LICENSE*")
- When searching for multiple content patterns, pass them as a list to search_content() in ONE call
- Use get_project_summary() or search_content() for better efficiency

For documentation criteria: 
- Read README.md directly with read_file("README.md")
- Check for visuals by looking at the file list from list_files()

For technical criteria:
- Use list_files() ONCE to understand project structure
- Read specific files based on what you see in the file list
- Only search across files when you must find patterns in multiple locations

Investigation Guidelines:
- One list_files() call shows you everything - use it wisely
- One file read is better than multiple file searches
- Don't search for files when you already have the complete file list
- Be evidence-based: Cite specific files, code snippets, or observations
- Don't over-investigate - sometimes the answer is obvious from the structure

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

    # If there's a comment, modify the score level descriptions to incorporate it
    score_levels_text_lines = []
    for level in criteria.score_levels:
        score_levels_text_lines.append(f"  {level.score} points: {level.description}")

    score_levels_text = "\n".join(score_levels_text_lines)

    # Add clarifying comment right after score levels if present
    if criteria.comment:
        score_levels_text += f"\n\n  IMPORTANT: {criteria.comment}"

    prompt = SCORED_CRITERIA_TEMPLATE.format(
        criteria_name=criteria.name,
        score_levels=score_levels_text,
        max_score=criteria.max_score,
    )

    return prompt


def create_checklist_criteria_prompt(criteria: ChecklistCriteria) -> str:
    """Create user prompt for checklist criteria"""
    items_text = "\n".join(
        [
            f"  Item {i}: {item.description} ({item.points} points)"
            for i, item in enumerate(criteria.items)
        ]
    )

    prompt = CHECKLIST_CRITERIA_TEMPLATE.format(
        criteria_name=criteria.name, checklist_items=items_text
    )

    # Add comment if present
    if criteria.comment:
        prompt += f"\n\n### Additional Guidelines:\n{criteria.comment}"

    return prompt


def create_user_prompt(criteria: Union[ScoredCriteria, ChecklistCriteria]) -> str:
    """Create task-specific user prompt based on criteria type (compatibility function)"""
    if isinstance(criteria, ScoredCriteria):
        return create_scored_criteria_prompt(criteria)
    elif isinstance(criteria, ChecklistCriteria):
        return create_checklist_criteria_prompt(criteria)
    else:
        raise ValueError(f"Unknown criteria type: {type(criteria)}")


def create_evaluation_agent(
    model_string: str, analyzer_tools: AnalyzerTools, output_type
) -> Agent:
    """Create a unified evaluation agent for both scored and checklist criteria"""

    tools = get_instance_methods(analyzer_tools)

    agent = Agent(
        model=model_string,
        tools=tools,
        output_type=output_type,
        system_prompt=SYSTEM_INSTRUCTIONS,
    )

    return agent
