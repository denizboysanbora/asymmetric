"""
Reporting utilities for Qullamaggie.
Handles saving outputs and printing dashboards.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime
from loguru import logger

from .data import now_et
from .screen import Candidate


def save_json(payload: Dict[str, Any], path: str) -> None:
    """
    Save payload as JSON file.
    
    Args:
        payload: Data to save
        path: File path
    """
    try:
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path_obj, 'w') as f:
            json.dump(payload, f, indent=2, default=str)
        
        logger.info(f"Saved JSON to {path}")
    except Exception as e:
        logger.error(f"Error saving JSON to {path}: {e}")
        raise


def save_csv(df: pd.DataFrame, path: str) -> None:
    """
    Save DataFrame as CSV file.
    
    Args:
        df: DataFrame to save
        path: File path
    """
    try:
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(path_obj, index=True)
        logger.info(f"Saved CSV to {path}")
    except Exception as e:
        logger.error(f"Error saving CSV to {path}: {e}")
        raise


def candidates_to_dataframe(candidates: List[Candidate]) -> pd.DataFrame:
    """
    Convert candidates to DataFrame for CSV export.
    
    Args:
        candidates: List of Candidate objects
        
    Returns:
        DataFrame with candidate data
    """
    if not candidates:
        return pd.DataFrame()
    
    data = []
    for candidate in candidates:
        # Get setup information
        setup_names = [setup.setup for setup in candidate.setups]
        setup_scores = [setup.score for setup in candidate.setups]
        
        row = {
            'symbol': candidate.symbol,
            'adr_pct': candidate.adr_pct,
            'rs_score': candidate.rs_score,
            'setups': '; '.join(setup_names),
            'setup_scores': '; '.join([f"{score:.2f}" for score in setup_scores]),
            'setup_count': len(candidate.setups),
            'notes': '; '.join(candidate.notes),
            'atr': candidate.meta.get('atr', 0),
            'avg_volume': candidate.meta.get('avg_volume', 0),
            'latest_price': candidate.meta.get('latest_price', 0)
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    df = df.set_index('symbol')
    return df


def opening_range_to_dataframe(opening_range_results: Dict[str, Dict]) -> pd.DataFrame:
    """
    Convert opening range results to DataFrame for CSV export.
    
    Args:
        opening_range_results: Results from compute_opening_range()
        
    Returns:
        DataFrame with opening range data
    """
    if not opening_range_results:
        return pd.DataFrame()
    
    data = []
    for symbol, result in opening_range_results.items():
        row = {
            'symbol': symbol,
            'orh': result.get('orh'),
            'orl': result.get('orl'),
            'last_price': result.get('last_price'),
            'entry_triggered': result.get('entry_triggered', False),
            'or_start': result.get('or_start'),
            'or_end': result.get('or_end'),
            'or_bars': result.get('or_bars', 0)
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    df = df.set_index('symbol')
    return df


def create_artifacts_directory(base_dir: str = "artifacts") -> Path:
    """
    Create artifacts directory for today's date.
    
    Args:
        base_dir: Base artifacts directory
        
    Returns:
        Path to today's artifacts directory
    """
    today = now_et().date()
    artifacts_dir = Path(base_dir) / today.strftime("%Y-%m-%d")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    return artifacts_dir


def save_analysis_artifacts(
    gate_state: Dict[str, Any],
    candidates: List[Candidate],
    opening_range_results: Optional[Dict[str, Dict]] = None,
    artifacts_dir: Optional[Path] = None
) -> Dict[str, str]:
    """
    Save all analysis artifacts to files.
    
    Args:
        gate_state: Market gate state and metadata
        candidates: List of ranked candidates
        opening_range_results: Opening range results (optional)
        artifacts_dir: Artifacts directory path (optional)
        
    Returns:
        Dict mapping artifact type to file path
    """
    if artifacts_dir is None:
        artifacts_dir = create_artifacts_directory()
    
    saved_files = {}
    
    # Save gate state
    gate_path = artifacts_dir / "gate.json"
    save_json(gate_state, str(gate_path))
    saved_files['gate'] = str(gate_path)
    
    # Save candidates as CSV and JSON
    candidates_df = candidates_to_dataframe(candidates)
    if not candidates_df.empty:
        watchlist_path = artifacts_dir / "watchlist.csv"
        save_csv(candidates_df, str(watchlist_path))
        saved_files['watchlist'] = str(watchlist_path)
        
        candidates_json = [candidate.dict() for candidate in candidates]
        candidates_json_path = artifacts_dir / "candidates.json"
        save_json(candidates_json, str(candidates_json_path))
        saved_files['candidates'] = str(candidates_json_path)
    
    # Save opening range results
    if opening_range_results:
        or_df = opening_range_to_dataframe(opening_range_results)
        if not or_df.empty:
            or_path = artifacts_dir / "opening_range.csv"
            save_csv(or_df, str(or_path))
            saved_files['opening_range'] = str(or_path)
    
    # Create README for artifacts
    readme_path = artifacts_dir / "README.md"
    create_artifacts_readme(readme_path, saved_files)
    saved_files['readme'] = str(readme_path)
    
    logger.info(f"Saved {len(saved_files)} artifacts to {artifacts_dir}")
    return saved_files


def create_artifacts_readme(readme_path: Path, saved_files: Dict[str, str]) -> None:
    """
    Create README file explaining artifacts.
    
    Args:
        readme_path: Path to README file
        saved_files: Dict mapping artifact type to file path
    """
    readme_content = """# Qullamaggie Analysis Artifacts

