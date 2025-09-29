import asyncio
import inspect
from typing import List, Union, Dict
from pathlib import Path

from pydantic_ai import Agent
from pydantic import BaseModel

from models import ScoredCriteria, ChecklistCriteria, EvaluationResult, ScoredCriteriaResult, ChecklistResult
from file_analyzer import FileAnalyzer
from usage_tracker import UsageTracker


class AnalysisContext(BaseModel):
    """Context passed to evaluation agents"""

    repo_path: Path
    file_analyzer: FileAnalyzer
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


def create_scored_criteria_agent(model_string: str, file_analyzer: FileAnalyzer) -> Agent:
    """Create an agent for evaluating scored criteria"""
    
    tools = get_instance_methods(file_analyzer)
    
    instructions = """You are an expert software engineer and technical evaluator specializing in assessing GitHub repositories against specific quality criteria.

Your mission is to thoroughly evaluate a GitHub repository and assign an accurate score based on the provided criteria and scoring levels.

## Your Capabilities

You have access to powerful file analysis tools:
- `list_files(extensions=None, exclude_patterns=None, max_files=1000)`: List files by extension or pattern
- `read_file(file_path, max_lines=1000)`: Read and examine file contents (use relative paths from repo root)
- `grep_files(pattern, extensions=None, max_results=100)`: Search for text patterns across files
- `find_config_files()`: Discover configuration files (requirements.txt, package.json, etc.)
- `find_files_by_name(pattern)`: Find files by name pattern (e.g., "README*", "*.yml")
- `check_file_exists(filename)`: Check if specific files exist
- `get_file_stats()`: Get repository statistics (file counts by type)

**Important**: Use relative paths from repository root (e.g., "notebooks/example.ipynb", not full paths).
For .ipynb files, read_file automatically converts notebooks to markdown format with cleared outputs.

## Evaluation Strategy

1. **Start with Overview**: Use `get_file_stats()` and `find_config_files()` to understand the project structure
2. **Read Documentation**: Find and read README files, documentation, and project descriptions
3. **Examine Code**: Look at source files to understand implementation quality, patterns, and practices
4. **Check Configuration**: Review build files, dependencies, testing setup, CI/CD configurations
5. **Look for Evidence**: Find specific examples that support your scoring decision

## Scoring Guidelines

- **Be thorough**: Don't rush to conclusions. Investigate multiple files and aspects
- **Be evidence-based**: Your reasoning must cite specific files, code snippets, or observations
- **Be fair**: Consider the project's scope and purpose when evaluating
- **Be specific**: Provide concrete examples from the repository to justify your score

## Investigation Process

1. First, understand what you're looking for based on the criteria
2. Plan your investigation strategy (which files to check, what to search for)
3. Use tools systematically to gather evidence
4. Cross-reference findings across multiple files
5. Form a conclusion based on comprehensive analysis

Remember: The quality of your evaluation depends on the depth of your investigation. Don't accept surface-level observations—dig deeper to find the truth about the repository's quality."""

    scored_agent = Agent(
        model=model_string,
        output_type=ScoredCriteriaResult,
        tools=tools,
        instructions=instructions
    )
    
    return scored_agent


