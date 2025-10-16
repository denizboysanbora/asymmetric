"""
Configuration management for Qullamaggie.
Handles YAML config loading, environment variables, and Pydantic validation.
"""
import os
from pathlib import Path
from typing import List, Literal, Optional
import yaml
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv


class GateConfig(BaseModel):
    """Market gate configuration."""
    proxy: str = Field(default="QQQ", description="ETF proxy for market gate")
    ema_short: int = Field(default=10, ge=1, le=50, description="Short EMA period")
    ema_long: int = Field(default=20, ge=1, le=100, description="Long EMA period")
    rising_lookback: int = Field(default=3, ge=1, le=10, description="Days to check for rising EMAs")


class FlagConfig(BaseModel):
    """Tight flag detection configuration."""
    min_days: int = Field(default=5, ge=3, le=30, description="Minimum days for flag formation")
    max_days: int = Field(default=20, ge=5, le=50, description="Maximum days for flag formation")
    atr_contract_ratio: float = Field(default=0.7, ge=0.1, le=1.0, description="ATR contraction ratio threshold")
    require_higher_lows: bool = Field(default=True, description="Require at least 2 higher swing lows")


class BreakoutConfig(BaseModel):
    """Breakout setup configuration."""
    impulse_min_pct: float = Field(default=30.0, ge=10.0, le=100.0, description="Minimum impulse percentage")
    lookback_impulse_days: int = Field(default=60, ge=20, le=90, description="Lookback days for impulse detection")
    flag_min_days: int = Field(default=5, ge=3, le=30, description="Minimum flag days")
    flag_max_days: int = Field(default=40, ge=10, le=60, description="Maximum flag days")
    atr_contract_ratio: float = Field(default=0.7, ge=0.1, le=1.0, description="ATR contraction ratio")


class EPConfig(BaseModel):
    """Episodic Pivot setup configuration."""
    gap_min_pct: float = Field(default=10.0, ge=5.0, le=50.0, description="Minimum gap percentage")
    premkt_notional_min: float = Field(default=2000000, ge=100000, description="Minimum premarket notional")
    require_big_volume_minutes: int = Field(default=10, ge=5, le=30, description="Minutes to check for volume spike")
    prefer_flat_prior_months: bool = Field(default=True, description="Prefer flat prior 3-6 months")


class ParabolicLongConfig(BaseModel):
    """Parabolic Long setup configuration."""
    crash_min_pct: float = Field(default=50.0, ge=30.0, le=90.0, description="Minimum crash percentage")
    lookback_days: int = Field(default=7, ge=3, le=14, description="Lookback days for crash detection")
    oversold_atr_multiple: float = Field(default=2.0, ge=1.0, le=5.0, description="Oversold ATR multiple")


class SetupsConfig(BaseModel):
    """Setup detection configuration."""
    breakout: BreakoutConfig = Field(default_factory=BreakoutConfig)
    ep: EPConfig = Field(default_factory=EPConfig)
    parabolic_long: ParabolicLongConfig = Field(default_factory=ParabolicLongConfig)


class ScanConfig(BaseModel):
    """Stock scanning configuration."""
    adr_min_pct: float = Field(default=5.0, ge=1.0, le=20.0, description="Minimum ADR percentage")
    rs_top_percentile: float = Field(default=0.90, ge=0.5, le=0.99, description="RS percentile threshold")


class CatalystConfig(BaseModel):
    """Gap catalyst configuration."""
    premkt_gap_min_pct: float = Field(default=4.0, ge=1.0, le=20.0, description="Minimum premarket gap percentage")
    premkt_notional_min: float = Field(default=1000000, ge=100000, description="Minimum premarket notional volume")


class EntryConfig(BaseModel):
    """Entry signal configuration."""
    or_minutes: int = Field(default=5, ge=1, le=30, description="Opening range minutes")


class OutputsConfig(BaseModel):
    """Output configuration."""
    dir: str = Field(default="artifacts", description="Output directory")
    save: bool = Field(default=True, description="Save outputs to files")