Generated on: {timestamp}

## Files

""".format(timestamp=now_et().strftime("%Y-%m-%d %H:%M:%S ET"))
    
    if 'gate' in saved_files:
        readme_content += """### gate.json
Market gate state and QQQ EMA metadata:
- `gate_open`: Boolean indicating if market gate is open
- `ema_10`, `ema_20`: Current EMA values
- `ema_10_slope`, `ema_20_slope`: EMA slopes over lookback period
- `rising_lookback`: Number of days checked for rising EMAs
- `ema_10_rising`, `ema_20_rising`: Boolean indicators for rising EMAs
- `ema_10_above_20`: Boolean indicating EMA ordering

"""
    
    if 'watchlist' in saved_files:
        readme_content += """### watchlist.csv
Ranked candidate stocks with momentum characteristics:
- `symbol`: Stock symbol
- `adr_pct`: Average Daily Range percentage
- `rs_score`: Relative Strength score (0-1)
- `has_flag`: Has tight flag pattern
- `has_ep_gap`: Has EP-style gap catalyst
- `notes`: Analysis notes and exclusion reasons
- `atr`: Average True Range
- `avg_volume`: Average volume
- `latest_price`: Latest closing price

"""
    
    if 'candidates' in saved_files:
        readme_content += """### candidates.json
Full candidate data including all metadata and notes.

"""
    
    if 'opening_range' in saved_files:
        readme_content += """### opening_range.csv
Opening range analysis results:
- `symbol`: Stock symbol
- `orh`: Opening Range High (first 5 minutes)
- `orl`: Opening Range Low (first 5 minutes)
- `last_price`: Last available price
- `entry_triggered`: Boolean indicating if price > ORH
- `or_start`, `or_end`: Opening range time boundaries
- `or_bars`: Number of bars in opening range

"""
    
    readme_content += """## Analysis Summary

This analysis evaluates:
1. **Market Gate**: QQQ 10/20 EMA trend (both rising + EMA10 > EMA20)
2. **Momentum Scan**: ADR ≥5%, RS in top 90%, explosive leg ≥25%, tight flag pattern
3. **Gap Catalysts**: EP-style gaps ≥4% (when available)
4. **Opening Range**: First 5-minute high/low and breakout triggers

