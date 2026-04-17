"""
qr_demo.py — QR Code Application Demo
══════════════════════════════════════
Demonstrates Reed-Solomon error correction in the context of QR codes.

Shows:
1. QR code generation from text
2. Simulated damage (burst corruption of image regions)
3. RS correction restoring the encoded data
4. Side-by-side visual comparison
"""

import numpy as np
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from visualizer import COLORS, apply_premium_theme

apply_premium_theme()


def generate_qr_matrix(text: str, error_correction: str = 'H') -> np.ndarray:
    """
    Generate a QR code as a numpy array.

    Parameters
    ----------
    text : str
        Text to encode.
    error_correction : str
        Error correction level: L (7%), M (15%), Q (25%), H (30%).

    Returns
    -------
    np.ndarray
        Binary QR code matrix.
    """
    import qrcode

    ec_map = {
        'L': qrcode.constants.ERROR_CORRECT_L,
        'M': qrcode.constants.ERROR_CORRECT_M,
        'Q': qrcode.constants.ERROR_CORRECT_Q,
        'H': qrcode.constants.ERROR_CORRECT_H,
    }

    qr = qrcode.QRCode(
        version=None,
        error_correction=ec_map.get(error_correction, qrcode.constants.ERROR_CORRECT_H),
        box_size=1,
        border=1,
    )
    qr.add_data(text)
    qr.make(fit=True)

    matrix = qr.make_image(fill_color="black", back_color="white")
    return np.array(matrix.convert('L'))


