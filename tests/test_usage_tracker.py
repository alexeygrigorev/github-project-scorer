import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil
from pathlib import Path

from scorer.usage_tracker import UsageTracker, ProgressTracker, TokenUsage


class TestTokenUsage:
    def test_token_usage_creation(self):
        """Test creating a TokenUsage object"""
        usage = TokenUsage(input_tokens=1000, output_tokens=500, model="gpt-4")
        
        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500
        assert usage.model == "gpt-4"
    
    def test_token_usage_defaults(self):
        """Test TokenUsage with default values"""
        usage = TokenUsage()
        
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.model == ""


class TestUsageTracker:
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create a test pricing file
        pricing_content = """
models:
  gpt-4:
    input: 30.0
    output: 60.0
  gpt-3.5-turbo:
    input: 1.0
    output: 2.0
default:
  input: 1.0
  output: 3.0
"""
        self.pricing_file = self.temp_path / "test_pricing.yaml"
        self.pricing_file.write_text(pricing_content)
    
    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_init_default(self):
        """Test UsageTracker initialization with defaults"""
        tracker = UsageTracker()
        
        assert tracker.total_input_tokens == 0
        assert tracker.total_output_tokens == 0
        assert isinstance(tracker.model_usage, dict)
        assert isinstance(tracker.pricing, dict)
    
    @patch('pathlib.Path.exists')
    def test_init_with_pricing_file(self, mock_exists):
        """Test initialization when pricing file exists"""
        mock_exists.return_value = True
        
        with patch('builtins.open', mock_open_yaml(self.pricing_file.read_text())):
            tracker = UsageTracker()
            
            assert "models" in tracker.pricing
            assert "gpt-4" in tracker.pricing["models"]
    
    @patch('pathlib.Path.exists')
    def test_init_without_pricing_file(self, mock_exists):
        """Test initialization when pricing file doesn't exist"""
        mock_exists.return_value = False
        
        tracker = UsageTracker()
        
        assert "default" in tracker.pricing
        assert tracker.pricing["default"]["input"] == 1.0
        assert tracker.pricing["default"]["output"] == 3.0
    
    def test_add_usage(self):
        """Test adding usage data"""
        tracker = UsageTracker()
        
        # Mock usage object
        usage = Mock()
        usage.input_tokens = 1000
        usage.output_tokens = 500
        
        tracker.add_usage("gpt-4", usage)
        
        assert tracker.total_input_tokens == 1000
        assert tracker.total_output_tokens == 500
        assert "gpt-4" in tracker.model_usage
        assert tracker.model_usage["gpt-4"].input_tokens == 1000
        assert tracker.model_usage["gpt-4"].output_tokens == 500
    
    def test_add_usage_none_tokens(self):
        """Test adding usage with None token values"""
        tracker = UsageTracker()
        
        usage = Mock()
        usage.input_tokens = None
        usage.output_tokens = None
        
        tracker.add_usage("gpt-4", usage)
        
        assert tracker.total_input_tokens == 0
        assert tracker.total_output_tokens == 0
    
    def test_get_model_pricing(self):
        """Test getting model pricing"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open_yaml(self.pricing_file.read_text())):
            tracker = UsageTracker()
            
            pricing = tracker.get_model_pricing("gpt-4")
            assert pricing["input"] == 30.0
            assert pricing["output"] == 60.0
    
    def test_get_model_pricing_with_prefix(self):
        """Test getting model pricing with pydantic-ai prefix"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open_yaml(self.pricing_file.read_text())):
            tracker = UsageTracker()
            
            pricing = tracker.get_model_pricing("openai:gpt-4")
            assert pricing["input"] == 30.0
            assert pricing["output"] == 60.0
    
    def test_get_model_pricing_unknown(self):
        """Test getting pricing for unknown model"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open_yaml(self.pricing_file.read_text())):
            tracker = UsageTracker()
            
            pricing = tracker.get_model_pricing("unknown-model")
            assert pricing["input"] == 1.0  # Default pricing
            assert pricing["output"] == 3.0
    
    def test_calculate_cost_single_model(self):
        """Test calculating cost for single model"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open_yaml(self.pricing_file.read_text())):
            tracker = UsageTracker()
            
            usage = Mock()
            usage.input_tokens = 1000000  # 1M tokens
            usage.output_tokens = 500000   # 0.5M tokens
            
            tracker.add_usage("gpt-4", usage)
            cost = tracker.calculate_cost("gpt-4")
            
            # Expected: (1M * 30.0 + 0.5M * 60.0) / 1M = 30.0 + 30.0 = 60.0
            assert cost == 60.0
    
    def test_calculate_cost_total(self):
        """Test calculating total cost across all models"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open_yaml(self.pricing_file.read_text())):
            tracker = UsageTracker()
            
            usage1 = Mock()
            usage1.input_tokens = 1000000
            usage1.output_tokens = 500000
            
            usage2 = Mock()
            usage2.input_tokens = 2000000
            usage2.output_tokens = 1000000
            
            tracker.add_usage("gpt-4", usage1)
            tracker.add_usage("gpt-3.5-turbo", usage2)
            
            total_cost = tracker.calculate_cost()
            
            # GPT-4: (1M * 30 + 0.5M * 60) / 1M = 60.0
            # GPT-3.5: (2M * 1 + 1M * 2) / 1M = 4.0
            # Total: 64.0
            assert total_cost == 64.0
    
    def test_get_cost_breakdown(self):
        """Test getting detailed cost breakdown"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open_yaml(self.pricing_file.read_text())):
            tracker = UsageTracker()
            
            usage = Mock()
            usage.input_tokens = 1000000
            usage.output_tokens = 500000
            
            tracker.add_usage("gpt-4", usage)
            breakdown = tracker.get_cost_breakdown()
            
            assert breakdown["total_cost"] == 60.0
            assert breakdown["total_input_tokens"] == 1000000
            assert breakdown["total_output_tokens"] == 500000
            assert "gpt-4" in breakdown["models"]
            assert breakdown["models"]["gpt-4"]["total_cost"] == 60.0
    
    def test_format_cost_summary_single_model(self):
        """Test formatting cost summary for single model"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open_yaml(self.pricing_file.read_text())):
            tracker = UsageTracker()
            
            usage = Mock()
            usage.input_tokens = 1000
            usage.output_tokens = 500
            
            tracker.add_usage("gpt-4", usage)
            summary = tracker.format_cost_summary()
            
            assert "Cost Summary:" in summary
            assert "gpt-4" in summary
            assert "1,000 input + 500 output" in summary


class TestProgressTracker:
    def test_init(self):
        """Test ProgressTracker initialization"""
        tracker = ProgressTracker()
        
        assert tracker.total_criteria == 0
        assert tracker.completed_criteria == 0
        assert tracker.current_criteria == ""
        assert tracker.failed_criteria == 0
    
    def test_start(self):
        """Test starting progress tracking"""
        tracker = ProgressTracker()
        tracker.start(5)
        
        assert tracker.total_criteria == 5
        assert tracker.completed_criteria == 0
        assert tracker.failed_criteria == 0
    
    def test_update_success(self):
        """Test updating progress with success"""
        tracker = ProgressTracker()
        tracker.start(5)
        
        tracker.update("Test Criteria", success=True)
        
        assert tracker.current_criteria == "Test Criteria"
        assert tracker.completed_criteria == 1
        assert tracker.failed_criteria == 0
    
    def test_update_failure(self):
        """Test updating progress with failure"""
        tracker = ProgressTracker()
        tracker.start(5)
        
        tracker.update("Test Criteria", success=False)
        
        assert tracker.current_criteria == "Test Criteria"
        assert tracker.completed_criteria == 0
        assert tracker.failed_criteria == 1
    
    def test_get_progress_text(self):
        """Test getting progress text"""
        tracker = ProgressTracker()
        tracker.start(5)
        tracker.update("Test 1", success=True)
        tracker.update("Test 2", success=False)
        
        text = tracker.get_progress_text()
        
        assert "Progress: 1/5 (20.0%)" in text
        assert "Failed: 1" in text
        assert "Remaining: 3" in text
    
    def test_is_complete(self):
        """Test completion check"""
        tracker = ProgressTracker()
        tracker.start(3)
        
        assert not tracker.is_complete()
        
        tracker.update("Test 1", success=True)
        tracker.update("Test 2", success=False)
        
        assert not tracker.is_complete()
        
        tracker.update("Test 3", success=True)
        
        assert tracker.is_complete()


def mock_open_yaml(content):
    """Mock open function for YAML content"""
    from unittest.mock import mock_open
    import yaml
    
    def yaml_load_side_effect(*args, **kwargs):
        return yaml.safe_load(content)
    
    mock_file = mock_open(read_data=content)
    with patch('yaml.safe_load', side_effect=yaml_load_side_effect):
        return mock_file