**Note**: This is analysis only - no trading orders are placed.
"""
    
    with open(readme_path, 'w') as f:
        f.write(readme_content)


def print_dashboard(
    gate_state: Dict[str, Any],
    candidates: List[Candidate],
    or_df: Optional[pd.DataFrame] = None
) -> None:
    """
    Print formatted dashboard to console.
    
    Args:
        gate_state: Market gate state and metadata
        candidates: List of ranked candidates
        or_df: Opening range DataFrame (optional)
    """
    print("=" * 80)
    print("🚀 QULLAMAGGIE MOMENTUM ANALYZER")
    print("=" * 80)
    print(f"Analysis Time: {now_et().strftime('%Y-%m-%d %H:%M:%S ET')}")
    print()
    
    # Market Gate Section
    print("📊 MARKET GATE (QQQ)")
    print("-" * 40)
    
    gate_open = gate_state.get('gate_open', False)
    ema_10 = gate_state.get('ema_10', 0)
    ema_20 = gate_state.get('ema_20', 0)
    ema_10_rising = gate_state.get('ema_10_rising', False)
    ema_20_rising = gate_state.get('ema_20_rising', False)
    close = gate_state.get('close', 0)
    
    status_icon = "🟢" if gate_open else "🔴"
    print(f"Gate Status: {status_icon} {'OPEN' if gate_open else 'CLOSED'}")
    print(f"QQQ Close: ${close:.2f}")
    print(f"EMA 10: ${ema_10:.2f} ({'↗' if ema_10_rising else '↘'})")
    print(f"EMA 20: ${ema_20:.2f} ({'↗' if ema_20_rising else '↘'})")
    print()
    
    # Candidates Section
    print("🎯 MOMENTUM CANDIDATES")
    print("-" * 40)
    
    if not candidates:
        print("No candidates found.")
    else:
        # Show top 15 candidates
        top_candidates = candidates[:15]
        
        print(f"{'Rank':<4} {'Symbol':<8} {'RS':<6} {'ADR':<6} {'Breakout':<8} {'EP':<8} {'Parabolic':<10} {'Price':<8} {'Notes'}")
        print("-" * 80)
        
        for i, candidate in enumerate(top_candidates, 1):
            # Get setup indicators
            breakout_icon = "✓" if any(s.setup == "Breakout" for s in candidate.setups) else "✗"
            ep_icon = "🚀" if any(s.setup == "Episodic Pivot" for s in candidate.setups) else "  "
            parabolic_icon = "📉" if any(s.setup == "Parabolic Long" for s in candidate.setups) else "  "
            
            price = candidate.meta.get('latest_price', 0)
            notes = candidate.notes[0] if candidate.notes else ""
            
            print(f"{i:<4} {candidate.symbol:<8} {candidate.rs_score:<6.2f} "
                  f"{candidate.adr_pct:<6.1f}% {breakout_icon:<8} {ep_icon:<8} {parabolic_icon:<10} "
                  f"${price:<7.2f} {notes}")
        
        print()
        print(f"Total candidates: {len(candidates)}")
        
        # Summary stats
        breakout_count = sum(1 for c in candidates for s in c.setups if s.setup == "Breakout")
        ep_count = sum(1 for c in candidates for s in c.setups if s.setup == "Episodic Pivot")
        parabolic_count = sum(1 for c in candidates for s in c.setups if s.setup == "Parabolic Long")
        
        avg_adr = sum(c.adr_pct for c in candidates) / len(candidates)
        avg_rs = sum(c.rs_score for c in candidates) / len(candidates)
        
        print(f"Breakout: {breakout_count} | EP: {ep_count} | Parabolic: {parabolic_count}")
        print(f"Avg ADR: {avg_adr:.1f}% | Avg RS: {avg_rs:.2f}")
    
    print()
    
    # Opening Range Section
    if or_df is not None and not or_df.empty:
        print("⚡ OPENING RANGE BREAKOUTS")
        print("-" * 40)
        
        triggered = or_df[or_df['entry_triggered'] == True]
        
        if not triggered.empty:
            print(f"{'Symbol':<8} {'ORH':<8} {'ORL':<8} {'Last':<8} {'Breakout':<9}")
            print("-" * 50)
            
            for symbol, row in triggered.iterrows():
                orh = row['orh']
                orl = row['orl']
                last = row['last_price']
                breakout_pct = ((last - orh) / orh * 100) if orh > 0 else 0
                
                print(f"{symbol:<8} ${orh:<7.2f} ${orl:<7.2f} ${last:<7.2f} +{breakout_pct:<7.2f}%")
            
            print()
            print(f"Breakout signals: {len(triggered)}/{len(or_df)} symbols")
        else:
            print("No opening range breakouts detected.")
    
    print("=" * 80)


def format_email_content(
    gate_state: Dict[str, Any],
    candidates: List[Candidate],
    opening_range_results: Optional[Dict[str, Dict]] = None
) -> str:
    """
    Format analysis results for email content.
    
    Args:
        gate_state: Market gate state and metadata
        candidates: List of ranked candidates
        opening_range_results: Opening range results (optional)
        
    Returns:
        Formatted email content string
    """
    content = []
    content.append("🚀 QULLAMAGGIE MOMENTUM ANALYSIS")
    content.append("=" * 50)
    content.append(f"Time: {now_et().strftime('%Y-%m-%d %H:%M:%S ET')}")
    content.append("")
    
    # Market Gate
    gate_open = gate_state.get('gate_open', False)
    ema_10 = gate_state.get('ema_10', 0)
    ema_20 = gate_state.get('ema_20', 0)
    
    status = "OPEN" if gate_open else "CLOSED"
    content.append(f"📊 MARKET GATE: {status}")
    content.append(f"QQQ EMA 10/20: ${ema_10:.2f} / ${ema_20:.2f}")
    content.append("")
    
    # Top Candidates
    if candidates:
        content.append("🎯 TOP CANDIDATES:")
        top_5 = candidates[:5]
        
        for i, candidate in enumerate(top_5, 1):
            ep_indicator = " 🚀" if candidate.has_ep_gap else ""
            price = candidate.meta.get('latest_price', 0)
            content.append(f"{i}. {candidate.symbol} (RS: {candidate.rs_score:.2f}, ADR: {candidate.adr_pct:.1f}%, ${price:.2f}){ep_indicator}")
        
        content.append("")
        content.append(f"Total candidates: {len(candidates)}")
        
        ep_gaps = sum(1 for c in candidates if c.has_ep_gap)
        content.append(f"EP gaps: {ep_gaps}")
    
    # Opening Range Breakouts
    if opening_range_results:
        triggered = [s for s, r in opening_range_results.items() if r.get('entry_triggered', False)]
        if triggered:
            content.append("")
            content.append("⚡ OPENING RANGE BREAKOUTS:")
            for symbol in triggered[:5]:  # Show top 5
                result = opening_range_results[symbol]
                orh = result.get('orh', 0)
                last = result.get('last_price', 0)
                breakout_pct = ((last - orh) / orh * 100) if orh > 0 else 0
                content.append(f"• {symbol}: +{breakout_pct:.1f}% above ORH ${orh:.2f}")
    
    content.append("")
    content.append("Note: Analysis only - no trading orders placed.")
    
    return "\n".join(content)
