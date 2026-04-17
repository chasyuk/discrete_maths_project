"""
main.py — Reed-Solomon Codes Project — Main Entry Point
════════════════════════════════════════════════════════
Provides a CLI interface with rich console output for all project features.

Usage:
    python main.py encode       — Encode a message
    python main.py decode       — Decode a codeword
    python main.py simulate     — Run channel simulation
    python main.py qr-demo      — Run QR code demonstration
    python main.py compare      — Run RS vs BCH comparison
    python main.py full-demo    — Run everything
"""

import argparse
import sys
import time
import numpy as np
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.markdown import Markdown
from rich import box

from gf256 import gf
from rs_codec import ReedSolomonCodec
from channel_simulator import (
    BurstErrorChannel, RandomErrorChannel, MixedErrorChannel,
    MonteCarloSimulator
)
from visualizer import RSVisualizer


console = Console()

# ═══════════════════════════════════════════════════════════════════════
#  BANNER
# ═══════════════════════════════════════════════════════════════════════

BANNER = """[bold cyan]
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ██████╗ ███████╗    ██████╗ ██████╗ ██████╗ ███████╗       ║
║   ██╔══██╗██╔════╝   ██╔════╝██╔═══██╗██╔══██╗██╔════╝      ║
║   ██████╔╝███████╗   ██║     ██║   ██║██║  ██║█████╗         ║
║   ██╔══██╗╚════██║   ██║     ██║   ██║██║  ██║██╔══╝         ║
║   ██║  ██║███████║   ╚██████╗╚██████╔╝██████╔╝███████╗      ║
║   ╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝     ║
║                                                              ║
║          Reed-Solomon Error Correction Codes                 ║
║          ─────────────────────────────────────               ║
║          GF(2⁸) • Berlekamp-Massey • Forney                 ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
[/bold cyan]"""


def print_banner():
    console.print(BANNER)


def print_section(title: str, icon: str = "►"):
    console.print(f"\n[bold bright_blue]{icon} {title}[/bold bright_blue]")
    console.print("─" * 60)


# ═══════════════════════════════════════════════════════════════════════
#  COMMANDS
# ═══════════════════════════════════════════════════════════════════════

def cmd_encode(args):
    """Encode a text message with Reed-Solomon."""
    print_section("Reed-Solomon Encoding", "🔐")

    text = args.message or "Hello, Reed-Solomon!"
    nsym = args.nsym

    rs = ReedSolomonCodec(nsym=nsym)
    message = list(text.encode('utf-8'))

    console.print(f"[bold]Input text:[/bold] \"{text}\"")
    console.print(f"[dim]Message bytes ({len(message)}):[/dim] {message[:30]}{'...' if len(message) > 30 else ''}")
    console.print(f"[dim]RS parameters:[/dim] nsym={nsym}, t={nsym//2}")

    start = time.perf_counter()
    codeword = rs.encode(message)
    elapsed = (time.perf_counter() - start) * 1000

    table = Table(title="Encoding Result", border_style="bright_blue", box=box.ROUNDED)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Message length", f"{len(message)} symbols")
    table.add_row("Codeword length", f"{len(codeword)} symbols")
    table.add_row("Parity symbols", f"{nsym}")
    table.add_row("Code rate", f"{len(message)/len(codeword):.3f}")
    table.add_row("Error capacity", f"up to {nsym//2} symbol errors")
    table.add_row("Encoding time", f"{elapsed:.3f} ms")
    console.print(table)

    console.print(f"\n[dim]Codeword:[/dim] {codeword[:20]}... ({len(codeword)} symbols)")
    return codeword


