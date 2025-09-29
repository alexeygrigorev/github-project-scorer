import asyncio
import inspect
from typing import List, Union, Dict
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.messages import (
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
)
from pydantic import BaseModel
from rich.console import Console
from rich.text import Text
from rich.panel import Panel

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


def create_evaluation_agent(model_string: str, file_analyzer: FileAnalyzer, output_type) -> Agent:
    """Create a unified evaluation agent for both scored and checklist criteria"""
    
    tools = get_instance_methods(file_analyzer)
    
    agent = Agent(
        model=model_string,
        output_type=output_type,
        tools=tools,
        system_prompt=SYSTEM_INSTRUCTIONS
    )
    
    return agent


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


class ProjectEvaluator:
    """Main evaluator that coordinates multiple agents"""

    def __init__(self, model_string: str, file_analyzer: FileAnalyzer):
        self.model_string = model_string
        self.file_analyzer = file_analyzer
        self.scored_agent = create_evaluation_agent(model_string, file_analyzer, ScoredCriteriaResult)
        self.checklist_agent = create_evaluation_agent(model_string, file_analyzer, ChecklistResult)
        self.usage_tracker = UsageTracker()
        # Configure console for better Windows compatibility  
        self.console = Console(force_terminal=True, legacy_windows=False)

    async def evaluate_criteria(
        self,
        criteria: Union[ScoredCriteria, ChecklistCriteria],
        context: AnalysisContext,
    ) -> EvaluationResult:
        """Evaluate a single criteria with streaming tool calls"""

        if isinstance(criteria, ScoredCriteria):
            # Create user prompt for scored criteria
            prompt = create_user_prompt(criteria, context)
            result = await self._run_agent_with_streaming(self.scored_agent, prompt)
            
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
            # Create user prompt for checklist criteria
            prompt = create_user_prompt(criteria, context)
            result = await self._run_agent_with_streaming(self.checklist_agent, prompt)
            
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

    async def _run_agent_with_streaming(self, agent: Agent, prompt: str):
        """Run agent with real-time streaming tool calls"""
        self.console.print("  🤖 [bold blue]Starting evaluation...[/bold blue]")
        
        async with agent.iter(prompt) as run:
            result = None
            async for node in run:
                if Agent.is_user_prompt_node(node):
                    # User prompt submitted
                    pass
                elif Agent.is_model_request_node(node):
                    # Model thinking/responding
                    self.console.print("  🧠 [bold yellow]Model analyzing...[/bold yellow]")
                    async with node.stream(run.ctx) as request_stream:
                        final_result_found = False
                        async for event in request_stream:
                            if isinstance(event, FinalResultEvent):
                                self.console.print("  ✨ [bold magenta]Generating final result...[/bold magenta]")
                                final_result_found = True
                                break
                        
                        if final_result_found:
                            # For structured output, we can't stream text but we can show progress
                            self.console.print("  📋 [bold cyan]Creating structured result...[/bold cyan]")
                                    
                elif Agent.is_call_tools_node(node):
                    # Tool usage
                    async with node.stream(run.ctx) as handle_stream:
                        async for event in handle_stream:
                            if isinstance(event, FunctionToolCallEvent):
                                # Tool emojis mapping
                                tool_emojis = {
                                    'get_file_stats': '📊',
                                    'find_files_by_name': '🔍',
                                    'read_file': '📖',
                                    'list_files': '📁',
                                    'grep_files': '🔎',
                                    'find_config_files': '⚙️',
                                    'check_file_exists': '✅',
                                }
                                
                                emoji = tool_emojis.get(event.part.tool_name, '🔧')
                                
                                # Format args for display
                                args_str = ""
                                if event.part.args:
                                    import json
                                    try:
                                        args_dict = json.loads(event.part.args)
                                        args_items = []
                                        for k, v in args_dict.items():
                                            if isinstance(v, str) and len(v) > 30:
                                                v = v[:30] + "..."
                                            args_items.append(f"[dim]{k}[/dim]={v}")
                                        args_str = f"([dim]{', '.join(args_items)}[/dim])"
                                    except:
                                        args_str = f"([dim]{event.part.args[:50]}...[/dim])"
                                
                                tool_text = Text(f"  {emoji} ")
                                tool_text.append(event.part.tool_name, style="bold green")
                                tool_text.append(args_str, style="dim")
                                self.console.print(tool_text)
                                
                            elif isinstance(event, FunctionToolResultEvent):
                                # Don't show result output - too verbose
                                pass
                                    
                elif Agent.is_end_node(node):
                    # Evaluation complete
                    assert run.result is not None
                    result = run.result
                    self.console.print("  ✅ [bold green]Evaluation complete![/bold green]")
                    
        return result

    def _display_tool_calls(self, criteria_name: str, result):
        """Legacy method - now replaced by streaming"""
        pass

    async def evaluate_project(
        self,
        criteria_list: List[Union[ScoredCriteria, ChecklistCriteria]],
        context: AnalysisContext,
    ) -> List[EvaluationResult]:
        """Evaluate all criteria for a project"""
        
        results = []
        total_criteria = len(criteria_list)
        
        for i, criteria in enumerate(criteria_list, 1):
            # Create a beautiful panel for each criteria
            panel = Panel(
                f"[bold]{criteria.name}[/bold]\n"
                f"[dim]Criteria {i} of {total_criteria}[/dim]",
                border_style="blue",
                title="🎯 Evaluating",
                title_align="left"
            )
            self.console.print(panel)
            
            try:
                result = await self.evaluate_criteria(criteria, context)
                results.append(result)
                
                # Show result summary
                score_color = "green" if result.score == result.max_score else "yellow" if result.score > 0 else "red"
                self.console.print(f"  🎯 [bold {score_color}]Score: {result.score}/{result.max_score}[/bold {score_color}]")
                self.console.print(f"  💭 [dim]{result.reasoning[:100]}{'...' if len(result.reasoning) > 100 else ''}[/dim]")
                self.console.print("")
                
            except Exception as e:
                self.console.print(f"  ❌ [bold red]Error evaluating {criteria.name}: {e}[/bold red]")
                
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
                self.console.print("")

        # Show final summary
        successful = len([r for r in results if r.score > 0])
        self.console.print(Panel(
            f"[bold green]✅ Evaluation complete![/bold green]\n"
            f"[dim]Successfully evaluated {successful}/{total_criteria} criteria[/dim]",
            border_style="green",
            title="🎉 Summary"
        ))
        
        return results