def create_checklist_agent(model_string: str, file_analyzer: FileAnalyzer) -> Agent:
    """Create an agent for evaluating checklist criteria"""
    
    tools = get_instance_methods(file_analyzer)
    
    instructions = """You are an expert software engineer and technical auditor specializing in systematic checklist evaluations of GitHub repositories.

Your mission is to methodically verify each checklist item and determine which ones are completed or present in the repository.

## Your Capabilities

You have access to powerful file analysis tools:
- `list_files(extensions=None, exclude_patterns=None, max_files=1000)`: List files by extension or pattern
- `read_file(file_path, max_lines=1000)`: Read and examine file contents (use relative paths from repo root)
- `grep_files(pattern, extensions=None, max_results=100)`: Search for text patterns across files
- `find_config_files()`: Discover configuration files (requirements.txt, package.json, etc.)
- `find_files_by_name(pattern)`: Find files by name pattern (e.g., "README*", "*.yml")
- `check_file_exists(filename)`: Check if specific files exist
- `get_file_stats()`: Get repository statistics (file counts by type)

**Important**: Use relative paths from repository root (e.g., "notebooks/example.ipynb", not full paths).
For .ipynb files, read_file automatically converts notebooks to markdown format with cleared outputs.

## Evaluation Strategy

For each checklist item, follow this systematic approach:

1. **Understand the Requirement**: Clearly interpret what the checklist item is asking for
2. **Plan Investigation**: Determine which files or patterns might contain evidence
3. **Search Methodically**: Use appropriate tools to look for evidence
4. **Verify Thoroughly**: Don't just check for existence—verify quality and completeness
5. **Document Evidence**: Record specific findings that prove the item is completed

## Investigation Guidelines

- **Be systematic**: Check each item independently and thoroughly
- **Look for standards**: Consider industry best practices for each requirement
- **Check multiple sources**: Don't rely on a single file or indicator
- **Consider context**: Evaluate requirements appropriate to the project type and size
- **Be precise**: Only mark items as completed if they truly meet the requirement

## Common Investigation Patterns

- **Documentation**: Look for README files, docs folders, inline comments
- **Testing**: Search for test files, test commands in package.json/Makefile, CI configs
- **Dependencies**: Check package.json, requirements.txt, go.mod, etc.
- **Build/Deploy**: Look for Dockerfile, CI/CD configs, build scripts
- **Code Quality**: Search for linting configs, type checking, code formatting tools
- **Security**: Check for dependency scanning, security configs, proper authentication

## Verification Process

1. For each checklist item, start with the most likely locations
2. Use file existence checks first, then examine contents
3. Search for keywords and patterns related to the requirement
4. Validate that found items actually fulfill the requirement (not just exist)
5. Cross-reference evidence across multiple files when possible

Remember: Only mark an item as completed if you have clear, verifiable evidence. When in doubt, investigate further before making a decision."""

    checklist_agent = Agent(
        model=model_string,
        output_type=ChecklistResult,
        tools=tools,
        instructions=instructions
    )
    
    return checklist_agent


class ProjectEvaluator:
    """Main evaluator that coordinates multiple agents"""

    def __init__(self, model_string: str, file_analyzer: FileAnalyzer):
        self.model_string = model_string
        self.file_analyzer = file_analyzer
        self.scored_agent = create_scored_criteria_agent(model_string, file_analyzer)
        self.checklist_agent = create_checklist_agent(model_string, file_analyzer)
        self.usage_tracker = UsageTracker()

    async def evaluate_criteria(
        self,
        criteria: Union[ScoredCriteria, ChecklistCriteria],
        context: AnalysisContext,
    ) -> EvaluationResult:
        """Evaluate a single criteria"""

        if isinstance(criteria, ScoredCriteria):
            # Create enhanced prompt for scored criteria
            prompt = self._create_scored_prompt(criteria, context)
            result = await self.scored_agent.run(prompt)
            
            # Display tool calls for transparency
            self._display_tool_calls(criteria.name, result)
            
            # Track token usage if available
            if hasattr(result, 'usage') and result.usage() is not None:
                usage = result.usage()
                self.usage_tracker.add_usage(
                    model=self.model_string,
                    input_tokens=usage.input_tokens or 0,
                    output_tokens=usage.output_tokens or 0
                )
            
            return EvaluationResult(
                criteria_name=criteria.name,
                criteria_type="scored",
                score=result.output.score,
                max_score=criteria.max_score,
                reasoning=result.output.reasoning,
                evidence=result.output.evidence,
            )

        elif isinstance(criteria, ChecklistCriteria):
            # Create enhanced prompt for checklist criteria
            prompt = self._create_checklist_prompt(criteria, context)
            result = await self.checklist_agent.run(prompt)
            
            # Display tool calls for transparency
            self._display_tool_calls(criteria.name, result)
            
            # Track token usage if available
            if hasattr(result, 'usage') and result.usage() is not None:
                usage = result.usage()
                self.usage_tracker.add_usage(
                    model=self.model_string,
                    input_tokens=usage.input_tokens or 0,
                    output_tokens=usage.output_tokens or 0
                )
            
            completed_items = result.output.completed_items
            score = sum(
                criteria.items[i].points
                for i in completed_items
                if i < len(criteria.items)
            )

            return EvaluationResult(
                criteria_name=criteria.name,
                criteria_type="checklist",
                score=score,
                max_score=criteria.max_score,
                reasoning=result.output.reasoning,
                evidence=result.output.evidence,
            )

        else:
            raise ValueError(f"Unknown criteria type: {type(criteria)}. Expected ScoredCriteria or ChecklistCriteria.")

    def _display_tool_calls(self, criteria_name: str, result):
        """Display tool calls for transparency"""
        try:
            messages = result.new_messages()
            tool_calls = {}
            
            for message in messages:
                for part in message.parts:
                    kind = part.part_kind
                    
                    if kind == "tool-call":
                        call_id = part.tool_call_id
                        tool_calls[call_id] = part
                        args_str = ""
                        if hasattr(part, 'args') and part.args:
                            args_str = f"({part.args})"
                        print(f"  Tool call: {part.tool_name}{args_str}")
                    
                    elif kind == "tool-return":
                        call_id = part.tool_call_id
                        if call_id in tool_calls:
                            call = tool_calls[call_id]
                            print(f"  Tool result: {call.tool_name} completed")
        
        except Exception:
            # Don't let tool call display errors break the evaluation
            pass

    def _create_scored_prompt(self, criteria: ScoredCriteria, context: AnalysisContext) -> str:
        """Create comprehensive prompt for scored criteria evaluation"""
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
1. **Investigate thoroughly** using the available file analysis tools
2. **Gather concrete evidence** from files, code, documentation, and configuration
3. **Assign a score** from 0 to {criteria.max_score} based on the scoring levels
4. **Provide detailed reasoning** explaining your score with specific examples
5. **List evidence** with file names and relevant content snippets

