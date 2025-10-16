"""
Qullamaggie CLI interface.
Provides commands for analysis, opening range, and reporting.
"""
import sys
from pathlib import Path
from typing import Optional
import typer
from loguru import logger

from .config import load_config, get_default_config
from .data import (
    get_daily_bars, get_intraday_bars, get_premarket_stats, 
    get_dynamic_universe, now_et
)
from .features import market_gate
from .screen import build_candidates, rank_candidates, filter_candidates_by_volume, get_top_candidates
from .opening_range import compute_opening_range, get_entry_signals
from .report import (
    save_analysis_artifacts, print_dashboard, format_email_content,
    opening_range_to_dataframe
)


app = typer.Typer(
    name="qullamaggie",
    help="Qullamaggie Momentum Pattern Analyzer - Listen to the market, not your opinions.",
    add_completion=False
)


def setup_logging(log_level: str = "INFO"):
    """Setup loguru logging configuration."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )


@app.command()
def analyze(
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config.yaml file"),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level (DEBUG, INFO, WARNING, ERROR)"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save artifacts to files")
):
    """
    Run pre-market analysis: gate evaluation + candidate screening.
    
    This command should be run before market open to:
    1. Evaluate QQQ market gate (EMA 10/20 trend)
    2. Screen universe for momentum candidates
    3. Generate watchlist and save artifacts
    """
    setup_logging(log_level)
    
    try:
        # Load configuration
        try:
            cfg = load_config(config_path)
        except (FileNotFoundError, ValueError) as e:
            logger.warning(f"Could not load config file: {e}")
            logger.info("Using default configuration")
            cfg = get_default_config()
        
        logger.info("🚀 Starting Qullamaggie analysis...")
        
        # Get universe
        logger.info(f"Universe mode: {cfg.universe.mode}")
        if cfg.universe.mode == "dynamic":
            logger.info("Fetching dynamic universe from Alpaca...")
            symbols = get_dynamic_universe(
                min_price=cfg.universe.min_price,
                min_avg_volume=cfg.universe.min_avg_volume,
                require_options=cfg.universe.require_options,
                exchanges=cfg.universe.exchanges
            )
        else:
            symbols = cfg.universe.static_symbols
            logger.info(f"Using static universe: {len(symbols)} symbols")
        
        if not symbols:
            logger.error("No symbols to analyze")
            sys.exit(1)
        
        # Add QQQ for market gate
        if cfg.gate.proxy not in symbols:
            symbols.append(cfg.gate.proxy)
        
        # Fetch daily data
        logger.info(f"Fetching daily data for {len(symbols)} symbols...")
        daily_df = get_daily_bars(symbols, lookback_days=252)
        
        if daily_df.empty:
            logger.error("No daily data available")
            sys.exit(1)
        
        # Evaluate market gate
        logger.info(f"Evaluating market gate using {cfg.gate.proxy}...")
        qqq_data = daily_df.xs(cfg.gate.proxy, level='symbol')
        
        gate_open, gate_meta = market_gate(
            qqq_data,
            ema_short=cfg.gate.ema_short,
            ema_long=cfg.gate.ema_long,
            rising_lookback=cfg.gate.rising_lookback
        )
        
        gate_state = {
            "gate_open": gate_open,
            "timestamp": now_et().isoformat(),
            **gate_meta
        }
        
        gate_icon = "🟢" if gate_open else "🔴"
        logger.info(f"Market gate: {gate_icon} {'OPEN' if gate_open else 'CLOSED'}")
        
        # Screen for candidates
        logger.info("Screening for momentum candidates...")
        
        # Get premarket stats (placeholder for now)
        premarket_df = get_premarket_stats(symbols, {})
        
        candidates = build_candidates(daily_df, premarket_df, None, cfg)
        
        if not candidates:
            logger.warning("No candidates found - market conditions may not be suitable")
            candidates = []
        else:
            # Filter by volume
            candidates = filter_candidates_by_volume(
                candidates, 
                min_volume=cfg.universe.min_avg_volume
            )
            
            # Rank candidates
            candidates = rank_candidates(candidates)
            
            # Get top candidates
            candidates = get_top_candidates(candidates, limit=50)
            
            logger.info(f"Found {len(candidates)} ranked candidates")
        
        # Print dashboard
        print_dashboard(gate_state, candidates)
        
        # Save artifacts
        if save:
            saved_files = save_analysis_artifacts(
                gate_state, candidates, artifacts_dir=None
            )
            logger.info(f"Artifacts saved: {list(saved_files.keys())}")
        
        # Exit codes
        if gate_open and candidates:
            logger.info("✅ Analysis complete - Market gate open with candidates found")
            sys.exit(0)
        elif gate_open:
            logger.warning("⚠️  Analysis complete - Market gate open but no candidates found")
            sys.exit(0)
        else:
            logger.warning("⚠️  Analysis complete - Market gate closed")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


@app.command()
def opening_range(
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config.yaml file"),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save artifacts to files")
):
    """
    Compute opening range breakouts for current candidates.
    
    This command should be run after 9:35 AM ET to:
    1. Load latest candidates from artifacts
    2. Compute ORH/ORL for first 5 minutes
    3. Check for breakout triggers (price > ORH)
    4. Update opening range artifacts
    """
    setup_logging(log_level)
    
    try:
        # Load configuration
        if config_path:
            cfg = load_config(config_path)
        else:
            cfg = get_default_config()
        
        logger.info("⚡ Computing opening range breakouts...")
        
        # Check if we have recent candidates
        artifacts_dir = Path(cfg.outputs.dir) / now_et().date().strftime("%Y-%m-%d")
        candidates_file = artifacts_dir / "candidates.json"
        
        if not candidates_file.exists():
            logger.error(f"No candidates file found: {candidates_file}")
            logger.info("Run 'analyze' command first to generate candidates")
            sys.exit(1)
        
        # Load candidates
        import json
        with open(candidates_file, 'r') as f:
            candidates_data = json.load(f)
        
        symbols = [c['symbol'] for c in candidates_data]
        logger.info(f"Computing opening range for {len(symbols)} candidates")
        
        # Fetch intraday data for today
        now = now_et()
        start_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
        end_time = now
        
        if now.hour < 9 or (now.hour == 9 and now.minute < 35):
            logger.warning("Market may not be open yet - opening range may be incomplete")
        
        minute_df = get_intraday_bars(symbols, start_time, end_time, timeframe="1Min")
        
        if minute_df.empty:
            logger.error("No intraday data available")
            sys.exit(1)
        
        # Compute opening range
        opening_range_results = compute_opening_range(
            minute_df,
            or_minutes=cfg.entry.or_minutes
        )
        
        # Convert to DataFrame for dashboard
        or_df = opening_range_to_dataframe(opening_range_results)
        
        # Get triggered symbols
        triggered_symbols = get_entry_signals(opening_range_results)
        
        logger.info(f"Opening range computed: {len(triggered_symbols)}/{len(symbols)} symbols triggered")
        
        if triggered_symbols:
            logger.info(f"Breakout signals: {', '.join(triggered_symbols[:5])}")
            if len(triggered_symbols) > 5:
                logger.info(f"... and {len(triggered_symbols) - 5} more")
        
        # Print dashboard with opening range
        print_dashboard({}, [], or_df)
        
        # Save opening range artifacts
        if save:
            # Load gate state if available
            gate_file = artifacts_dir / "gate.json"
            gate_state = {}
            if gate_file.exists():
                with open(gate_file, 'r') as f:
                    gate_state = json.load(f)
            
            # Save updated artifacts
            saved_files = save_analysis_artifacts(
                gate_state, [], opening_range_results, artifacts_dir
            )
            logger.info(f"Opening range artifacts saved: {saved_files.get('opening_range', 'N/A')}")
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Opening range analysis failed: {e}")
        sys.exit(1)


@app.command()
def report(
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config.yaml file"),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level")
):
    """
    Generate and display latest analysis report.
    
    Combines the latest gate state, candidates, and opening range data
    into a comprehensive dashboard report.
    """
    setup_logging(log_level)
    
    try:
        # Load configuration
        if config_path:
            cfg = load_config(config_path)
        else:
            cfg = get_default_config()
        
        logger.info("📊 Generating latest report...")
        
        # Find latest artifacts
        artifacts_base = Path(cfg.outputs.dir)
        if not artifacts_base.exists():
            logger.error(f"Artifacts directory not found: {artifacts_base}")
            sys.exit(1)
        
        # Get today's artifacts directory
        today_dir = artifacts_base / now_et().date().strftime("%Y-%m-%d")
        
        if not today_dir.exists():
            logger.error(f"No artifacts found for today: {today_dir}")
            logger.info("Run 'analyze' command first")
            sys.exit(1)
        
        # Load gate state
        gate_file = today_dir / "gate.json"
        gate_state = {}
        if gate_file.exists():
            import json
            with open(gate_file, 'r') as f:
                gate_state = json.load(f)
        
        # Load candidates
        candidates_file = today_dir / "candidates.json"
        candidates = []
        if candidates_file.exists():
            import json
            with open(candidates_file, 'r') as f:
                candidates_data = json.load(f)
                from .screen import Candidate
                candidates = [Candidate(**c) for c in candidates_data]
        
        # Load opening range
        or_file = today_dir / "opening_range.csv"
        or_df = None
        if or_file.exists():
            or_df = pd.read_csv(or_file, index_col='symbol')
        
        # Print comprehensive dashboard
        print_dashboard(gate_state, candidates, or_df)
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        sys.exit(1)


@app.command()
def create_config(
    output_path: str = typer.Option("config.yaml", "--output", "-o", help="Output path for config file")
):
    """Create a sample configuration file."""
    from .config import create_sample_config
    
    try:
        create_sample_config(output_path)
        typer.echo(f"✅ Sample configuration created: {output_path}")
        typer.echo("Edit the file and set your ALPACA_API_KEY and ALPACA_SECRET_KEY in .env")
    except Exception as e:
        typer.echo(f"❌ Error creating config: {e}")
        sys.exit(1)


if __name__ == "__main__":
    app()