def cmd_decode(args):
    """Demonstrate decoding with error injection."""
    print_section("Reed-Solomon Decoding with Error Correction", "🔓")

    text = args.message or "Hello, Reed-Solomon!"
    nsym = args.nsym
    num_errors = args.errors

    rs = ReedSolomonCodec(nsym=nsym)
    message = list(text.encode('utf-8'))
    codeword = rs.encode(message)

    console.print(f"[bold]Original:[/bold] \"{text}\"")
    console.print(f"[dim]Codeword length: {len(codeword)} | Correction capacity: {nsym//2} errors[/dim]")

    # Inject errors
    np.random.seed(args.seed)
    corrupted = list(codeword)
    error_positions = sorted(np.random.choice(len(corrupted), min(num_errors, len(corrupted)), replace=False))
    for pos in error_positions:
        corrupted[pos] ^= np.random.randint(1, 256)

    console.print(f"\n[bold red]Injected {len(error_positions)} errors[/bold red] at: {list(error_positions)}")

    # Decode
    try:
        start = time.perf_counter()
        decoded, errors_fixed, info = rs.decode(corrupted, return_info=True)
        elapsed = (time.perf_counter() - start) * 1000

        decoded_text = bytes(decoded).decode('utf-8')

        table = Table(title="Decoding Result", border_style="bright_green", box=box.ROUNDED)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Errors injected", str(len(error_positions)))
        table.add_row("Errors corrected", str(errors_fixed))
        table.add_row("Recovered text", f'"{decoded_text}"')
        table.add_row("Perfect match?", "✓ Yes" if decoded == message else "✗ No")
        table.add_row("Decoding time", f"{elapsed:.3f} ms")
        table.add_row("Error positions found", str(info['error_positions']))
        console.print(table)

    except ValueError as e:
        console.print(f"[bold red]✗ Decoding failed:[/bold red] {e}")
        console.print(f"[dim]({len(error_positions)} errors exceeds capacity of {nsym//2})[/dim]")


def cmd_simulate(args):
    """Run channel simulation with visualizations."""
    print_section("Channel Simulation", "📡")

    nsym = args.nsym
    rs = ReedSolomonCodec(nsym=nsym)
    message = list(b"The quick brown fox jumps over the lazy dog! RS codes are amazing.")
    codeword = rs.encode(message)

    console.print(f"[bold]Message:[/bold] \"{bytes(message).decode()}\"")
    console.print(f"[dim]RS({len(codeword)}, {len(message)}), t={nsym//2}[/dim]")

    viz = RSVisualizer(args.output)

    # ── 1. Encoding pipeline ──────────────────────────────────────────
    console.print("\n[cyan]1.[/cyan] Generating encoding pipeline visualization...")
    path = viz.plot_encoding_pipeline(message, codeword, nsym)
    console.print(f"   [dim]Saved: {path}[/dim]")

    # ── 2. Burst error simulation ─────────────────────────────────────
    console.print("[cyan]2.[/cyan] Simulating burst errors...")
    burst = BurstErrorChannel(burst_length=8, num_bursts=2, seed=42)
    stats = burst.transmit(codeword)
    console.print(f"   [red]{stats.num_errors} errors[/red] in bursts: {stats.burst_ranges}")

    path = viz.plot_burst_error_map(codeword, stats)
    console.print(f"   [dim]Saved: {path}[/dim]")

    # ── 3. Error correction ───────────────────────────────────────────
    console.print("[cyan]3.[/cyan] Correcting errors...")
    try:
        decoded, errors_fixed, info = rs.decode(stats.corrupted, return_info=True)
        corrected_codeword = rs.encode(decoded)
        console.print(f"   [green]✓ Corrected {errors_fixed} errors[/green]")

        path = viz.plot_correction(
            codeword, stats.corrupted, corrected_codeword,
            stats.error_positions, nsym
        )
        console.print(f"   [dim]Saved: {path}[/dim]")

        # Syndromes
        path = viz.plot_syndromes(info['syndromes'], info['error_locator'], nsym)
        console.print(f"   [dim]Saved: {path}[/dim]")

        # Dashboard
        path = viz.plot_dashboard(
            message, codeword, stats, corrected_codeword, info, nsym
        )
        console.print(f"   [dim]Saved: {path}[/dim]")

    except ValueError as e:
        console.print(f"   [red]✗ {e}[/red]")

    # ── 4. Monte Carlo simulation ─────────────────────────────────────
    console.print("[cyan]4.[/cyan] Running Monte Carlo simulation...")
    short_msg = list(b"RS Monte Carlo test data.")
    sim = MonteCarloSimulator(rs, num_trials=args.trials)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Random errors...", total=2)
        random_results = sim.run_random_error_sweep(
            short_msg, range(1, nsym + 3)
        )
        progress.update(task, advance=1, description="Burst errors...")
        burst_results = sim.run_burst_error_sweep(
            short_msg, range(1, nsym + 3)
        )
        progress.update(task, advance=1)

    path = viz.plot_performance_curves(random_results, burst_results, nsym)
    console.print(f"   [dim]Saved: {path}[/dim]")

    console.print("\n[bold green]✓ Simulation complete![/bold green]")


