"""
comparison.py — Reed-Solomon vs BCH Code Comparison
════════════════════════════════════════════════════
Implements a simplified BCH encoder/decoder for comparison with Reed-Solomon.
Generates detailed performance and complexity analysis.
"""

import time
import numpy as np
from rs_codec import ReedSolomonCodec
from gf256 import gf
from channel_simulator import RandomErrorChannel, BurstErrorChannel


class SimpleBCHCodec:
    """
    Simplified BCH(n, k, t) encoder/decoder over GF(2).

    This is a binary BCH code implementation for comparison purposes.
    Uses a generator polynomial approach.

    BCH(255, 223, 4) — binary code, corrects up to 4 bit errors.
    """

    def __init__(self, n: int = 255, k: int = 223, t: int = 4):
        """
        Parameters
        ----------
        n : int
            Codeword length (usually 2^m - 1).
        k : int
            Message length.
        t : int
            Error correction capability (bits).
        """
        self.n = n
        self.k = k
        self.t = t
        self.nsym = n - k
        self.generator = self._build_generator()

    def _build_generator(self) -> list:
        """
        Build BCH generator polynomial.
        Uses minimal polynomials of α, α², ..., α^(2t).
        Simplified: uses RS-like generator over GF(2⁸) as approximation.
        """
        g = [1]
        for i in range(2 * self.t):
            g = gf.poly_mul(g, [gf.exp_table[i], 1])
        return g

    def encode(self, message: list) -> list:
        """Encode message using BCH encoding (similar structure to RS)."""
        if len(message) > self.k:
            raise ValueError(f"Message too long: {len(message)} > {self.k}")

        # Pad message to k length
        padded = list(message) + [0] * (self.k - len(message))

        # Systematic encoding
        msg_shifted = [0] * self.nsym + padded
        _, remainder = gf.poly_div(msg_shifted, self.generator)

        while len(remainder) < self.nsym:
            remainder.append(0)

        return remainder[:self.nsym] + padded

    def decode(self, received: list) -> tuple:
        """
        Decode BCH codeword.
        Uses syndrome-based decoding (simplified).
        """
        # Calculate syndromes
        syndromes = []
        for i in range(2 * self.t):
            s = gf.poly_eval(received, gf.exp_table[i])
            syndromes.append(s)

        if all(s == 0 for s in syndromes):
            return received[self.nsym:], 0

        # Use Berlekamp-Massey (same as RS for simplicity)
        # In practice BCH uses a binary-optimized version
        rs_temp = ReedSolomonCodec(nsym=2 * self.t)
        try:
            err_locator = rs_temp._berlekamp_massey(syndromes)
            num_errors = len(err_locator) - 1

            if num_errors > self.t:
                raise ValueError("Too many errors")

            err_positions = rs_temp._chien_search(err_locator, len(received))

            if len(err_positions) != num_errors:
                raise ValueError("Decoding failure")

            corrected = list(received)
            err_magnitudes = rs_temp._forney(syndromes, err_locator, err_positions, len(received))
            for pos, mag in zip(err_positions, err_magnitudes):
                corrected[pos] = gf.add(corrected[pos], mag)

            return corrected[self.nsym:], num_errors
        except (ValueError, ZeroDivisionError):
            raise ValueError("BCH decoding failure")


def run_comparison(message_length: int = 50, num_trials: int = 50) -> dict:
    """
    Run comprehensive RS vs BCH comparison.

    Returns a dictionary with all comparison metrics.
    """
    # Configuration
    rs_nsym = 32  # RS(n, n-32) — 16 symbol errors
    bch_t = 4     # BCH — 4 symbol errors (conceptual)

    rs = ReedSolomonCodec(nsym=rs_nsym)
    bch = SimpleBCHCodec(n=255, k=223, t=bch_t)

    # Generate test message
    np.random.seed(42)
    message = list(np.random.randint(0, 256, message_length).astype(int))

    # ── Timing: Encoding ──────────────────────────────────────────────
    # RS Encoding
    times = []
    for _ in range(num_trials):
        start = time.perf_counter()
        rs_codeword = rs.encode(message)
        times.append((time.perf_counter() - start) * 1000)
    rs_encode_time = np.mean(times)

    # BCH Encoding
    times = []
    for _ in range(num_trials):
        start = time.perf_counter()
        bch_codeword = bch.encode(message)
        times.append((time.perf_counter() - start) * 1000)
    bch_encode_time = np.mean(times)

    # ── Timing: Decoding (with errors) ────────────────────────────────
    channel = RandomErrorChannel(num_errors=5, seed=42)

    # RS Decoding
    rs_stats = channel.transmit(rs_codeword)
    times = []
    for _ in range(num_trials):
        start = time.perf_counter()
        try:
            rs.decode(rs_stats.corrupted)
        except Exception:
            pass
        times.append((time.perf_counter() - start) * 1000)
    rs_decode_time = np.mean(times)

    # BCH Decoding
    bch_channel = RandomErrorChannel(num_errors=3, seed=42)
    bch_stats = bch_channel.transmit(bch_codeword)
    times = []
    for _ in range(num_trials):
        start = time.perf_counter()
        try:
            bch.decode(bch_stats.corrupted)
        except Exception:
            pass
        times.append((time.perf_counter() - start) * 1000)
    bch_decode_time = np.mean(times)

    # ── Efficiency Metrics ────────────────────────────────────────────
    rs_n = len(rs_codeword)
    rs_k = len(message)
    bch_n = len(bch_codeword)
    bch_k = len(message)

    results = {
        # Timing
        'rs_encode_time': rs_encode_time,
        'rs_decode_time': rs_decode_time,
        'bch_encode_time': bch_encode_time,
        'bch_decode_time': bch_decode_time,

        # Efficiency
        'rs_redundancy': (rs_nsym / rs_n) * 100,
        'rs_code_rate': rs_k / rs_n,
        'bch_redundancy': (bch.nsym / bch_n) * 100,
        'bch_code_rate': bch_k / bch_n,

        # Correction capability
        'rs_symbol_correction': rs_nsym // 2,
        'rs_burst_correction': rs_nsym,  # can handle burst up to nsym
        'bch_bit_correction': bch_t,
        'bch_burst_correction': bch_t,  # limited burst correction

        # Code parameters
        'rs_n': rs_n,
        'rs_k': rs_k,
        'rs_nsym': rs_nsym,
        'bch_n': bch_n,
        'bch_k': bch_k,
        'bch_nsym': bch.nsym,
        'bch_t': bch_t,

        # Complexity
        'rs_encode_complexity': f'O(n × (n-k))',
        'rs_decode_complexity': f'O(n² + (n-k)²)',
        'bch_encode_complexity': f'O(n × (n-k))',
        'bch_decode_complexity': f'O(n × t²)',
    }

    return results


