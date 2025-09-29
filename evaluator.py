from typing import List, Union

from pydantic_ai.messages import (
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
)
from rich.console import Console
from rich.text import Text
from rich.panel import Panel

from models import ScoredCriteria, ChecklistCriteria, EvaluationResult
from models import ScoredCriteriaResult, ChecklistResult

from github_analyzer_tools import GithubAnalyzerTools
from usage_tracker import UsageTracker
from agent_factory import AnalysisContext, create_evaluation_agent, create_user_prompt


class ProjectEvaluator:
    """Main class for evaluating projects against criteria with beautiful Rich display"""
    
    def __init__(self, model_string: str, file_analyzer: GithubAnalyzerTools):
        self.model_string = model_string
        self.file_analyzer = file_analyzer
        self.usage_tracker = UsageTracker()
        self.console = Console()
        
        # Create agents for different criteria types
        self.scored_agent = create_evaluation_agent(model_string, file_analyzer, ScoredCriteriaResult)
        self.checklist_agent = create_evaluation_agent(model_string, file_analyzer, ChecklistResult)

    async def evaluate_criteria(self, criteria: Union[ScoredCriteria, ChecklistCriteria], context: AnalysisContext) -> EvaluationResult:
        """Evaluate a single criteria against the repository"""
        
        if isinstance(criteria, ScoredCriteria):
            # Create user prompt for scored criteria
            prompt = create_user_prompt(criteria)
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
            prompt = create_user_prompt(criteria)
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

    async def _run_agent_with_streaming(self, agent, prompt: str):
        """Run agent with real-time streaming tool calls"""
        self.console.print("  🤖 [bold blue]Starting evaluation...[/bold blue]")
        
        async with agent.iter(prompt) as run:
            result = None
            async for node in run:
                if isinstance(node, FinalResultEvent):
                    result = node
                    self.console.print("  ✅ [bold green]Evaluation complete![/bold green]")
                    break
                    
                elif isinstance(node, FunctionToolCallEvent):
                    # Map tool names to emojis for better visual feedback
                    tool_emojis = {
                        "read_file": "📖",
                        "list_files": "📁", 
                        "search_files": "🔍",
                        "get_config_files": "⚙️",
                        "get_file_stats": "📊",
                    }
                    
                    emoji = tool_emojis.get(node.part.tool_name, "🔧")
                    
                    if node.part.args:
                        import json
                        try:
                            args_dict = json.loads(node.part.args)
                            args_items = []
                            for k, v in args_dict.items():
                                if isinstance(v, str) and len(v) > 30:
                                    v = v[:30] + "..."
                                args_items.append(f"{k}={v}")
                            args_str = f"({', '.join(args_items)})"
                        except:
                            args_str = f"({node.part.args[:50]}...)"
                    
                    tool_text = Text(f"  {emoji} ")
                    tool_text.append(node.part.tool_name, style="bold green")
                    tool_text.append(args_str, style="dim")
                    self.console.print(tool_text)
                    
                elif isinstance(node, FunctionToolResultEvent):
                    # Don't show result output - too verbose
                    pass
                        
        return result

    async def evaluate_all_criteria(self, criteria_list: List[Union[ScoredCriteria, ChecklistCriteria]], context: AnalysisContext) -> List[EvaluationResult]:
        """Evaluate all criteria with beautiful Rich display"""
        
        results = []
        total_criteria = len(criteria_list)
        
        for i, criteria in enumerate(criteria_list, 1):
            # Build criteria details string
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
                result = await self.evaluate_criteria(criteria, context)
                results.append(result)
                
                # Show result summary
                score_color = "green" if result.score == result.max_score else "yellow" if result.score > 0 else "red"
                self.console.print(f"  🎯 [bold {score_color}]Score: {result.score}/{result.max_score}[/bold {score_color}]")
                
                # Show full reasoning and evidence in a panel
                result_panel_content = f"[bold]Reasoning:[/bold]\n{result.reasoning}"
                if result.evidence:
                    result_panel_content += f"\n\n[bold]Evidence:[/bold]\n{result.evidence}"
                
                result_panel = Panel(
                    result_panel_content,
                    border_style="green" if result.score == result.max_score else "yellow" if result.score > 0 else "red",
                    title="📋 Result Details",
                    title_align="left"
                )
                self.console.print(result_panel)
                self.console.print("")
                
            except Exception as e:
                self.console.print(f"  ❌ [bold red]Error evaluating {criteria.name}: {e}[/bold red]")
                
        # Show final summary
        successful = len([r for r in results if r.score > 0])
        self.console.print(Panel(
            f"[bold green]✅ Evaluation complete![/bold green]\n"
            f"Successfully evaluated {successful}/{total_criteria} criteria",
            border_style="green",
            title="🎉 Summary"
        ))
        
        return results