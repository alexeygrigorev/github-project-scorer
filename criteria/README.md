# Evaluation Criteria Files

This directory contains YAML files that define evaluation criteria for different course projects. Each file specifies what aspects of a project will be evaluated and how points are awarded.

## Available Criteria Files

### 1. AI Crash Course (`ai-crash-course.yaml`)
**Total**: 18 points max (2 must-have + 12 scored + 4 documentation)

#### Must-have Dataset Requirement (2 points)
- Uses different dataset (not FAQ dataset from DataTalksClub/faq) - 2 points

#### Scored Criteria (12 points, 0-2 each)
- **Data pipeline** (0-2): From basic loading to well-structured pipeline
- **Agent implementation** (0-2): From notebooks to modular, reusable code
- **Agent evaluation** (0-2): From no evaluation to comprehensive metrics
- **User interface** (0-2): From CLI to interactive UI (Streamlit/Gradio)
- **Code organization** (0-2): From single notebook to well-structured modules
- **Reproducibility** (0-2): From no docs to clear setup with dependencies

#### Documentation Quality (4 points)
- Clear project goal and purpose - 1 point
- Setup/installation instructions - 1 point
- Usage examples or quickstart - 1 point
- Visuals (demo video, screenshots, GIFs) - 1 point

### 2. LLM Zoomcamp (`llm-zoomcamp.yaml`)
**Total**: 26 points max (20 scored + 6 checklist)

#### Scored Criteria (20 points)
- Problem description (0-2)
- RAG flow (0-2)
- Retrieval evaluation (0-2)
- RAG evaluation (0-2)
- Interface (0-2)
- Ingestion pipeline (0-2)
- Monitoring (0-2)
- Containerization (0-2)
- Reproducibility (0-2)

#### Checklist Items (6 points)
- Best practices: Hybrid search, document re-ranking, user query rewriting (3 points)
- Bonus points: Cloud deployment + 3 bonus points (5 points)

### 3. Data Engineering Zoomcamp (`de-zoomcamp.yaml`)
**Total**: 30 points max

#### Scored Criteria
- Problem description (0-3)
- Cloud (0-4)
- Data ingestion (batch and streaming) (0-4)
- Data warehouse (0-4)
- Transformations (dbt, spark, etc.) (0-4)
- Dashboard (0-4)
- Reproducibility (0-4)

#### Checklist Items
- Best practices (3 points)

### 4. Machine Learning Zoomcamp (`ml-zoomcamp.yaml`)
**Total**: 16 points max

#### Scored Criteria
- Problem description (0-2)
- EDA (0-2)
- Model training (0-3)
- Exporting notebook to script (0-1)
- Model deployment (0-1)
- Dependency and environment management (0-1)
- Containerization (0-1)
- Cloud deployment (0-1)

#### Checklist Items
- Best practices: Unit tests, integration tests, linter, CI/CD (4 points)

### 5. MLOps Zoomcamp (`mlops-zoomcamp.yaml`)
**Total**: 34 points max

#### Scored Criteria
- Problem description (0-2)
- Cloud (0-4)
- Experiment tracking and model registry (0-4)
- Workflow orchestration (0-4)
- Model deployment (0-4)
- Model monitoring (0-4)
- Reproducibility (0-4)

#### Checklist Items
- Best practices: Unit tests, integration test, linter, Makefile, pre-commit hooks, CI/CD (8 points)

## Criteria Types

### Scored Criteria
Projects are evaluated on a scale (typically 0-2 or 0-4) based on how well they meet the criteria.

Example:
```yaml
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
Binary items that are either present or absent. Each item has a fixed point value.

Example:
```yaml
- name: "Best practices"
  type: "checklist"
  items:
    - description: "Unit tests are present"
      points: 1
    - description: "CI/CD pipeline exists"
      points: 2
```

## Usage

To use a criteria file for evaluation:

```bash
python -m uv run main.py <repo_url> --criteria criteria/ai-crash-course.yaml
```

Or use the interactive mode and select from the list:

```bash
python -m uv run main.py
```