def cmd_qr_demo(args):
    """Run QR code RS demonstration."""
    print_section("QR Code RS Demo", "📱")

    from qr_demo import run_qr_demo

    text = args.message or "Reed-Solomon codes protect this QR message!"
    result = run_qr_demo(text, args.output)

    table = Table(title="QR Demo Results", border_style="bright_blue", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Original text", result['original_text'][:60])
    table.add_row("Recovered text", result['recovered_text'][:60])
    table.add_row("Match?", "✓ Yes" if result['match'] else "✗ No")
    table.add_row("Image damage", f"{result['damage_percent']:.1f}%")
    table.add_row("Symbol errors", str(result['num_errors']))
    table.add_row("Errors corrected", str(result['errors_corrected']))
    table.add_row("Output", result['image_path'])
    console.print(table)


def cmd_compare(args):
    """Run RS vs BCH comparison."""
    print_section("RS vs BCH Comparison", "⚔️")

    from comparison import run_comparison, format_comparison_table

    console.print("[dim]Running benchmark...[/dim]")
    results = run_comparison(num_trials=args.trials)

    table = Table(title="RS vs BCH Comparison", border_style="bright_blue", box=box.HEAVY)
    table.add_column("Metric", style="cyan", min_width=22)
    table.add_column("Reed-Solomon", style="green", justify="center")
    table.add_column("BCH", style="yellow", justify="center")

    table.add_row("Code",
                  f"RS({results['rs_n']},{results['rs_k']})",
                  f"BCH({results['bch_n']},{results['bch_k']})")
    table.add_row("Code Rate",
                  f"{results['rs_code_rate']:.3f}",
                  f"{results['bch_code_rate']:.3f}")
    table.add_row("Redundancy",
                  f"{results['rs_redundancy']:.1f}%",
                  f"{results['bch_redundancy']:.1f}%")
    table.add_row("Symbol Errors Fixed",
                  str(results['rs_symbol_correction']),
                  str(results['bch_bit_correction']))
    table.add_row("Burst Capability",
                  f"up to {results['rs_burst_correction']} sym",
                  f"up to {results['bch_burst_correction']} bits")
    table.add_row("Encode Time",
                  f"{results['rs_encode_time']:.3f} ms",
                  f"{results['bch_encode_time']:.3f} ms")
    table.add_row("Decode Time",
                  f"{results['rs_decode_time']:.3f} ms",
                  f"{results['bch_decode_time']:.3f} ms")
    table.add_row("Encode Complexity",
                  results['rs_encode_complexity'],
                  results['bch_encode_complexity'])
    table.add_row("Decode Complexity",
                  results['rs_decode_complexity'],
                  results['bch_decode_complexity'])
    console.print(table)

    # Generate visualization
    viz = RSVisualizer(args.output)
    path = viz.plot_comparison(results)
    console.print(f"\n[dim]Chart saved: {path}[/dim]")

    # Save markdown table
    md_table = format_comparison_table(results)
    md_path = Path(args.output) / "comparison_table.md"
    md_path.write_text(md_table)
    console.print(f"[dim]Table saved: {md_path}[/dim]")

    console.print(f"\n[bold]Key insight:[/bold] RS excels at [cyan]burst errors[/cyan] "
                  f"(QR, CD/DVD, space comm), BCH better for [yellow]random bit errors[/yellow] "
                  f"(flash, WiFi)")

    return results


def cmd_full_demo(args):
    """Run all demos in sequence."""
    print_banner()
    console.print(Panel(
        "[bold]Running complete Reed-Solomon demonstration[/bold]\n"
        "This includes encoding, decoding, channel simulation,\n"
        "QR code demo, and RS vs BCH comparison.",
        title="[bold cyan]Full Demo[/bold cyan]",
        border_style="bright_blue",
        padding=(1, 2),
    ))

    Path(args.output).mkdir(parents=True, exist_ok=True)

    steps = [
        ("Encoding", lambda: cmd_encode(args)),
        ("Decoding", lambda: cmd_decode(args)),
        ("Channel Simulation", lambda: cmd_simulate(args)),
        ("QR Code Demo", lambda: cmd_qr_demo(args)),
        ("RS vs BCH Comparison", lambda: cmd_compare(args)),
    ]

    for i, (name, func) in enumerate(steps, 1):
        console.print(f"\n{'═' * 60}")
        console.print(f"[bold bright_blue]  Step {i}/{len(steps)}: {name}[/bold bright_blue]")
        console.print(f"{'═' * 60}")
        try:
            func()
        except Exception as e:
            console.print(f"[bold red]Error in {name}: {e}[/bold red]")

    console.print(f"\n{'═' * 60}")
    console.print(Panel(
        f"[bold green]✓ All demos completed successfully![/bold green]\n"
        f"Output saved to: [cyan]{args.output}/[/cyan]",
        border_style="bright_green",
        padding=(1, 2),
    ))


# ═══════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Reed-Solomon Error Correction Codes — Demo & Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py encode -m "Hello World"
  python main.py decode -m "Test" -e 5
  python main.py simulate --nsym 16
  python main.py qr-demo -m "My QR message"
  python main.py compare --trials 100
  python main.py full-demo
        """
    )

    parser.add_argument('-o', '--output', default='output',
                        help='Output directory for visualizations (default: output)')
    parser.add_argument('--nsym', type=int, default=32,
                        help='Number of RS parity symbols (default: 32)')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Encode
    p_enc = subparsers.add_parser('encode', help='Encode a message')
    p_enc.add_argument('-m', '--message', default="Hello, Reed-Solomon!",
                       help='Text message to encode')

    # Decode
    p_dec = subparsers.add_parser('decode', help='Decode with error correction')
    p_dec.add_argument('-m', '--message', default="Hello, Reed-Solomon!",
                       help='Text message to encode/corrupt/decode')
    p_dec.add_argument('-e', '--errors', type=int, default=5,
                       help='Number of errors to inject (default: 5)')
    p_dec.add_argument('--seed', type=int, default=42,
                       help='Random seed (default: 42)')

    # Simulate
    p_sim = subparsers.add_parser('simulate', help='Run channel simulation')
    p_sim.add_argument('--trials', type=int, default=30,
                       help='Monte Carlo trials (default: 30)')

    # QR Demo
    p_qr = subparsers.add_parser('qr-demo', help='QR code RS demonstration')
    p_qr.add_argument('-m', '--message',
                      default="Reed-Solomon codes protect this QR message!",
                      help='Text for QR code')

    # Compare
    p_cmp = subparsers.add_parser('compare', help='RS vs BCH comparison')
    p_cmp.add_argument('--trials', type=int, default=50,
                       help='Benchmark trials (default: 50)')

    # Full demo
    p_full = subparsers.add_parser('full-demo', help='Run all demonstrations')
    p_full.add_argument('-m', '--message', default="Hello, Reed-Solomon!",
                        help='Text message for demos')
    p_full.add_argument('-e', '--errors', type=int, default=8,
                        help='Number of errors for decode demo')
    p_full.add_argument('--seed', type=int, default=42,
                        help='Random seed')
    p_full.add_argument('--trials', type=int, default=30,
                        help='Simulation/benchmark trials')

    args = parser.parse_args()

    if args.command is None:
        print_banner()
        parser.print_help()
        sys.exit(0)

    commands = {
        'encode': cmd_encode,
        'decode': cmd_decode,
        'simulate': cmd_simulate,
        'qr-demo': cmd_qr_demo,
        'compare': cmd_compare,
        'full-demo': cmd_full_demo,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
