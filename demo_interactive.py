"""
Demo script showing the interactive interface without requiring API keys
"""
import asyncio
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel


async def demo_interactive():
    """Demo version of the interactive interface"""
    console = Console()
    
    # Welcome message
    console.print(Panel.fit(
        "[bold blue]GitHub Project Scorer - Demo Mode[/bold blue]\n"
        "[white]This demo shows the interactive interface without running actual evaluation[/white]",
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
            exists = "✅" if Path(file).exists() else "❌"
            console.print(f"  {i}. {exists} {file} - {desc}")
        else:
            console.print(f"  {i}. 📁 {desc}")
    
    criteria_choice = Prompt.ask(
        "[cyan]Choose criteria file[/cyan]",
        choices=["1", "2", "3"],
        default="1"
    )
    
    if criteria_choice == "1":
        criteria_path = "criteria.yaml"
    elif criteria_choice == "2":
        criteria_path = "example_criteria.yaml"
    else:
        criteria_path = Prompt.ask("[cyan]Enter path to custom criteria file[/cyan]")
    
    # Model configuration (demo)
    console.print("\n[bold yellow]Step 3: AI Model Configuration[/bold yellow]")
    console.print("[yellow]Demo mode: API key detection skipped[/yellow]")
    
    model_provider = Prompt.ask(
        "[cyan]Choose AI provider[/cyan]",
        choices=["openai", "anthropic"],
        default="openai"
    )
    
    if model_provider == "openai":
        model_options = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
    else:
        model_options = ["claude-3-5-sonnet-20241022", "claude-3-sonnet-20240229"]
    
    console.print(f"\nAvailable {model_provider} models:")
    for i, model in enumerate(model_options, 1):
        console.print(f"  {i}. {model}")
    
    model_choice = Prompt.ask(
        "[cyan]Choose model[/cyan]",
        choices=[str(i) for i in range(1, len(model_options) + 1)],
        default="1"
    )
    model_name = model_options[int(model_choice) - 1]
    
    # Output configuration
    console.print("\n[bold yellow]Step 4: Output Configuration[/bold yellow]")
    
    save_report = Confirm.ask("[cyan]Save detailed report to file?[/cyan]", default=True)
    
    if save_report:
        output_dir = Prompt.ask(
            "[cyan]Output directory for reports[/cyan]",
            default="./reports"
        )
    else:
        output_dir = None
    
    cleanup_repo = Confirm.ask("[cyan]Clean up cloned repository after evaluation?[/cyan]", default=True)
    
    # Summary
    console.print("\n[bold yellow]Configuration Summary[/bold yellow]")
    console.print(f"📁 Repository: {repo_url}")
    console.print(f"📋 Criteria: {criteria_path}")
    console.print(f"🤖 Model: {model_provider}/{model_name}")
    console.print(f"💾 Save report: {'Yes' if save_report else 'No'}")
    if save_report:
        console.print(f"📂 Output dir: {output_dir}")
    console.print(f"🧹 Cleanup: {'Yes' if cleanup_repo else 'No'}")
    
    if Confirm.ask("\n[cyan]Proceed with evaluation?[/cyan]", default=True):
        console.print("\n[bold green]🚀 Demo Mode: Evaluation would start here![/bold green]")
        console.print("[yellow]In real mode, this would clone the repository and run AI evaluation.[/yellow]")
    else:
        console.print("[yellow]Evaluation cancelled.[/yellow]")


if __name__ == "__main__":
    print("Running interactive demo...")
    asyncio.run(demo_interactive())