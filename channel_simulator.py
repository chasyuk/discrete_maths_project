"""
channel_simulator.py — Communication Channel Simulator
═══════════════════════════════════════════════════════
Simulates various error channels for testing Reed-Solomon codes:
- Burst error channel (contiguous symbol errors)
- Random error channel (uniformly distributed errors)
- Mixed error channel (combination of burst and random)

Includes Monte Carlo simulation for performance analysis.
"""

import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChannelStats:
    """Statistics from a channel error injection."""
    original: list = field(default_factory=list)
    corrupted: list = field(default_factory=list)
    error_positions: list = field(default_factory=list)
    error_values: dict = field(default_factory=dict)
    burst_ranges: list = field(default_factory=list)
    num_errors: int = 0
    symbol_error_rate: float = 0.0


class BurstErrorChannel:
    """
    Simulates a channel with burst (contiguous) errors.

    Burst errors are common in real-world scenarios:
    - Scratches on CDs/DVDs
    - Fading in wireless channels
    - Interference pulses in satellite communication
    """

    def __init__(self, burst_length: int = 5, num_bursts: int = 1, seed: Optional[int] = None):
        """
        Parameters
        ----------
        burst_length : int
            Length of each contiguous error burst.
        num_bursts : int
            Number of separate bursts to inject.
        seed : int, optional
            Random seed for reproducibility.
        """
        self.burst_length = burst_length
        self.num_bursts = num_bursts
        self.rng = random.Random(seed)

    def transmit(self, codeword: list) -> ChannelStats:
        """Inject burst errors into the codeword."""
        n = len(codeword)
        corrupted = list(codeword)
        all_error_positions = []
        error_values = {}
        burst_ranges = []

        for _ in range(self.num_bursts):
            # Random burst start position
            max_start = n - self.burst_length
            if max_start <= 0:
                start = 0
            else:
                start = self.rng.randint(0, max_start)

            end = min(start + self.burst_length, n)
            burst_ranges.append((start, end))

            for i in range(start, end):
                if i not in all_error_positions:
                    original_val = corrupted[i]
                    # Corrupt with random non-zero XOR
                    error_mask = self.rng.randint(1, 255)
                    corrupted[i] ^= error_mask
                    error_values[i] = (original_val, corrupted[i])
                    all_error_positions.append(i)

        all_error_positions.sort()

        return ChannelStats(
            original=list(codeword),
            corrupted=corrupted,
            error_positions=all_error_positions,
            error_values=error_values,
            burst_ranges=burst_ranges,
            num_errors=len(all_error_positions),
            symbol_error_rate=len(all_error_positions) / n,
        )


class RandomErrorChannel:
    """
    Simulates a channel with uniformly random symbol errors.
    """

    def __init__(self, num_errors: int = 5, seed: Optional[int] = None):
        self.num_errors = num_errors
        self.rng = random.Random(seed)

    def transmit(self, codeword: list) -> ChannelStats:
        """Inject random errors at random positions."""
        n = len(codeword)
        corrupted = list(codeword)
        error_values = {}

        positions = self.rng.sample(range(n), min(self.num_errors, n))
        positions.sort()

        for pos in positions:
            original_val = corrupted[pos]
            error_mask = self.rng.randint(1, 255)
            corrupted[pos] ^= error_mask
            error_values[pos] = (original_val, corrupted[pos])

        return ChannelStats(
            original=list(codeword),
            corrupted=corrupted,
            error_positions=positions,
            error_values=error_values,
            burst_ranges=[],
            num_errors=len(positions),
            symbol_error_rate=len(positions) / n,
        )


class MixedErrorChannel:
    """
    Simulates a channel with both burst and random errors.
    """

    def __init__(self, burst_length: int = 4, num_bursts: int = 1,
                 num_random: int = 3, seed: Optional[int] = None):
        self.burst_channel = BurstErrorChannel(burst_length, num_bursts, seed)
        self.random_channel = RandomErrorChannel(num_random, seed + 1 if seed else None)

    def transmit(self, codeword: list) -> ChannelStats:
        """Inject both burst and random errors."""
        # Apply burst errors first
        burst_stats = self.burst_channel.transmit(codeword)
        # Then apply random errors to already-corrupted codeword
        random_stats = self.random_channel.transmit(burst_stats.corrupted)

        # Merge statistics
        all_positions = sorted(set(burst_stats.error_positions + random_stats.error_positions))
        all_values = {**burst_stats.error_values}
        for pos, val in random_stats.error_values.items():
            if pos not in all_values:
                all_values[pos] = (codeword[pos], random_stats.corrupted[pos])
            else:
                all_values[pos] = (codeword[pos], random_stats.corrupted[pos])

        return ChannelStats(
            original=list(codeword),
            corrupted=random_stats.corrupted,
            error_positions=all_positions,
            error_values=all_values,
            burst_ranges=burst_stats.burst_ranges,
            num_errors=len(all_positions),
            symbol_error_rate=len(all_positions) / len(codeword),
        )


class MonteCarloSimulator:
    """
    Monte Carlo simulator for RS code performance analysis.

    Runs multiple trials to measure correction success rate
    as a function of error count and type.
    """

    def __init__(self, rs_codec, num_trials: int = 100):
        self.rs = rs_codec
        self.num_trials = num_trials

    def run_random_error_sweep(self, message: list,
                               error_range: range = None) -> dict:
        """
        Sweep over different numbers of random errors.
        Returns {num_errors: success_rate}.
        """
        if error_range is None:
            error_range = range(1, self.rs.nsym + 5)

        codeword = self.rs.encode(message)
        results = {}

        for num_errors in error_range:
            successes = 0
            for trial in range(self.num_trials):
                channel = RandomErrorChannel(num_errors, seed=trial * 1000 + num_errors)
                stats = channel.transmit(codeword)
                try:
                    decoded, _ = self.rs.decode(stats.corrupted)
                    if decoded == message:
                        successes += 1
                except (ValueError, ZeroDivisionError):
                    pass
            results[num_errors] = successes / self.num_trials

        return results

    def run_burst_error_sweep(self, message: list,
                              burst_lengths: range = None) -> dict:
        """
        Sweep over different burst lengths.
        Returns {burst_length: success_rate}.
        """
        if burst_lengths is None:
            burst_lengths = range(1, self.rs.nsym + 5)

        codeword = self.rs.encode(message)
        results = {}

        for burst_len in burst_lengths:
            successes = 0
            for trial in range(self.num_trials):
                channel = BurstErrorChannel(burst_len, num_bursts=1, seed=trial * 1000 + burst_len)
                stats = channel.transmit(codeword)
                try:
                    decoded, _ = self.rs.decode(stats.corrupted)
                    if decoded == message:
                        successes += 1
                except (ValueError, ZeroDivisionError):
                    pass
            results[burst_len] = successes / self.num_trials

        return results


if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    console.print(Panel.fit(
        "[bold cyan]Channel Simulator Demo[/bold cyan]",
        border_style="bright_blue"
    ))

    # Quick demo
    data = list(range(50))
    console.print(f"\n[bold]Test data:[/bold] {data[:20]}...")

    burst = BurstErrorChannel(burst_length=8, num_bursts=1, seed=42)
    stats = burst.transmit(data)
    console.print(f"\n[bold red]Burst errors:[/bold red] {stats.num_errors} errors")
    console.print(f"[dim]Burst ranges: {stats.burst_ranges}[/dim]")
    console.print(f"[dim]Error positions: {stats.error_positions}[/dim]")
    console.print(f"[dim]SER: {stats.symbol_error_rate:.2%}[/dim]")