### Investigation Guidelines:
- Start by understanding the project structure and purpose
- Look for relevant files, code patterns, and documentation
- Consider the quality, completeness, and implementation of what you find
- Base your score on objective evidence, not assumptions
- Be thorough but efficient in your analysis

Begin your evaluation by planning which files and aspects to investigate, then systematically gather evidence to support your scoring decision."""

    def _create_checklist_prompt(self, criteria: ChecklistCriteria, context: AnalysisContext) -> str:
        """Create comprehensive prompt for checklist criteria evaluation"""
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

### Verification Guidelines:
- Check each item independently and thoroughly
- Look for actual implementation, not just mentions or placeholders
- Consider industry best practices for what constitutes "completion"
- Verify quality and completeness, not just existence
- Only mark items as completed if you have clear evidence

### Investigation Strategy:
1. Plan which files/locations are most likely to contain evidence for each item
2. Use systematic searches and file examinations
3. Cross-reference findings across multiple sources when possible
4. Validate that found items actually meet the requirement standards
5. Document your findings with specific file references

Begin by analyzing the project structure, then systematically verify each checklist item with concrete evidence."""

    async def evaluate_project(
        self,
        criteria_list: List[Union[ScoredCriteria, ChecklistCriteria]],
        context: AnalysisContext,
    ) -> List[EvaluationResult]:
        """Evaluate all criteria for a project"""
        
        results = []
        total_criteria = len(criteria_list)
        
        for i, criteria in enumerate(criteria_list, 1):
            print(f"\nEvaluating criteria {criteria.name} ({i}/{total_criteria})")
            
            try:
                result = await self.evaluate_criteria(criteria, context)
                results.append(result)
                
                print(f"End result: {result.score}/{result.max_score}")
                print(f"Short justification: {result.reasoning[:100]}{'...' if len(result.reasoning) > 100 else ''}")
                
            except Exception as e:
                print(f"Error evaluating {criteria.name}: {e}")
                
                # Create a failed result
                results.append(
                    EvaluationResult(
                        criteria_name=criteria.name,
                        criteria_type=getattr(criteria, 'type', 'scored'),
                        score=0,
                        max_score=getattr(criteria, "max_score", 0),
                        reasoning=f"Evaluation failed: {e}",
                        evidence=[],
                    )
                )
                
                print(f"End result: 0/{getattr(criteria, 'max_score', 0)} (failed)")

        print(f"\nEvaluation complete: {len([r for r in results if r.score > 0])}/{total_criteria} successful")
        
        return results