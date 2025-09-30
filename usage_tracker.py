from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict
import yaml


@dataclass
class TokenUsage:
    """Track token usage for a single request"""
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""


@dataclass
class UsageTracker:
    """Track cumulative usage and calculate costs"""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    model_usage: Dict[str, TokenUsage] = field(default_factory=dict)
    pricing: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Load pricing configuration"""
        pricing_path = Path("pricing.yaml")
        if pricing_path.exists():
            with open(pricing_path, 'r', encoding='utf-8') as f:
                self.pricing = yaml.safe_load(f)
        else:
            # Fallback default pricing
            self.pricing = {
                'default': {'input': 1.0, 'output': 3.0}
            }
    
    def add_usage(self, model: str, input_tokens: int, output_tokens: int):
        """Add usage for a model"""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        
        if model not in self.model_usage:
            self.model_usage[model] = TokenUsage(model=model)
        
        self.model_usage[model].input_tokens += input_tokens
        self.model_usage[model].output_tokens += output_tokens
    
    def get_model_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for a specific model"""
        models = self.pricing.get('models', {})
        
        # Try exact match first
        if model in models:
            return models[model]
        
        # For pydantic-ai format like "openai:gpt-4o-mini", extract just the model name
        if ":" in model:
            model_name = model.split(":", 1)[1]
            if model_name in models:
                return models[model_name]
        
        # Try partial matches for model variations, but be more specific
        # Sort by length descending to match longer names first (e.g., gpt-4o-mini before gpt-4)
        sorted_models = sorted(models.keys(), key=len, reverse=True)
        for price_model in sorted_models:
            if price_model in model:
                return models[price_model]
        
        # Fall back to default
        return self.pricing.get('default', {'input': 1.0, 'output': 3.0})
    
    def calculate_cost(self, model: str = None) -> float:
        """Calculate total cost or cost for specific model"""
        total_cost = 0.0
        
        if model:
            # Cost for specific model
            if model in self.model_usage:
                usage = self.model_usage[model]
                pricing = self.get_model_pricing(model)
                
                input_cost = (usage.input_tokens / 1_000_000) * pricing['input']
                output_cost = (usage.output_tokens / 1_000_000) * pricing['output']
                total_cost = input_cost + output_cost
        else:
            # Total cost across all models
            for model_name, usage in self.model_usage.items():
                pricing = self.get_model_pricing(model_name)
                
                input_cost = (usage.input_tokens / 1_000_000) * pricing['input']
                output_cost = (usage.output_tokens / 1_000_000) * pricing['output']
                total_cost += input_cost + output_cost
        
        return total_cost
    
    def get_cost_breakdown(self) -> Dict:
        """Get detailed cost breakdown by model"""
        breakdown = {
            'total_cost': 0.0,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'models': {}
        }
        
        for model_name, usage in self.model_usage.items():
            pricing = self.get_model_pricing(model_name)
            
            input_cost = (usage.input_tokens / 1_000_000) * pricing['input']
            output_cost = (usage.output_tokens / 1_000_000) * pricing['output']
            model_cost = input_cost + output_cost
            
            breakdown['models'][model_name] = {
                'input_tokens': usage.input_tokens,
                'output_tokens': usage.output_tokens,
                'input_cost': input_cost,
                'output_cost': output_cost,
                'total_cost': model_cost,
                'pricing_per_1m': pricing
            }
            
            breakdown['total_cost'] += model_cost
        
        return breakdown
    
    def format_cost_summary(self) -> str:
        """Format a simplified cost summary"""
        breakdown = self.get_cost_breakdown()
        
        # Since we typically use one model, simplify the display
        if len(breakdown['models']) == 1:
            model_name = list(breakdown['models'].keys())[0]
            model_data = breakdown['models'][model_name]
            
            # Clean up model name for display
            display_name = model_name
            if ":" in model_name:
                display_name = model_name.replace(":", " ")
            
            summary = f"""Cost Summary:
Model: {display_name}
Total Tokens: {breakdown['total_input_tokens']:,} input + {breakdown['total_output_tokens']:,} output
Total Cost: ${model_data['input_cost']:.4f} input + ${model_data['output_cost']:.4f} output = ${breakdown['total_cost']:.4f}"""
        else:
            # Fallback for multiple models
            summary = f"""Cost Summary:
Total Tokens: {breakdown['total_input_tokens']:,} input + {breakdown['total_output_tokens']:,} output
Total Cost: ${breakdown['total_cost']:.4f}

Per Model:"""
            
            for model, data in breakdown['models'].items():
                summary += f"""
  {model}:
    Tokens: {data['input_tokens']:,} input + {data['output_tokens']:,} output
    Cost: ${data['total_cost']:.4f} (${data['input_cost']:.4f} input + ${data['output_cost']:.4f} output)"""
        
        return summary


@dataclass
class ProgressTracker:
    """Track evaluation progress"""
    total_criteria: int = 0
    completed_criteria: int = 0
    current_criteria: str = ""
    failed_criteria: int = 0
    
    def start(self, total: int):
        """Initialize progress tracking"""
        self.total_criteria = total
        self.completed_criteria = 0
        self.failed_criteria = 0
    
    def update(self, criteria_name: str, success: bool = True):
        """Update progress for a criteria"""
        self.current_criteria = criteria_name
        if success:
            self.completed_criteria += 1
        else:
            self.failed_criteria += 1
    
    def get_progress_text(self) -> str:
        """Get current progress as text"""
        remaining = self.total_criteria - self.completed_criteria - self.failed_criteria
        percentage = (self.completed_criteria / self.total_criteria * 100) if self.total_criteria > 0 else 0
        
        return f"Progress: {self.completed_criteria}/{self.total_criteria} ({percentage:.1f}%) | Failed: {self.failed_criteria} | Remaining: {remaining}"
    
    def is_complete(self) -> bool:
        """Check if all criteria are processed"""
        return (self.completed_criteria + self.failed_criteria) >= self.total_criteria