class UniverseConfig(BaseModel):
    """Universe configuration."""
    mode: Literal["dynamic", "static"] = Field(default="dynamic", description="Universe mode")
    static_symbols: List[str] = Field(default_factory=list, description="Static symbol list")
    
    # Dynamic universe filters
    min_price: float = Field(default=10.0, ge=1.0, description="Minimum stock price")
    min_avg_volume: int = Field(default=100000, ge=10000, description="Minimum average volume")
    require_options: bool = Field(default=True, description="Require options availability")
    exchanges: List[str] = Field(default=["NYSE", "NASDAQ"], description="Allowed exchanges")


class Config(BaseModel):
    """Main configuration model."""
    name: str = Field(default="Qullamaggie", description="System name")
    gate: GateConfig = Field(default_factory=GateConfig)
    scan: ScanConfig = Field(default_factory=ScanConfig)
    setups: SetupsConfig = Field(default_factory=SetupsConfig)
    entry: EntryConfig = Field(default_factory=EntryConfig)
    outputs: OutputsConfig = Field(default_factory=OutputsConfig)
    tz: str = Field(default="America/New_York", description="Timezone")
    universe: UniverseConfig = Field(default_factory=UniverseConfig)
    
    @validator('gate')
    def validate_ema_order(cls, v):
        if v.ema_short >= v.ema_long:
            raise ValueError("ema_short must be less than ema_long")
        return v
    
    @validator('setups')
    def validate_setup_params(cls, v):
        if v.breakout.flag_min_days >= v.breakout.flag_max_days:
            raise ValueError("breakout.flag_min_days must be less than flag_max_days")
        return v


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from YAML file and environment variables.
    
    Args:
        config_path: Path to config.yaml file. If None, looks for config.yaml in current directory.
        
    Returns:
        Config object with loaded settings
        
    Raises:
        FileNotFoundError: If config file not found
        yaml.YAMLError: If config file is invalid YAML
        ValueError: If config validation fails
    """
    # Load environment variables first
    load_dotenv()
    
    # Check for API keys
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    if not api_key or not secret_key:
        raise ValueError(
            "Missing Alpaca API credentials. Please set ALPACA_API_KEY and ALPACA_SECRET_KEY "
            "in your .env file or environment variables.\n"
            "Get your free API keys at: https://alpaca.markets/"
        )
    
    # Determine config file path
    if config_path is None:
        config_path = Path.cwd() / "config.yaml"
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    # Load YAML config
    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in config file: {e}")
    
    # Create config object with validation
    try:
        return Config(**config_data)
    except Exception as e:
        raise ValueError(f"Config validation failed: {e}")


def get_default_config() -> Config:
    """Get default configuration."""
    return Config()


def create_sample_config(output_path: str = "config.yaml") -> None:
    """
    Create a sample configuration file.
    
    Args:
        output_path: Path where to save the sample config
    """
    sample_config = {
        "name": "Qullamaggie",
        "gate": {
            "proxy": "QQQ",
            "ema_short": 10,
            "ema_long": 20,
            "rising_lookback": 3
        },
        "scan": {
            "adr_min_pct": 5.0,
            "rs_top_percentile": 0.90,
            "explosive_leg_pct": 25.0,
            "flag": {
                "min_days": 5,
                "max_days": 20,
                "atr_contract_ratio": 0.7,
                "require_higher_lows": True
            }
        },
        "catalyst": {
            "premkt_gap_min_pct": 4.0,
            "premkt_notional_min": 1000000
        },
        "entry": {
            "or_minutes": 5
        },
        "outputs": {
            "dir": "artifacts",
            "save": True
        },
        "tz": "America/New_York",
        "universe": {
            "mode": "dynamic",
            "static_symbols": [
                "NVDA", "TSLA", "ROKU", "COIN", "ENPH", "SHOP", "SQ", "CRWD"
            ],
            "min_price": 10.0,
            "min_avg_volume": 100000,
            "require_options": True,
            "exchanges": ["NYSE", "NASDAQ"]
        }
    }
    
    with open(output_path, 'w') as f:
        yaml.dump(sample_config, f, default_flow_style=False, sort_keys=False)
    
    print(f"Sample configuration created: {output_path}")
