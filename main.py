import os
import sys

# Set UTF-8 encoding for Windows compatibility
if sys.platform == "win32":
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

import asyncio
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

from models import load_criteria_from_yaml, ProjectEvaluation
from repository_manager import RepositoryManager
from github_analyzer_tools import GithubAnalyzerTools
from report_generator import ReportGenerator, ImprovementGenerator
from evaluator import ProjectEvaluator


# Load environment variables
load_dotenv()


class GitHubProjectScorer:
    """Main orchestrator for GitHub project evaluation"""
    
    def __init__(self, model: str = "openai:gpt-4o-mini"):
        """
        Initialize the scorer
        
        Args:
            model: Model string (e.g., "openai:gpt-4o-mini", "anthropic:claude-3-sonnet-20240229")
        """
        self.model = model
        self.report_generator = ReportGenerator()
        self.improvement_generator = ImprovementGenerator()
    
    async def evaluate_repository(self,
                                repo_url: str,
                                criteria_path: Path,
                                output_dir: Optional[Path] = None,
                                cleanup: bool = True) -> ProjectEvaluation:
        """
        Evaluate a GitHub repository against criteria
        
        Args:
            repo_url: GitHub repository URL
            criteria_path: Path to YAML criteria file
            output_dir: Directory to save reports (optional)
            cleanup: Whether to cleanup cloned repository
            
        Returns:
            ProjectEvaluation results
        """
        
        print(f"Starting evaluation of: {repo_url}")
        
        # Load criteria
        print("Loading evaluation criteria...")
        criteria_list = load_criteria_from_yaml(criteria_path)
        print(f"Loaded {len(criteria_list)} criteria")
        
        # Setup repository manager
        repo_manager = RepositoryManager()
        
        try:
            # Clone repository
            print("Cloning repository...")
            repo_path = repo_manager.clone_repository(repo_url)

            # Evaluate criteria
            print("Starting evaluation...")
            analyzer_tools = GithubAnalyzerTools(repo_path)
            evaluator = ProjectEvaluator(self.model, analyzer_tools)
            results = await evaluator.evaluate_project(criteria_list)

            # Calculate totals
            total_score = sum(result.score for result in results)
            max_total_score = sum(result.max_score for result in results)

            # Generate improvements
            improvements = self.improvement_generator.generate_improvements(results)
            
            # Create evaluation object
            evaluation = ProjectEvaluation(
                project_url=repo_url,
                project_path=repo_path,
                total_score=total_score,
                max_total_score=max_total_score,
                results=results,
                improvements=improvements
            )
            
            # Generate reports
            print("\nGenerating report...")
            self.report_generator.generate_console_report(evaluation)
            
            # Save report to file if output directory specified
            if output_dir:
                output_dir = Path(output_dir)
                output_dir.mkdir(exist_ok=True)
                
                # Create safe filename from repo URL
                repo_name = repo_url.split('/')[-1].replace('.git', '')
                report_path = output_dir / f"{repo_name}_evaluation_report"
                
                self.report_generator.save_report(evaluation, report_path, "markdown")
            
            return evaluation, evaluator.usage_tracker
            
        finally:
            if cleanup:
                repo_manager.cleanup()

    
    async def evaluate_multiple_repositories(self,
                                           repo_urls: List[str],
                                           criteria_path: Path,
                                           output_dir: Optional[Path] = None) -> List[ProjectEvaluation]:
        """Evaluate multiple repositories"""
        
        evaluations = []
        for repo_url in repo_urls:
            try:
                evaluation, usage_tracker = await self.evaluate_repository(repo_url, criteria_path, output_dir)
                evaluations.append(evaluation)
            except Exception as e:
                print(f"Error evaluating {repo_url}: {e}")
        
        return evaluations


