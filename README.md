# GitHub Project Scorer

A multi-agent system using Pydantic AI for scoring GitHub projects against customizable criteria.

## Features

- **Multi-agent evaluation**: Uses Pydantic AI agents to evaluate different aspects of projects
- **Flexible criteria**: Define evaluation criteria in YAML with scored or checklist formats
- **Repository analysis**: Clones and analyzes GitHub repositories automatically
- **Comprehensive reports**: Generates detailed reports with improvement suggestions
- **Multiple models**: Supports OpenAI and Anthropic models
- **Progress tracking**: Real-time progress bar showing evaluation status
- **Cost tracking**: Automatic token usage and cost calculation with detailed breakdown
- **Interactive mode**: Guided setup with smart defaults and validation

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Set your API key as an environment variable:
```bash
# For OpenAI
export OPENAI_API_KEY="your-api-key"

# For Anthropic
export ANTHROPIC_API_KEY="your-api-key"
```

## Usage

### Interactive Mode (Recommended)

Simply run the script without arguments for a guided, interactive experience:

```bash
python main.py
```

The interactive mode will ask you step-by-step for:
1. **Repository URL** - GitHub repository to evaluate
2. **Criteria file** - Choose from available criteria or specify custom path
3. **AI model** - Automatically detects available API keys and model options
4. **Output settings** - Whether to save reports and cleanup options
5. **Confirmation** - Review settings before starting evaluation

### Command Line Mode

For automation or scripting, use command line arguments:

```bash
# Basic usage
python main.py https://github.com/owner/repo

# With custom options
python main.py https://github.com/owner/repo \
    --criteria my_criteria.yaml \
    --output ./reports \
    --model-provider anthropic \
    --model-name claude-3-sonnet-20240229
```

### Parameters

- `repo_url`: GitHub repository URL (required)
- `--criteria`: Path to criteria YAML file (default: criteria.yaml)
- `--output`: Output directory for reports (optional)
- `--model-provider`: AI provider - "openai" or "anthropic" (default: openai)
- `--model-name`: Model name (default: gpt-4)
- `--no-cleanup`: Don't cleanup cloned repository

## Criteria Configuration

Define evaluation criteria in YAML format. See `criteria.yaml` for examples.

### Scored Criteria
```yaml
criteria:
  - name: "Problem description"
    type: "scored"
    score_levels:
      - score: 0
        description: "The problem is not described"
      - score: 1
        description: "The problem is described but briefly"
      - score: 2
        description: "The problem is well-described"
```

### Checklist Criteria
```yaml
criteria:
  - name: "Best practices"
    type: "checklist"
    items:
      - description: "Hybrid search implementation"
        points: 1
      - description: "Document re-ranking"
        points: 1
```

## Programmatic Usage

```python
import asyncio
from pathlib import Path
from main import GitHubProjectScorer

async def evaluate_project():
    scorer = GitHubProjectScorer(
        model_provider="openai",
        model_name="gpt-4"
    )
    
    evaluation = await scorer.evaluate_repository(
        repo_url="https://github.com/owner/repo",
        criteria_path=Path("criteria.yaml"),
        output_dir=Path("./reports")
    )
    
    print(f"Score: {evaluation.total_score}/{evaluation.max_total_score}")

asyncio.run(evaluate_project())
```

## Output

The system generates:
1. **Console report**: Rich-formatted evaluation results with progress tracking
2. **Markdown report**: Detailed written report saved to file
3. **Improvement suggestions**: Specific recommendations for enhancement
4. **Cost breakdown**: Token usage and pricing information per model

### Cost Tracking

The system automatically tracks token usage and calculates costs based on current pricing:

```
Cost Summary:
Total Tokens: 4,500 input + 1,000 output
Total Cost: $0.1590

Per Model:
  gpt-4:
    Tokens: 3,500 input + 800 output
    Cost: $0.1530 ($0.1050 input + $0.0480 output)
```

Pricing is configurable in `pricing.yaml` and includes support for:
- OpenAI models (GPT-4, GPT-4 Turbo, GPT-3.5 Turbo, etc.)
- Anthropic models (Claude 3.5 Sonnet, Claude 3 Haiku, etc.)
- Future models (GPT-5 series placeholder pricing)

### Progress Tracking

Real-time progress bar shows:
- Current criteria being evaluated
- Success/failure status for each criteria
- Overall completion percentage
- Token usage as evaluation proceeds

## Architecture

- `models.py`: Data models and YAML loading
- `repository_manager.py`: GitHub repository cloning
- `file_analyzer.py`: Repository file analysis tools
- `evaluator.py`: Pydantic AI evaluation agents
- `report_generator.py`: Report generation and formatting
- `main.py`: Main orchestrator and CLI interface
