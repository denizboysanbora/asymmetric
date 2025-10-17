"""
Stock screening logic for Qullamaggie.
Builds candidates based on the three timeless momentum setups.
"""
from typing import List, Dict, Optional
import pandas as pd
from pydantic import BaseModel, Field
from loguru import logger

from .features import adr_pct, rs_score, calculate_atr, calculate_volume_profile
from .setups import detect_all_setups, rank_setups, SetupTag
from .config import Config


class Candidate(BaseModel):
    """Stock candidate model."""
    symbol: str = Field(..., description="Stock symbol")
    adr_pct: float = Field(..., description="Average Daily Range percentage")
    rs_score: float = Field(..., description="Relative Strength score (0-1)")
    setups: List[SetupTag] = Field(default_factory=list, description="Detected setups")
    notes: List[str] = Field(default_factory=list, description="Analysis notes")
    meta: Dict = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        extra = "allow"


def build_candidates(
    daily_df: pd.DataFrame, 
    premarket_df: pd.DataFrame, 
    minute_df: Optional[pd.DataFrame],
    cfg: Config,
    gate_open: bool = True
) -> List[Candidate]:
    """
    Build candidate list by detecting the three timeless momentum setups.
    
    Args:
        daily_df: Daily bars DataFrame with MultiIndex [symbol, date]
        premarket_df: Premarket stats DataFrame
        minute_df: Intraday minute bars (optional)
        cfg: Configuration object
        
    Returns:
        List of Candidate objects
    """
    if daily_df.empty:
        logger.warning("No daily data provided for screening")
        return []
    
    candidates = []
    symbols = daily_df.index.get_level_values('symbol').unique()
    
    logger.info(f"Screening {len(symbols)} symbols for momentum setups")
    
    if not gate_open:
        logger.info("Market gate is CLOSED (QQQ 10/20 EMA). Listing candidates as FYI only.")
    
    # Calculate base features for all symbols
    adr_values = adr_pct(daily_df, window=20)
    rs_values = rs_score(daily_df, periods=[21, 63, 126])
    atr_values = calculate_atr(daily_df)
    volume_profile = calculate_volume_profile(daily_df)
    
    # Process each symbol
    for symbol in symbols:
        notes = []
        
        try:
            # Get symbol data
            symbol_daily = daily_df.xs(symbol, level=0)
            
            # Add gate status note
            if not gate_open:
                notes.append("Gate CLOSED")
            
            # Check ADR requirement
            adr = adr_values.get(symbol, 0)
            if pd.isna(adr) or adr < cfg.scan.adr_min_pct:
                notes.append(f"ADR {adr:.1f}% < {cfg.scan.adr_min_pct}%")
                continue
            
            # Check RS score
            rs = rs_values.get(symbol, 0)
            if pd.isna(rs) or rs < cfg.scan.rs_top_percentile:
                notes.append(f"RS {rs:.2f} < {cfg.scan.rs_top_percentile}")
                continue
            
            # Detect all setups for this symbol
            setups = detect_all_setups(daily_df, premarket_df, minute_df, cfg, symbol)
            
            # Only include symbols with at least one setup detected
            if not setups:
                notes.append("No setups detected")
                continue
            
            # Rank setups by priority
            setups = rank_setups(setups)
            
            # Additional metadata
            atr = atr_values.get(symbol, 0)
            avg_volume = volume_profile.get(symbol, 0)
            latest_price = symbol_daily['close'].iloc[-1]
            
            meta = {
                "atr": atr,
                "avg_volume": int(avg_volume) if not pd.isna(avg_volume) else 0,
                "latest_price": latest_price,
                "adr": adr,
                "rs": rs,
                "setup_count": len(setups)
            }
            
            # Add setup-specific notes
            setup_names = [setup.setup for setup in setups]
            notes.append(f"Setups: {', '.join(setup_names)}")
            
            candidate = Candidate(
                symbol=symbol,
                adr_pct=adr,
                rs_score=rs,
                setups=setups,
                notes=notes,
                meta=meta
            )
            
            candidates.append(candidate)
            
            setup_summary = ", ".join([f"{s.setup}({s.score:.2f})" for s in setups])
            logger.debug(f"Added candidate: {symbol} (ADR: {adr:.1f}%, RS: {rs:.2f}, Setups: {setup_summary})")
            
        except Exception as e:
            logger.warning(f"Error processing symbol {symbol}: {e}")
            continue
    
    logger.info(f"Found {len(candidates)} candidates with setups")
    return candidates