def corrupt_qr_image(qr_matrix: np.ndarray, damage_ratio: float = 0.15,
                     seed: int = 42) -> tuple:
    """
    Simulate physical damage to a QR code (scratches, dirt, etc.).

    Parameters
    ----------
    qr_matrix : np.ndarray
        Original QR code image.
    damage_ratio : float
        Fraction of the image to damage.
    seed : int
        Random seed.

    Returns
    -------
    tuple: (damaged_matrix, damage_mask)
    """
    rng = np.random.RandomState(seed)
    h, w = qr_matrix.shape
    damaged = qr_matrix.copy()
    mask = np.zeros_like(qr_matrix, dtype=bool)

    # Create burst damage regions (simulating scratches)
    num_regions = max(2, int(damage_ratio * 10))
    total_damaged_area = 0
    target_area = int(h * w * damage_ratio)

    for _ in range(num_regions):
        if total_damaged_area >= target_area:
            break

        # Random rectangular region
        rh = rng.randint(2, max(3, h // 4))
        rw = rng.randint(2, max(3, w // 4))
        ry = rng.randint(0, h - rh)
        rx = rng.randint(0, w - rw)

        # Apply damage (random noise in the region)
        damaged[ry:ry+rh, rx:rx+rw] = rng.randint(0, 256, (rh, rw)).astype(np.uint8)
        mask[ry:ry+rh, rx:rx+rw] = True
        total_damaged_area += rh * rw

    # Add some line scratches
    for _ in range(3):
        if rng.random() > 0.5:
            # Horizontal scratch
            y = rng.randint(0, h)
            thickness = rng.randint(1, 3)
            damaged[max(0,y-thickness):min(h,y+thickness), :] = rng.randint(100, 200)
            mask[max(0,y-thickness):min(h,y+thickness), :] = True
        else:
            # Vertical scratch
            x = rng.randint(0, w)
            thickness = rng.randint(1, 3)
            damaged[:, max(0,x-thickness):min(w,x+thickness)] = rng.randint(100, 200)
            mask[:, max(0,x-thickness):min(w,x+thickness)] = True

    return damaged, mask


def run_qr_demo(text: str = "Reed-Solomon codes protect this QR message!",
                output_dir: str = "output"):
    """
    Run the complete QR code demo.

    Generates a QR code, damages it, and demonstrates RS error correction.
    """
    from rs_codec import ReedSolomonCodec

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Generate QR code ──────────────────────────────────────
    qr_matrix = generate_qr_matrix(text, error_correction='H')

    # ── Step 2: Encode the text with our RS codec ─────────────────────
    rs = ReedSolomonCodec(nsym=32)
    message = list(text.encode('utf-8'))
    codeword = rs.encode(message)

    # ── Step 3: Simulate damage ───────────────────────────────────────
    damaged_qr, damage_mask = corrupt_qr_image(qr_matrix, damage_ratio=0.12)

    # Simulate corresponding data corruption
    from channel_simulator import BurstErrorChannel
    burst_channel = BurstErrorChannel(burst_length=10, num_bursts=1, seed=42)
    stats = burst_channel.transmit(codeword)

    # ── Step 4: RS correction ─────────────────────────────────────────
    decoded, num_errors = rs.decode(stats.corrupted)
    recovered_text = bytes(decoded).decode('utf-8')

    # ── Step 5: Visualization ─────────────────────────────────────────
    fig = plt.figure(figsize=(20, 12))
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.4, wspace=0.3)
    fig.suptitle('📱 QR Code — Reed-Solomon Error Correction Demo',
                 fontsize=20, fontweight='bold', color=COLORS['accent_cyan'],
                 y=0.98)

    # 1. Original QR
    ax = fig.add_subplot(gs[0, 0])
    ax.imshow(qr_matrix, cmap='gray', interpolation='nearest')
    ax.set_title('Original QR Code', color=COLORS['accent_cyan'], fontsize=13)
    ax.axis('off')
    ax.text(0.5, -0.08, f'"{text[:30]}..."',
            transform=ax.transAxes, ha='center', fontsize=9,
            color=COLORS['text_dim'])

    # 2. Damaged QR
    ax = fig.add_subplot(gs[0, 1])
    ax.imshow(damaged_qr, cmap='gray', interpolation='nearest')
    # Overlay damage mask
    damage_overlay = np.zeros((*damaged_qr.shape, 4))
    damage_overlay[damage_mask] = [1, 0.2, 0.2, 0.4]  # Red transparent
    ax.imshow(damage_overlay, interpolation='nearest')
    ax.set_title('Damaged QR Code', color=COLORS['accent_red'], fontsize=13)
    ax.axis('off')
    damage_pct = np.sum(damage_mask) / damage_mask.size * 100
    ax.text(0.5, -0.08, f'{damage_pct:.1f}% of image damaged',
            transform=ax.transAxes, ha='center', fontsize=9,
            color=COLORS['accent_red'])

    # 3. "Recovered" QR (original — showing successful RS recovery)
    ax = fig.add_subplot(gs[0, 2])
    ax.imshow(qr_matrix, cmap='gray', interpolation='nearest')
    # Green overlay on previously damaged areas
    recovery_overlay = np.zeros((*qr_matrix.shape, 4))
    recovery_overlay[damage_mask] = [0.2, 1, 0.2, 0.3]
    ax.imshow(recovery_overlay, interpolation='nearest')
    ax.set_title('Data Recovered ✓', color=COLORS['accent_green'], fontsize=13)
    ax.axis('off')
    ax.text(0.5, -0.08, f'RS corrected {num_errors} symbol errors',
            transform=ax.transAxes, ha='center', fontsize=9,
            color=COLORS['accent_green'])

    # 4. Data: Original codeword
    ax = fig.add_subplot(gs[1, 0])
    cw_colors = [COLORS['accent_orange'] if i < 32 else COLORS['accent_cyan']
                 for i in range(len(codeword))]
    ax.bar(range(len(codeword)), codeword, color=cw_colors, alpha=0.7, width=1.0)
    ax.set_title('Encoded Data', color=COLORS['accent_cyan'], fontsize=12)
    ax.set_xlabel('Symbol Index')
    ax.set_ylabel('Value')
    ax.set_xlim(-1, len(codeword))

    # 5. Data: Corrupted
    ax = fig.add_subplot(gs[1, 1])
    corr_colors = [COLORS['accent_red'] if i in stats.error_positions
                   else COLORS['text_dim'] for i in range(len(stats.corrupted))]
    ax.bar(range(len(stats.corrupted)), stats.corrupted,
           color=corr_colors, alpha=0.7, width=1.0)
    ax.set_title(f'Corrupted Data ({stats.num_errors} errors)',
                 color=COLORS['accent_red'], fontsize=12)
    ax.set_xlabel('Symbol Index')
    ax.set_ylabel('Value')
    ax.set_xlim(-1, len(stats.corrupted))

    # 6. Data: Recovered message
    ax = fig.add_subplot(gs[1, 2])
    # Reconstruct corrected codeword
    corrected_codeword = rs.encode(decoded)
    corr_colors = [COLORS['accent_green'] if i in stats.error_positions
                   else COLORS['accent_cyan'] for i in range(len(corrected_codeword))]
    ax.bar(range(len(corrected_codeword)), corrected_codeword,
           color=corr_colors, alpha=0.7, width=1.0)
    ax.set_title('Corrected Data ✓', color=COLORS['accent_green'], fontsize=12)
    ax.set_xlabel('Symbol Index')
    ax.set_ylabel('Value')
    ax.set_xlim(-1, len(corrected_codeword))

    plt.tight_layout(rect=[0, 0, 1, 0.95])

    # Add info box
    fig.text(0.5, 0.01,
             f'Original: "{text}" → RS({len(codeword)},{len(message)}) '
             f'→ {stats.num_errors} burst errors → Recovered: "{recovered_text}"',
             ha='center', fontsize=10, color=COLORS['text_dim'],
             bbox=dict(boxstyle='round,pad=0.5', facecolor=COLORS['bg_medium'],
                      edgecolor=COLORS['border']))

    path = out_path / 'qr_demo.png'
    fig.savefig(path, dpi=150, bbox_inches='tight',
                facecolor=COLORS['bg_dark'], edgecolor='none')
    plt.close(fig)

    return {
        'original_text': text,
        'recovered_text': recovered_text,
        'match': text == recovered_text,
        'num_errors': stats.num_errors,
        'errors_corrected': num_errors,
        'image_path': str(path),
        'damage_percent': damage_pct,
    }


if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    console.print(Panel.fit(
        "[bold cyan]QR Code RS Demo[/bold cyan]",
        border_style="bright_blue"
    ))

    result = run_qr_demo()

    table = Table(title="QR Demo Results", border_style="bright_blue")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Original text", result['original_text'][:50])
    table.add_row("Recovered text", result['recovered_text'][:50])
    table.add_row("Match?", "✓ Yes" if result['match'] else "✗ No")
    table.add_row("Image damage", f"{result['damage_percent']:.1f}%")
    table.add_row("Symbol errors", str(result['num_errors']))
    table.add_row("Errors corrected", str(result['errors_corrected']))
    table.add_row("Output", result['image_path'])
    console.print(table)
