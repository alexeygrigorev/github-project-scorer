import os
import asyncio
import argparse

from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from rich.console import Console
import questionary

from models import load_criteria_from_yaml, ProjectEvaluation
from repository_manager import RepositoryManager
from analyzer_tools import AnalyzerTools
from evaluator import ProjectEvaluator
from report_generator import ReportGenerator, ImprovementGenerator


# Load environment variables
load_dotenv()


class GitHubProjectScorer:
    """Main orchestrator for GitHub project evaluation"""
    
    def __init__(self, 
                 model_provider: str = "openai",
                 model_name: str = "gpt-4o-mini",
                 api_key: Optional[str] = None):
        """
        Initialize the scorer
        
        Args:
            model_provider: "openai" or "anthropic"
            model_name: Model name (e.g., "gpt-4o-mini", "claude-3-sonnet-20240229")
            api_key: API key (if None, will use environment variables)
        """
        
        # Build model string for pydantic-ai
        if model_provider.lower() == "openai":
            self.model_string = f"openai:{model_name}"
        elif model_provider.lower() == "anthropic":
            self.model_string = f"anthropic:{model_name}"
        else:
            raise ValueError(f"Unsupported model provider: {model_provider}")
        
        # Set API key if provided
        if api_key:
            if model_provider.lower() == "openai":
                os.environ["OPENAI_API_KEY"] = api_key
            elif model_provider.lower() == "anthropic":
                os.environ["ANTHROPIC_API_KEY"] = api_key
        
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
            
            # Setup file analyzer and evaluator
            print("Analyzing repository structure...")
            analyzer_tools = AnalyzerTools(repo_path)
            evaluator = ProjectEvaluator(self.model_string, analyzer_tools)

            # Evaluate criteria
            print("Starting evaluation...")
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


def cli_main():
    """CLI version with smart prompting for missing arguments"""
    
    parser = argparse.ArgumentParser(description="GitHub Project Scorer")
    parser.add_argument("repo_url", nargs='?', help="GitHub repository URL")
    parser.add_argument("--criteria", help="Path to criteria YAML file")
    parser.add_argument("--output", help="Output directory for reports")
    parser.add_argument("--model-provider", default="openai", choices=["openai", "anthropic"])
    parser.add_argument("--model-name", default="gpt-4o-mini")
    parser.add_argument("--no-cleanup", action="store_true", help="Don't cleanup cloned repository")

    args = parser.parse_args()

    console = Console()

    # Prompt for repo URL if not provided
    repo_url = args.repo_url
    if not repo_url:
        console.print("[bold yellow]Repository Configuration[/bold yellow]")
        repo_url = questionary.text(
            "Enter GitHub repository URL:",
            style=questionary.Style([('qmark', 'fg:cyan bold')])
        ).ask()
        if not repo_url:
            console.print("[red]No repository URL provided. Exiting.[/red]")
            return

    # Prompt for criteria if not provided
    criteria_path = args.criteria
    if not criteria_path:
        # Discover available criteria files
        criteria_dir = Path("criteria")
        available_criteria = sorted(criteria_dir.glob("*.yaml"))

        if available_criteria:
            console.print("\n[bold yellow]Select Criteria File[/bold yellow]")
            criteria_choices = [crit_file.name for crit_file in available_criteria]
            
            selected = questionary.select(
                "Choose criteria:",
                choices=criteria_choices,
                style=questionary.Style([
                    ('qmark', 'fg:cyan bold'),
                    ('pointer', 'fg:cyan bold'),
                    ('highlighted', 'fg:cyan bold'),
                ])
            ).ask()
            
            if not selected:
                console.print("[red]No criteria selected. Exiting.[/red]")
                return
                
            criteria_path = str(criteria_dir / selected)
        else:
            criteria_path = questionary.text(
                "Enter path to criteria YAML file:",
                default="criteria.yaml",
                style=questionary.Style([('qmark', 'fg:cyan bold')])
            ).ask()
            if not criteria_path:
                console.print("[red]No criteria file provided. Exiting.[/red]")
                return

    # Initialize scorer
    scorer = GitHubProjectScorer(
        model_provider=args.model_provider,
        model_name=args.model_name
    )

    # Run evaluation (async)
    async def run_evaluation():
        console.print("\n[bold green]Starting evaluation...[/bold green]")
        evaluation, usage_tracker = await scorer.evaluate_repository(
            repo_url=repo_url,
            criteria_path=Path(criteria_path),
            output_dir=Path(args.output) if args.output else None,
            cleanup=not args.no_cleanup
        )
        
        console.print("\n[bold green]Evaluation completed![/bold green]")
        console.print(f"Final score: {evaluation.total_score}/{evaluation.max_total_score}")

        # Show usage and cost summary
        if usage_tracker:
            usage_summary = usage_tracker.format_cost_summary()
            print(usage_summary)
    
    asyncio.run(run_evaluation())


def main():
    """Main entry point"""
    cli_main()


if __name__ == "__main__":
    main()