def rank_candidates(candidates: List[Candidate]) -> List[Candidate]:
    """
    Rank candidates by priority: EP > Breakout > Parabolic Long > RS > ADR.
    
    Args:
        candidates: List of Candidate objects
        
    Returns:
        Ranked list of Candidate objects
    """
    if not candidates:
        return candidates
    
    def get_priority_score(candidate):
        """Calculate priority score for ranking."""
        priority_score = 0
        setup_priorities = {"Qullamaggie Episodic Pivot": 3, "Qullamaggie Breakout": 2, "Qullamaggie Parabolic Long": 1}
        
        # Get highest priority setup
        if candidate.setups:
            highest_priority = max([setup_priorities.get(s.setup, 0) for s in candidate.setups])
            priority_score = highest_priority
        
        # Secondary ranking by RS and ADR
        rs_score = candidate.rs_score
        adr_score = candidate.adr_pct / 20  # Normalize ADR to 0-1 scale
        
        return (priority_score, rs_score, adr_score)
    
    # Sort by priority: EP > Breakout > Parabolic Long > RS desc > ADR desc
    ranked = sorted(
        candidates,
        key=get_priority_score,
        reverse=True
    )
    
    logger.info(f"Ranked {len(ranked)} candidates (Qullamaggie Episodic Pivot > Qullamaggie Breakout > Qullamaggie Parabolic Long > RS > ADR)")
    return ranked


def filter_candidates_by_volume(
    candidates: List[Candidate], 
    min_volume: int = 100000
) -> List[Candidate]:
    """
    Filter candidates by minimum volume requirement.
    
    Args:
        candidates: List of Candidate objects
        min_volume: Minimum average volume
        
    Returns:
        Filtered list of Candidate objects
    """
    filtered = []
    
    for candidate in candidates:
        avg_volume = candidate.meta.get('avg_volume', 0)
        if avg_volume >= min_volume:
            filtered.append(candidate)
        else:
            logger.debug(f"Filtered out {candidate.symbol}: volume {avg_volume} < {min_volume}")
    
    logger.info(f"Volume filter: {len(filtered)}/{len(candidates)} candidates remain")
    return filtered


def get_top_candidates(candidates: List[Candidate], limit: int = 15) -> List[Candidate]:
    """
    Get top N candidates from ranked list.
    
    Args:
        candidates: List of ranked Candidate objects
        limit: Maximum number of candidates to return
        
    Returns:
        Top N candidates
    """
    return candidates[:limit]


def summarize_screening_results(candidates: List[Candidate]) -> Dict:
    """
    Generate summary statistics for screening results.
    
    Args:
        candidates: List of Candidate objects
        
    Returns:
        Dictionary with summary statistics
    """
    if not candidates:
        return {
            "total_candidates": 0,
            "breakout_setups": 0,
            "ep_setups": 0,
            "parabolic_long_setups": 0,
            "avg_adr": 0,
            "avg_rs": 0,
            "avg_price": 0
        }
    
    # Count setups
    breakout_count = sum(1 for c in candidates for s in c.setups if s.setup == "Qullamaggie Breakout")
    ep_count = sum(1 for c in candidates for s in c.setups if s.setup == "Qullamaggie Episodic Pivot")
    parabolic_long_count = sum(1 for c in candidates for s in c.setups if s.setup == "Qullamaggie Parabolic Long")
    
    avg_adr = sum(c.adr_pct for c in candidates) / len(candidates)
    avg_rs = sum(c.rs_score for c in candidates) / len(candidates)
    avg_price = sum(c.meta.get('latest_price', 0) for c in candidates) / len(candidates)
    
    return {
        "total_candidates": len(candidates),
        "breakout_setups": breakout_count,
        "ep_setups": ep_count,
        "parabolic_long_setups": parabolic_long_count,
        "avg_adr": avg_adr,
        "avg_rs": avg_rs,
        "avg_price": avg_price,
        "setup_distribution": {
            "breakout_pct": (breakout_count / len(candidates)) * 100 if candidates else 0,
            "ep_pct": (ep_count / len(candidates)) * 100 if candidates else 0,
            "parabolic_long_pct": (parabolic_long_count / len(candidates)) * 100 if candidates else 0
        }
    }
