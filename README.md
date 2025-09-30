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
- **Interactive UI**: Arrow-key navigation for selecting repositories and criteria files


## Installation

```bash
pip install uv
uv sync
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
uv run main.py
```

The interactive mode will ask you step-by-step for:

1. **Repository URL** - GitHub repository to evaluate (text input)
2. **Criteria file** - Choose from available criteria using arrow keys:
   - `ai-crash-course.yaml` - AI Crash Course (8 criteria, 18 pts max)
   - `de-zoomcamp.yaml` - Data Engineering Zoomcamp (8 criteria, 30 pts max)
   - `llm-zoomcamp.yaml` - LLM Zoomcamp (11 criteria, 26 pts max)
   - `ml-zoomcamp.yaml` - Machine Learning Zoomcamp (9 criteria, 16 pts max)
   - `mlops-zoomcamp.yaml` - MLOps Zoomcamp (8 criteria, 34 pts max)

### Command Line Mode

For automation or scripting, use command line arguments:

```bash
# Basic usage - prompts for criteria selection
uv run main.py https://github.com/owner/repo

# With custom options
uv run main.py https://github.com/owner/repo \
    --criteria criteria/llm-zoomcamp.yaml \
    --output ./reports \
    --model-provider anthropic \
    --model-name claude-3-5-sonnet-20241022
```

- `repo_url`: GitHub repository URL (optional - prompts if not provided)
- `--criteria`: Path to criteria YAML file (optional - shows interactive menu if not provided)
- `--output`: Output directory for reports (optional)
- `--model-provider`: AI provider - "openai" or "anthropic" (default: openai)
- `--model-name`: Model name (default: gpt-4o-mini)
- `--no-cleanup`: Don't cleanup cloned repository

## Criteria Configuration

All criteria files are located in the `criteria/` folder. Each file defines evaluation criteria for different course projects.

### Available Criteria Files

1. **`criteria/ai-crash-course.yaml`** - AI Crash Course project evaluation
   - Dataset requirement (different from FAQ dataset)
   - Data pipeline, agent implementation, agent evaluation
   - User interface, code organization, reproducibility
   - Documentation quality (README with visuals)
   - Max: 18 points

2. **`criteria/llm-zoomcamp.yaml`** - LLM Zoomcamp project evaluation
   - Problem description, RAG flow, retrieval/RAG evaluation
   - Interface, ingestion pipeline, monitoring
   - Containerization, reproducibility
   - Best practices (hybrid search, re-ranking, query rewriting)
   - Max: 26 points

3. **`criteria/de-zoomcamp.yaml`** - Data Engineering Zoomcamp
   - Cloud infrastructure, batch/streaming ingestion
   - Transformations, SQL, reproducibility
   - Best practices
   - Max: 30 points

4. **`criteria/ml-zoomcamp.yaml`** - Machine Learning Zoomcamp
   - Problem description, EDA, model training
   - Experiment tracking, reproducibility
   - Best practices (testing, linting, CI/CD)
   - Max: 16 points

5. **`criteria/mlops-zoomcamp.yaml`** - MLOps Zoomcamp
   - Problem description, cloud deployment
   - Experiment tracking, workflow orchestration
   - Model deployment, monitoring, best practices
   - Max: 34 points

See `criteria/README.md` for detailed descriptions of each criteria file.

### Criteria Format

#### Scored Criteria
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

#### Checklist Criteria
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

## Testing

Run the test suite with coverage:

```bash
# Run all tests with coverage report
uv run pytest

# Generate HTML coverage report
uv run pytest --cov=. --cov-report=html
# Open htmlcov/index.html in browser

# Run specific test file
uv run pytest tests/test_models.py
```

**Current Coverage**: 50.00%
- `usage_tracker.py`: 95.10%
- `repository_manager.py`: 85.96%
- `models.py`: 84.52%
- `analyzer_tools.py`: 39.05%

## Programmatic Usage

```python
import asyncio
from pathlib import Path
from scorer import GitHubProjectScorer

async def evaluate_project():
    scorer = GitHubProjectScorer(
        model_provider="openai",
        model_name="gpt-4o-mini"
    )
    
    evaluation, usage_tracker = await scorer.evaluate_repository(
        repo_url="https://github.com/owner/repo",
        criteria_path=Path("criteria/llm-zoomcamp.yaml"),
        output_dir=Path("./reports")
    )
    
    print(f"Score: {evaluation.total_score}/{evaluation.max_total_score}")
    
    # Show cost breakdown
    if usage_tracker:
        print(usage_tracker.format_cost_summary())

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
  gpt-4o-mini:
    Tokens: 3,500 input + 800 output
    Cost: $0.1530 ($0.1050 input + $0.0480 output)
```

Pricing is configurable in `pricing.yaml` and includes support for:
- OpenAI models (GPT-4, GPT-4 Turbo, GPT-4o, GPT-3.5 Turbo, etc.)
- Anthropic models (Claude 3.5 Sonnet, Claude 3 Haiku, etc.)

### Progress Tracking

Real-time progress bar shows:
- Current criteria being evaluated
- Success/failure status for each criteria
- Overall completion percentage
- Token usage as evaluation proceeds

## Architecture

### Project Structure

```
github-project-scorer/
├── main.py                    # Simple entry point (delegates to scorer.main)
├── scorer/                    # Main package
│   ├── __init__.py
│   ├── main.py               # CLI interface and orchestrator
│   ├── models.py             # Data models and YAML loading
│   ├── repository_manager.py # GitHub repository cloning and cleanup
│   ├── analyzer_tools.py     # Repository file analysis tools
│   ├── agents.py             # Pydantic AI agent creation and prompts
│   ├── evaluator.py          # Project evaluation orchestration with streaming
│   ├── report_generator.py   # Report generation and formatting
│   └── usage_tracker.py      # Token usage and cost tracking
├── criteria/                  # Evaluation criteria files
│   ├── ai-crash-course.yaml
│   ├── llm-zoomcamp.yaml
│   ├── de-zoomcamp.yaml
│   ├── ml-zoomcamp.yaml
│   └── mlops-zoomcamp.yaml
├── tests/                     # Comprehensive test suite with pytest
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_usage_tracker.py
│   ├── test_repository_manager.py
│   └── test_analyzer_basic.py
├── example.py                 # Example usage
├── pricing.yaml               # Model pricing configuration
└── pyproject.toml             # Project dependencies and configuration
```

### Module Responsibilities

- **`main.py`**: Simple entry point that delegates to `scorer.main`
- **`scorer/main.py`**: CLI interface, argument parsing, and evaluation orchestration
- **`scorer/models.py`**: Pydantic data models and YAML criteria loading
- **`scorer/repository_manager.py`**: Git operations and temporary directory management
- **`scorer/analyzer_tools.py`**: File reading, notebook formatting, and repository analysis
- **`scorer/agents.py`**: Pydantic AI agent creation with dynamic tool registration
- **`scorer/evaluator.py`**: Evaluation workflow with streaming progress display
- **`scorer/report_generator.py`**: Console and file report generation
- **`scorer/usage_tracker.py`**: Token counting and cost calculation with pricing lookup