async def interactive_main():
    """Interactive version that asks user for input"""
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel
    import os
    
    console = Console()
    
    # Welcome message
    console.print(Panel.fit(
        "[bold blue]GitHub Project Scorer[/bold blue]\n"
        "[white]Interactive evaluation of GitHub repositories against custom criteria[/white]",
        border_style="blue"
    ))
    
    # Get repository URL
    console.print("\n[bold yellow]Step 1: Repository Configuration[/bold yellow]")
    repo_url = Prompt.ask(
        "[cyan]Enter GitHub repository URL[/cyan]",
        default="https://github.com/pydantic/pydantic-ai"
    )
    
    # Get criteria file
    console.print("\n[bold yellow]Step 2: Criteria Configuration[/bold yellow]")
    criteria_options = [
        ("criteria.yaml", "Default criteria (RAG/LLM project focused)"),
        ("example_criteria.yaml", "Example criteria (general software quality)"),
        ("custom", "Specify custom criteria file path")
    ]
    
    console.print("Available criteria files:")
    for i, (file, desc) in enumerate(criteria_options, 1):
        if file != "custom":
            exists = "[green]YES[/green]" if Path(file).exists() else "[red]NO[/red]"
            console.print(f"  {i}. {exists} {file} - {desc}")
        else:
            console.print(f"  {i}. {desc}")
    
    criteria_choice = Prompt.ask(
        "[cyan]Choose criteria file[/cyan]",
        choices=["1", "2", "3"],
        default="1"
    )
    
    if criteria_choice == "1":
        criteria_path = Path("criteria.yaml")
    elif criteria_choice == "2":
        criteria_path = Path("example_criteria.yaml")
    else:
        custom_path = Prompt.ask("[cyan]Enter path to custom criteria file[/cyan]")
        criteria_path = Path(custom_path)
    
    if not criteria_path.exists():
        console.print(f"[red]ERROR: Criteria file not found: {criteria_path}[/red]")
        return
    
    # Get model configuration
    console.print("\n[bold yellow]Step 3: AI Model Configuration[/bold yellow]")
    
    # Check for existing API keys
    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    
    available_providers = []
    if openai_key:
        available_providers.append(("openai", "OpenAI (API key detected)"))
    if anthropic_key:
        available_providers.append(("anthropic", "Anthropic (API key detected)"))
    
    if not available_providers:
        console.print("[red]ERROR: No API keys detected![/red]")
        console.print("Please set one of the following environment variables:")
        console.print("  - OPENAI_API_KEY=your-openai-key")
        console.print("  - ANTHROPIC_API_KEY=your-anthropic-key")
        return
    
    if len(available_providers) == 1:
        model_provider = available_providers[0][0]
        console.print(f"[green]Using {available_providers[0][1]}[/green]")
    else:
        console.print("Available AI providers:")
        for i, (provider, desc) in enumerate(available_providers, 1):
            console.print(f"  {i}. {desc}")
        
        provider_choice = Prompt.ask(
            "[cyan]Choose AI provider[/cyan]",
            choices=[str(i) for i in range(1, len(available_providers) + 1)],
            default="1"
        )
        model_provider = available_providers[int(provider_choice) - 1][0]
    
    # Get model name
    if model_provider == "openai":
        model_options = ["gpt-4o-mini", "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
        default_model = "gpt-4o-mini"
    else:
        model_options = ["claude-3-5-sonnet-20241022", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
        default_model = "claude-3-5-sonnet-20241022"
    
    console.print(f"\nAvailable {model_provider} models:")
    for i, model in enumerate(model_options, 1):
        console.print(f"  {i}. {model}")
    
    model_choice = Prompt.ask(
        "[cyan]Choose model[/cyan]",
        choices=[str(i) for i in range(1, len(model_options) + 1)],
        default="1"
    )
    model_name = model_options[int(model_choice) - 1]
    
    # Get output configuration
    console.print("\n[bold yellow]Step 4: Output Configuration[/bold yellow]")
    
    save_report = Confirm.ask("[cyan]Save detailed report to file?[/cyan]", default=True)
    
    if save_report:
        output_dir = Prompt.ask(
            "[cyan]Output directory for reports[/cyan]",
            default="./reports"
        )
        output_path = Path(output_dir)
    else:
        output_path = None
    
    cleanup_repo = Confirm.ask("[cyan]Clean up cloned repository after evaluation?[/cyan]", default=True)
    
    # Summary
    console.print("\n[bold yellow]Configuration Summary[/bold yellow]")
    console.print(f"Repository: {repo_url}")
    console.print(f"📋 Criteria: {criteria_path}")
    console.print(f"🤖 Model: {model_provider}/{model_name}")
    console.print(f"💾 Save report: {'Yes' if save_report else 'No'}")
    if save_report:
        console.print(f"📂 Output dir: {output_path}")
    console.print(f"🧹 Cleanup: {'Yes' if cleanup_repo else 'No'}")
    
    if not Confirm.ask("\n[cyan]Proceed with evaluation?[/cyan]", default=True):
        console.print("[yellow]Evaluation cancelled.[/yellow]")
        return
    
    # Run evaluation
    console.print("\n[bold green]Starting Evaluation...[/bold green]")
    
    try:
        scorer = GitHubProjectScorer(
            model_provider=model_provider,
            model_name=model_name
        )
        
        evaluation, usage_tracker = await scorer.evaluate_repository(
            repo_url=repo_url,
            criteria_path=criteria_path,
            output_dir=output_path,
            cleanup=cleanup_repo
        )
        
        console.print(f"\n[bold green]Evaluation completed![/bold green]")
        console.print(f"[bold]Final score: {evaluation.total_score}/{evaluation.max_total_score} "
                     f"({evaluation.total_score/evaluation.max_total_score*100:.1f}%)[/bold]")
        
        # Show usage and cost summary
        if usage_tracker:
            usage_summary = usage_tracker.format_cost_summary()
            console.print(usage_summary)
        
        if evaluation.improvements:
            console.print(f"\n[yellow]Found {len(evaluation.improvements)} improvement suggestions[/yellow]")
        
    except Exception as e:
        console.print(f"\n[red]Error during evaluation: {e}[/red]")


async def cli_main():
    """Original CLI version"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GitHub Project Scorer")
    parser.add_argument("repo_url", help="GitHub repository URL")
    parser.add_argument("--criteria", default="criteria.yaml", help="Path to criteria YAML file")
    parser.add_argument("--output", help="Output directory for reports")
    parser.add_argument("--model", default="openai:gpt-4o-mini")
    parser.add_argument("--no-cleanup", action="store_true", help="Don't cleanup cloned repository")
    
    args = parser.parse_args()
    
    # Initialize scorer
    scorer = GitHubProjectScorer(model=args.model)

    # Run evaluation
    evaluation, usage_tracker = await scorer.evaluate_repository(
        repo_url=args.repo_url,
        criteria_path=Path(args.criteria),
        output_dir=Path(args.output) if args.output else None,
        cleanup=not args.no_cleanup
    )
    
    print(f"\nEvaluation completed! Final score: {evaluation.total_score}/{evaluation.max_total_score}")
    
    # Show usage and cost summary for CLI mode too
    if usage_tracker:
        usage_summary = usage_tracker.format_cost_summary()
        print(usage_summary)


async def main():
    """Main entry point - choose between interactive and CLI modes"""
    import sys
    
    # If arguments provided, use CLI mode
    if len(sys.argv) > 1:
        await cli_main()
    else:
        await interactive_main()


if __name__ == "__main__":
    asyncio.run(main())
