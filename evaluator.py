import json
from typing import List, Union, Dict

from pydantic_ai import Agent
from pydantic_ai.messages import (
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
)
from rich.console import Console
from rich.text import Text
from rich.panel import Panel

from models import (
    ScoredCriteria,
    ChecklistCriteria,
    EvaluationResult,
    ScoredCriteriaResult,
    ChecklistResult,
)
from usage_tracker import UsageTracker

from agents import create_evaluation_agent, create_user_prompt
from analyzer_tools import AnalyzerTools

class ProjectEvaluator:
    """Main evaluator that coordinates multiple agents"""

    def __init__(self, model_string: str, analyzer_tools: AnalyzerTools):
        self.model_string = model_string
        self.analyzer_tools = analyzer_tools
        self.scored_agent = create_evaluation_agent(
            model_string, analyzer_tools, ScoredCriteriaResult
        )
        self.checklist_agent = create_evaluation_agent(
            model_string, analyzer_tools, ChecklistResult
        )
        self.usage_tracker = UsageTracker()
        self.console = Console(force_terminal=True, legacy_windows=False)

    async def evaluate_criteria(
        self, criteria: Union[ScoredCriteria, ChecklistCriteria]
    ) -> EvaluationResult:
        """Evaluate a single criteria with streaming tool calls"""

        # Choose the right agent and create prompt
        if isinstance(criteria, ScoredCriteria):
            agent = self.scored_agent
            prompt = create_user_prompt(criteria)
        elif isinstance(criteria, ChecklistCriteria):
            agent = self.checklist_agent
            prompt = create_user_prompt(criteria)
        else:
            raise ValueError(
                f"Unknown criteria type: {type(criteria)}. Expected ScoredCriteria or ChecklistCriteria."
            )

        # Run the agent
        result = await self._run_agent_with_streaming(agent, prompt)
        self._display_and_track_usage(result)

        # Calculate score based on criteria type
        if isinstance(criteria, ScoredCriteria):
            score = result.output.score
        elif isinstance(criteria, ChecklistCriteria):
            completed_items = result.output.completed_items
            score = sum(
                criteria.items[i].points
                for i in completed_items
                if i < len(criteria.items)
            )

        return EvaluationResult(
            criteria_name=criteria.name,
            criteria_type="scored" if isinstance(criteria, ScoredCriteria) else "checklist",
            score=score,
            max_score=criteria.max_score,
            reasoning=result.output.reasoning,
            evidence=result.output.evidence,
        )
    
    def _display_and_track_usage(self, result):
        # Track token usage and show cost
        if not hasattr(result, "usage"):
            return

        usage = result.usage()
        if usage is None:
            return

        self._display_cost(usage)
        self.usage_tracker.add_usage(
            model=self.model_string,
            usage=usage
        )


    def _display_cost(self, usage):
        temp_tracker = UsageTracker()
        temp_tracker.pricing = self.usage_tracker.pricing
        temp_tracker.add_usage(self.model_string, usage)
        criteria_cost = temp_tracker.calculate_cost()

        input_tokens = usage.input_tokens or 0
        output_tokens = usage.output_tokens or 0

        self.console.print(
            f"  💰 [dim]Tokens: {input_tokens:,} input + {output_tokens:,} output | Cost: ${criteria_cost:.4f}[/dim]"
        )


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
                    self.console.print(
                        "  🧠 [bold yellow]Model analyzing...[/bold yellow]"
                    )
                    async with node.stream(run.ctx) as request_stream:
                        final_result_found = False
                        async for event in request_stream:
                            if isinstance(event, FinalResultEvent):
                                self.console.print(
                                    "  ✨ [bold magenta]Generating final result...[/bold magenta]"
                                )
                                final_result_found = True
                                break

                        if final_result_found:
                            # For structured output, we can't stream text but we can show progress
                            self.console.print(
                                "  📋 [bold cyan]Creating structured result...[/bold cyan]"
                            )

                elif Agent.is_call_tools_node(node):
                    # Tool usage
                    async with node.stream(run.ctx) as handle_stream:
                        async for event in handle_stream:
                            if isinstance(event, FunctionToolCallEvent):
                                # Tool emojis mapping
                                tool_emojis = {
                                    # "get_file_stats": "📊",
                                    "find_files_by_name": "🔍",
                                    "read_file": "📖",
                                    "list_files": "📁",
                                    "grep_files": "🔎",
                                    # "find_config_files": "⚙️",
                                    # "check_file_exists": "✅",
                                }

                                emoji = tool_emojis.get(event.part.tool_name, "🔧")

                                # Format args for display
                                args_str = ""
                                if event.part.args:
                                    try:
                                        args_dict = json.loads(event.part.args)
                                        args_items = []
                                        for k, v in args_dict.items():
                                            if isinstance(v, str) and len(v) > 30:
                                                v = v[:30] + "..."
                                            args_items.append(f"{k}={v}")
                                        args_str = (
                                            f"({', '.join(args_items)})"
                                        )
                                    except:
                                        args_str = (
                                            f"({event.part.args[:50]}...)"
                                        )

                                tool_text = Text(f"  {emoji} ")
                                tool_text.append(
                                    event.part.tool_name, style="bold green"
                                )
                                tool_text.append(args_str, style="dim")
                                self.console.print(tool_text)

                            elif isinstance(event, FunctionToolResultEvent):
                                # Don't show result output - too verbose
                                pass

                elif Agent.is_end_node(node):
                    # Evaluation complete
                    assert run.result is not None
                    result = run.result
                    self.console.print(
                        "  ✅ [bold green]Evaluation complete![/bold green]"
                    )

        return result


    async def evaluate_project(
        self,
        criteria_list: List[Union[ScoredCriteria, ChecklistCriteria]],
    ) -> List[EvaluationResult]:
        """Evaluate all criteria for a project"""

        results = []
        total_criteria = len(criteria_list)

        for i, criteria in enumerate(criteria_list, 1):
            details_str = ""
            if isinstance(criteria, ScoredCriteria):
                details_str = "Score levels:\n"
                for level in criteria.score_levels:
                    details_str += f"  • {level.score}: {level.description}\n"
            elif isinstance(criteria, ChecklistCriteria):
                details_str = f"Checklist items ({len(criteria.items)} total):\n"
                for item in criteria.items:
                    details_str += f"  • {item.description} ({item.points} pts)\n"
            
            # Create a beautiful panel for each criteria
            panel_content = (f"[bold]{criteria.name}[/bold]\n"
                           f"Criteria {i} of {total_criteria}\n\n"
                           f"{details_str.rstrip()}")
            
            panel = Panel(
                panel_content,
                border_style="blue",
                title="🎯 Evaluating",
                title_align="left"
            )

            self.console.print(panel)

            try:
                result = await self.evaluate_criteria(criteria)
                results.append(result)

                # Show result summary
                score_color = (
                    "green"
                    if result.score == result.max_score
                    else "yellow"
                    if result.score > 0
                    else "red"
                )
                self.console.print(
                    f"  🎯 [bold {score_color}]Score: {result.score}/{result.max_score}[/bold {score_color}]"
                )
                self.console.print(
                    f"  💭 [dim]{result.reasoning[:100]}{'...' if len(result.reasoning) > 100 else ''}[/dim]"
                )
                self.console.print("")

            except Exception as e:
                self.console.print(
                    f"  ❌ [bold red]Error evaluating {criteria.name}: {e}[/bold red]"
                )

                # Create a failed result
                results.append(
                    EvaluationResult(
                        criteria_name=criteria.name,
                        criteria_type=getattr(criteria, "type", "scored"),
                        score=0,
                        max_score=getattr(criteria, "max_score", 0),
                        reasoning=f"Evaluation failed: {e}",
                        evidence=[],
                    )
                )
                self.console.print("")

        # Show final summary
        successful = len([r for r in results if r.score > 0])
        self.console.print(
            Panel(
                f"[bold green]✅ Evaluation complete![/bold green]\n"
                f"[dim]Successfully evaluated {successful}/{total_criteria} criteria[/dim]",
                border_style="green",
                title="🎉 Summary",
            )
        )

        return results