def format_comparison_table(results: dict) -> str:
    """Format comparison results as a markdown table."""
    lines = [
        "# Reed-Solomon vs BCH Code Comparison\n",
        "| Metric | Reed-Solomon | BCH |",
        "|--------|-------------|-----|",
        f"| **Code Parameters** | RS({results['rs_n']}, {results['rs_k']}) | BCH({results['bch_n']}, {results['bch_k']}) |",
        f"| Parity Symbols | {results['rs_nsym']} | {results['bch_nsym']} |",
        f"| Code Rate | {results['rs_code_rate']:.3f} | {results['bch_code_rate']:.3f} |",
        f"| Redundancy | {results['rs_redundancy']:.1f}% | {results['bch_redundancy']:.1f}% |",
        f"| **Error Correction** | | |",
        f"| Symbol Errors | {results['rs_symbol_correction']} | {results['bch_bit_correction']} |",
        f"| Burst Error Capability | Up to {results['rs_burst_correction']} symbols | Up to {results['bch_burst_correction']} bits |",
        f"| **Performance** | | |",
        f"| Encode Time | {results['rs_encode_time']:.3f} ms | {results['bch_encode_time']:.3f} ms |",
        f"| Decode Time | {results['rs_decode_time']:.3f} ms | {results['bch_decode_time']:.3f} ms |",
        f"| **Complexity** | | |",
        f"| Encoding | {results['rs_encode_complexity']} | {results['bch_encode_complexity']} |",
        f"| Decoding | {results['rs_decode_complexity']} | {results['bch_decode_complexity']} |",
        "",
        "## Key Differences\n",
        "| Feature | Reed-Solomon | BCH |",
        "|---------|-------------|-----|",
        "| Symbol Size | Multi-bit (byte) | Single bit |",
        "| Burst Errors | Excellent | Limited |",
        "| Random Bit Errors | Good | Excellent |",
        "| Applications | QR, CD/DVD, Space | Flash memory, WiFi |",
        "| Implementation | More complex | Simpler |",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel

    console = Console()
    console.print(Panel.fit(
        "[bold cyan]RS vs BCH Comparison[/bold cyan]",
        border_style="bright_blue"
    ))

    results = run_comparison()

    table = Table(title="RS vs BCH Comparison", border_style="bright_blue")
    table.add_column("Metric", style="cyan", min_width=20)
    table.add_column("Reed-Solomon", style="green")
    table.add_column("BCH", style="yellow")

    table.add_row("Code", f"RS({results['rs_n']},{results['rs_k']})",
                  f"BCH({results['bch_n']},{results['bch_k']})")
    table.add_row("Code Rate", f"{results['rs_code_rate']:.3f}",
                  f"{results['bch_code_rate']:.3f}")
    table.add_row("Redundancy", f"{results['rs_redundancy']:.1f}%",
                  f"{results['bch_redundancy']:.1f}%")
    table.add_row("Symbol Errors Fixed", str(results['rs_symbol_correction']),
                  str(results['bch_bit_correction']))
    table.add_row("Burst Capability", f"{results['rs_burst_correction']} sym",
                  f"{results['bch_burst_correction']} bits")
    table.add_row("Encode Time", f"{results['rs_encode_time']:.3f} ms",
                  f"{results['bch_encode_time']:.3f} ms")
    table.add_row("Decode Time", f"{results['rs_decode_time']:.3f} ms",
                  f"{results['bch_decode_time']:.3f} ms")

    console.print(table)
    console.print(f"\n[dim]Advantage:[/dim] RS excels at burst errors (QR, CD/DVD, space); "
                  f"BCH better for random bit errors (flash, WiFi)")
