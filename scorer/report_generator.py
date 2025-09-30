from typing import List
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from scorer.models import ProjectEvaluation, EvaluationResult


class ReportGenerator:
    """Generates evaluation reports in various formats"""
    
    def __init__(self):
        self.console = Console()
    
    def generate_console_report(self, evaluation: ProjectEvaluation) -> None:
        """Generate a rich console report"""
        
        # Header
        self.console.print()
        self.console.print(Panel.fit(
            f"[bold blue]GitHub Project Evaluation Report[/bold blue]\n"
            f"[white]Project: {evaluation.project_url}[/white]\n"
            f"[white]Total Score: {evaluation.total_score}/{evaluation.max_total_score} "
            f"({evaluation.total_score/evaluation.max_total_score*100:.1f}%)[/white]",
            border_style="blue"
        ))
        
        # Summary table
        table = Table(title="Evaluation Summary", show_header=True, header_style="bold magenta")
        table.add_column("Criteria", style="cyan", no_wrap=True)
        table.add_column("Type", style="yellow")
        table.add_column("Score", style="green", justify="center")
        table.add_column("Max", style="blue", justify="center")
        table.add_column("Percentage", style="magenta", justify="center")
        
        for result in evaluation.results:
            percentage = (result.score / result.max_score * 100) if result.max_score > 0 else 0
            color = "green" if percentage >= 80 else "yellow" if percentage >= 50 else "red"
            
            table.add_row(
                result.criteria_name,
                result.criteria_type.title(),
                str(result.score),
                str(result.max_score),
                f"[{color}]{percentage:.1f}%[/{color}]"
            )
        
        self.console.print(table)
        
        # Detailed results
        self.console.print("\n[bold yellow]Detailed Evaluation Results[/bold yellow]")
        for result in evaluation.results:
            self._print_detailed_result(result)
        
        # Improvements section
        if evaluation.improvements:
            self.console.print("\n[bold red]Suggested Improvements[/bold red]")
            for i, improvement in enumerate(evaluation.improvements, 1):
                self.console.print(f"[red]{i}.[/red] {improvement}")
    
    def _print_detailed_result(self, result: EvaluationResult) -> None:
        """Print detailed result for a single criteria"""
        percentage = (result.score / result.max_score * 100) if result.max_score > 0 else 0
        color = "green" if percentage >= 80 else "yellow" if percentage >= 50 else "red"
        
        panel_content = f"""
[bold]{result.criteria_name}[/bold] ({result.criteria_type})
[{color}]Score: {result.score}/{result.max_score} ({percentage:.1f}%)[/{color}]

[bold]Reasoning:[/bold]
{result.reasoning}

[bold]Evidence:[/bold]
{chr(10).join(['• ' + evidence for evidence in result.evidence]) if result.evidence else 'No specific evidence provided'}
        """.strip()
        
        self.console.print(Panel(panel_content, border_style=color, padding=(1, 2)))
    
    def generate_markdown_report(self, evaluation: ProjectEvaluation) -> str:
        """Generate a markdown report"""
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""# GitHub Project Evaluation Report

**Project:** {evaluation.project_url}  
**Generated:** {timestamp}  
**Total Score:** {evaluation.total_score}/{evaluation.max_total_score} ({evaluation.total_score/evaluation.max_total_score*100:.1f}%)

## Summary

| Criteria | Type | Score | Max | Percentage |
|----------|------|-------|-----|------------|
"""
        
        for result in evaluation.results:
            percentage = (result.score / result.max_score * 100) if result.max_score > 0 else 0
            report += f"| {result.criteria_name} | {result.criteria_type.title()} | {result.score} | {result.max_score} | {percentage:.1f}% |\n"
        
        report += "\n## Detailed Results\n\n"
        
        for result in evaluation.results:
            percentage = (result.score / result.max_score * 100) if result.max_score > 0 else 0
            
            report += f"""### {result.criteria_name}

**Type:** {result.criteria_type.title()}  
**Score:** {result.score}/{result.max_score} ({percentage:.1f}%)

