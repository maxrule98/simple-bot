"""Signal types and data structures for trading decisions."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class SignalType(Enum):
    """Type of trading signal."""

    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"  # Close entire position
    PARTIAL_CLOSE = "partial_close"  # Close percentage of position


class SignalSource(Enum):
    """Source that generated the signal."""

    TECHNICAL = "technical"  # Technical indicators (RSI, MACD, BB, etc.)
    ML_MODEL = "ml_model"  # Machine learning model prediction
    ORDERBOOK = "orderbook"  # Order book analysis (bid/ask imbalance)
    MANUAL = "manual"  # Manual override signal


@dataclass
class Signal:
    """
    Rich signal object containing trading decision and context.

    Attributes:
        type: Type of signal (BUY, SELL, CLOSE, PARTIAL_CLOSE)
        source: Source that generated this signal
        confidence: Confidence level (0.0 to 1.0)
        reason: Human-readable explanation
        metadata: Additional context (indicator values, model outputs, etc.)
        close_percentage: For PARTIAL_CLOSE, percentage to close (0.0 to 1.0)
        timestamp: Signal generation timestamp (milliseconds)
    """

    type: SignalType
    source: SignalSource
    confidence: float
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    close_percentage: Optional[float] = None  # For PARTIAL_CLOSE only
    timestamp: Optional[int] = None  # Will be set by generator if not provided

    def __post_init__(self):
        """Validate signal attributes."""
        # Validate confidence
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")

        # Validate close_percentage for PARTIAL_CLOSE
        if self.type == SignalType.PARTIAL_CLOSE:
            if self.close_percentage is None:
                raise ValueError("close_percentage required for PARTIAL_CLOSE signal")
            if not 0.0 < self.close_percentage <= 1.0:
                raise ValueError(
                    f"close_percentage must be 0.0-1.0, got {self.close_percentage}"
                )

        # Set timestamp if not provided
        if self.timestamp is None:
            import time

            self.timestamp = int(time.time() * 1000)

    def __repr__(self) -> str:
        """Pretty string representation."""
        parts = [
            f"{self.type.value.upper()}",
            f"confidence={self.confidence:.2f}",
            f'source={self.source.value}',
            f'reason="{self.reason}"',
        ]
        if self.close_percentage:
            parts.append(f"close_pct={self.close_percentage:.1%}")
        return f"Signal({', '.join(parts)})"