**Reasoning:**
{result.reasoning}

**Evidence:**
"""
            
            if result.evidence:
                for evidence in result.evidence:
                    report += f"- {evidence}\n"
            else:
                report += "- No specific evidence provided\n"
            
            report += "\n"
        
        if evaluation.improvements:
            report += "## Suggested Improvements\n\n"
            for i, improvement in enumerate(evaluation.improvements, 1):
                report += f"{i}. {improvement}\n"
        
        return report
    
    def save_report(self, evaluation: ProjectEvaluation, output_path: Path, format: str = "markdown") -> None:
        """Save report to file"""
        if format.lower() == "markdown":
            content = self.generate_markdown_report(evaluation)
            output_path = output_path.with_suffix('.md')
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Report saved to: {output_path}")


class ImprovementGenerator:
    """Generates improvement suggestions based on evaluation results"""
    
    def generate_improvements(self, results: List[EvaluationResult]) -> List[str]:
        """Generate improvement suggestions based on low scores"""
        improvements = []
        
        for result in results:
            if result.score == 0:
                improvements.extend(self._get_zero_score_improvements(result))
            elif result.score < result.max_score * 0.5:  # Less than 50%
                improvements.extend(self._get_low_score_improvements(result))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_improvements = []
        for improvement in improvements:
            if improvement not in seen:
                seen.add(improvement)
                unique_improvements.append(improvement)
        
        return unique_improvements
    
    def _get_zero_score_improvements(self, result: EvaluationResult) -> List[str]:
        """Get improvements for criteria with zero score"""
        improvements = []
        criteria_name = result.criteria_name.lower()
        
        if "problem description" in criteria_name:
            improvements.append("Add a clear problem description to your README explaining what problem the project solves")
        
        elif "retrieval flow" in criteria_name:
            improvements.append("Implement a knowledge base and LLM-based retrieval system")
        
        elif "retrieval evaluation" in criteria_name:
            improvements.append("Add evaluation of different retrieval approaches and compare their performance")
        
        elif "llm evaluation" in criteria_name:
            improvements.append("Implement evaluation of LLM outputs with multiple approaches or prompts")
        
        elif "interface" in criteria_name:
            improvements.append("Create a user interface (CLI, web app, or API) for interacting with the application")
        
        elif "ingestion" in criteria_name:
            improvements.append("Add an automated data ingestion pipeline using Python scripts or specialized tools")
        
        elif "monitoring" in criteria_name:
            improvements.append("Implement monitoring with user feedback collection and/or dashboard")
        
        elif "containerization" in criteria_name:
            improvements.append("Add Docker containerization with Dockerfile and docker-compose configuration")
        
        elif "reproducibility" in criteria_name:
            improvements.append("Add clear setup instructions, specify dependency versions, and ensure data accessibility")
        
        elif "best practices" in criteria_name:
            improvements.append("Implement advanced techniques like hybrid search, document re-ranking, or query rewriting")
        
        return improvements
    
    def _get_low_score_improvements(self, result: EvaluationResult) -> List[str]:
        """Get improvements for criteria with low scores"""
        improvements = []
        criteria_name = result.criteria_name.lower()
        
        if "problem description" in criteria_name:
            improvements.append("Enhance the problem description with more detail and clarity")
        
        elif "retrieval flow" in criteria_name:
            improvements.append("Consider adding a knowledge base to complement direct LLM querying")
        
        elif "interface" in criteria_name:
            improvements.append("Upgrade from CLI/script to a web application or API for better user experience")
        
        elif "ingestion" in criteria_name:
            improvements.append("Automate the data ingestion process with scripts or specialized tools")
        
        elif "monitoring" in criteria_name:
            improvements.append("Add both user feedback collection AND a comprehensive monitoring dashboard")
        
        elif "containerization" in criteria_name:
            improvements.append("Complete Docker setup with both application and dependencies in docker-compose")
        
        elif "reproducibility" in criteria_name:
            improvements.append("Improve documentation completeness and ensure all dependencies are properly specified")
        
        return improvements