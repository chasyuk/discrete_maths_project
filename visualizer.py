"""
visualizer.py — Premium Visualization Engine
═════════════════════════════════════════════
Publication-quality visualizations for Reed-Solomon codes
with a premium dark theme and rich color palette.
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
from pathlib import Path
from matplotlib.patches import FancyBboxPatch
import matplotlib.ticker as ticker

# ═══════════════════════════════════════════════════════════════════════
#  PREMIUM THEME CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

# Color palette — cyberpunk-inspired
COLORS = {
    'bg_dark':      '#0D1117',
    'bg_card':      '#161B22',
    'bg_medium':    '#21262D',
    'text_primary': '#E6EDF3',
    'text_dim':     '#8B949E',
    'accent_cyan':  '#58A6FF',
    'accent_green': '#3FB950',
    'accent_red':   '#F85149',
    'accent_orange':'#D29922',
    'accent_purple':'#BC8CFF',
    'accent_pink':  '#F778BA',
    'gradient_start': '#1F6FEB',
    'gradient_end':   '#58A6FF',
    'grid':         '#30363D',
    'border':       '#30363D',
}

def apply_premium_theme():
    """Apply the premium dark theme to matplotlib."""
    plt.rcParams.update({
        'figure.facecolor': COLORS['bg_dark'],
        'axes.facecolor': COLORS['bg_card'],
        'axes.edgecolor': COLORS['border'],
        'axes.labelcolor': COLORS['text_primary'],
        'axes.grid': True,
        'grid.color': COLORS['grid'],
        'grid.alpha': 0.3,
        'grid.linestyle': '--',
        'text.color': COLORS['text_primary'],
        'xtick.color': COLORS['text_dim'],
        'ytick.color': COLORS['text_dim'],
        'legend.facecolor': COLORS['bg_medium'],
        'legend.edgecolor': COLORS['border'],
        'legend.fontsize': 9,
        'font.family': 'sans-serif',
        'font.size': 11,
        'axes.titlesize': 14,
        'axes.titleweight': 'bold',
        'figure.titlesize': 16,
        'figure.titleweight': 'bold',
        'savefig.dpi': 150,
        'savefig.bbox': 'tight',
        'savefig.facecolor': COLORS['bg_dark'],
        'savefig.edgecolor': COLORS['bg_dark'],
    })

apply_premium_theme()


class RSVisualizer:
    """Creates premium visualizations for Reed-Solomon code operations."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _save(self, fig, name: str):
        path = self.output_dir / f"{name}.png"
        fig.savefig(path, dpi=150, bbox_inches='tight',
                    facecolor=COLORS['bg_dark'], edgecolor='none')
        plt.close(fig)
        return str(path)

    # ═══════════════════════════════════════════════════════════════════
    #  1. ENCODING PIPELINE VISUALIZATION
    # ═══════════════════════════════════════════════════════════════════

    def plot_encoding_pipeline(self, message, codeword, nsym):
        """
        Visualize the encoding pipeline:
        Original Message → Parity Computation → Full Codeword
        """
        fig, axes = plt.subplots(3, 1, figsize=(16, 10),
                                  gridspec_kw={'height_ratios': [1, 0.5, 1]})
        fig.suptitle('🔐 Reed-Solomon Encoding Pipeline',
                     fontsize=18, fontweight='bold', color=COLORS['accent_cyan'],
                     y=0.98)

        # Top: Original message
        ax = axes[0]
        msg_arr = np.array(message)
        bars = ax.bar(range(len(message)), msg_arr,
                      color=COLORS['accent_cyan'], alpha=0.8, width=0.8,
                      edgecolor=COLORS['accent_cyan'], linewidth=0.5)
        ax.set_title('Original Message', color=COLORS['accent_cyan'], fontsize=13)
        ax.set_xlabel('Symbol Index')
        ax.set_ylabel('Value (0-255)')
        ax.set_xlim(-1, len(message))
        ax.set_ylim(0, 270)

        # Middle: arrow/info
        axes[1].axis('off')
        axes[1].text(0.5, 0.5,
                     f'▼  Systematic RS Encoding  ▼\n'
                     f'{len(message)} data symbols + {nsym} parity symbols = {len(codeword)} total',
                     ha='center', va='center', fontsize=13,
                     color=COLORS['accent_green'],
                     bbox=dict(boxstyle='round,pad=0.8', facecolor=COLORS['bg_medium'],
                              edgecolor=COLORS['accent_green'], alpha=0.9))

        # Bottom: Full codeword (parity highlighted)
        ax = axes[2]
        cw_arr = np.array(codeword)
        colors = [COLORS['accent_orange'] if i < nsym else COLORS['accent_cyan']
                  for i in range(len(codeword))]
        ax.bar(range(len(codeword)), cw_arr, color=colors, alpha=0.8, width=0.8)
        ax.set_title('Encoded Codeword', color=COLORS['accent_green'], fontsize=13)
        ax.set_xlabel('Symbol Index')
        ax.set_ylabel('Value (0-255)')
        ax.set_xlim(-1, len(codeword))
        ax.set_ylim(0, 270)

        # Legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor=COLORS['accent_orange'], alpha=0.8, label=f'Parity ({nsym} symbols)'),
            Patch(facecolor=COLORS['accent_cyan'], alpha=0.8, label=f'Data ({len(message)} symbols)'),
        ]
        ax.legend(handles=legend_elements, loc='upper right')

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        return self._save(fig, 'encoding_pipeline')

    # ═══════════════════════════════════════════════════════════════════
    #  2. BURST ERROR MAP
    # ═══════════════════════════════════════════════════════════════════

    def plot_burst_error_map(self, codeword, stats):
        """Heatmap visualization of error positions in the codeword."""
        fig, axes = plt.subplots(2, 1, figsize=(16, 8))
        fig.suptitle('🔥 Burst Error Map',
                     fontsize=18, fontweight='bold', color=COLORS['accent_red'],
                     y=0.98)

        n = len(codeword)

        # Top: codeword with error overlay
        ax = axes[0]
        cw = np.array(stats.original)
        ax.bar(range(n), cw, color=COLORS['accent_cyan'], alpha=0.4, width=1.0,
               label='Original')

        # Highlight error positions
        error_mask = np.zeros(n)
        for pos in stats.error_positions:
            error_mask[pos] = max(cw[pos], 50)
        ax.bar(range(n), error_mask, color=COLORS['accent_red'], alpha=0.8, width=1.0,
               label='Errors')

        # Highlight burst ranges
        for start, end in stats.burst_ranges:
            ax.axvspan(start - 0.5, end - 0.5, alpha=0.15,
                      color=COLORS['accent_orange'],
                      label='Burst Range' if start == stats.burst_ranges[0][0] else None)

        ax.set_title('Codeword with Error Positions', color=COLORS['accent_red'])
        ax.set_xlabel('Symbol Index')
        ax.set_ylabel('Symbol Value')
        ax.legend(loc='upper right')
        ax.set_xlim(-1, n)

        # Bottom: error magnitude heatmap
        ax = axes[1]
        error_grid = np.zeros((4, n))
        for pos in stats.error_positions:
            orig, corr = stats.error_values[pos]
            error_grid[0, pos] = orig
            error_grid[1, pos] = corr
            error_grid[2, pos] = orig ^ corr  # error pattern
            error_grid[3, pos] = 1  # error indicator

        im = ax.imshow(error_grid, aspect='auto', cmap='hot',
                       interpolation='nearest',
                       extent=[-0.5, n - 0.5, -0.5, 3.5])
        ax.set_yticks([0, 1, 2, 3])
        ax.set_yticklabels(['Original', 'Corrupted', 'Error XOR', 'Has Error'])
        ax.set_xlabel('Symbol Index')
        ax.set_title('Error Analysis Heatmap', color=COLORS['accent_orange'])
        plt.colorbar(im, ax=ax, shrink=0.6, label='Value')

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        return self._save(fig, 'burst_error_map')

    # ═══════════════════════════════════════════════════════════════════
    #  3. CORRECTION VISUALIZATION
    # ═══════════════════════════════════════════════════════════════════

    def plot_correction(self, original, corrupted, corrected, error_positions, nsym):
        """Before/after comparison showing error correction."""
        fig, axes = plt.subplots(3, 1, figsize=(16, 12))
        fig.suptitle('✨ Reed-Solomon Error Correction',
                     fontsize=18, fontweight='bold', color=COLORS['accent_green'],
                     y=0.98)

        n = len(original)

        # 1. Original
        ax = axes[0]
        ax.bar(range(n), original, color=COLORS['accent_cyan'], alpha=0.7, width=1.0)
        ax.set_title('Original Codeword (transmitted)', color=COLORS['accent_cyan'])
        ax.set_ylabel('Value')
        ax.set_xlim(-1, n)

        # 2. Corrupted with errors highlighted
        ax = axes[1]
        colors = [COLORS['accent_red'] if i in error_positions
                  else COLORS['text_dim'] for i in range(n)]
        ax.bar(range(n), corrupted, color=colors, alpha=0.7, width=1.0)
        ax.set_title(f'Received (corrupted) — {len(error_positions)} errors',
                     color=COLORS['accent_red'])
        ax.set_ylabel('Value')
        ax.set_xlim(-1, n)

        # Mark error positions
        for pos in error_positions:
            ax.annotate('✗', xy=(pos, corrupted[pos]),
                       fontsize=8, color=COLORS['accent_red'],
                       ha='center', va='bottom')

        # 3. Corrected
        ax = axes[2]
        colors = [COLORS['accent_green'] if i in error_positions
                  else COLORS['accent_cyan'] for i in range(n)]
        ax.bar(range(n), corrected, color=colors, alpha=0.7, width=1.0)
        ax.set_title('Corrected Codeword — all errors fixed ✓',
                     color=COLORS['accent_green'])
        ax.set_xlabel('Symbol Index')
        ax.set_ylabel('Value')
        ax.set_xlim(-1, n)

        # Mark corrected positions
        for pos in error_positions:
            ax.annotate('✓', xy=(pos, corrected[pos]),
                       fontsize=8, color=COLORS['accent_green'],
                       ha='center', va='bottom')

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        return self._save(fig, 'correction_visualization')

    # ═══════════════════════════════════════════════════════════════════
    #  4. PERFORMANCE CURVES
    # ═══════════════════════════════════════════════════════════════════

    def plot_performance_curves(self, random_results, burst_results, nsym):
        """Plot correction success rate vs error count."""
        fig, axes = plt.subplots(1, 2, figsize=(16, 7))
        fig.suptitle('📊 Reed-Solomon Performance Analysis',
                     fontsize=18, fontweight='bold', color=COLORS['accent_purple'],
                     y=0.98)

        t = nsym // 2  # correction capability

        # Random errors
        ax = axes[0]
        x = list(random_results.keys())
        y = list(random_results.values())
        ax.plot(x, y, 'o-', color=COLORS['accent_cyan'], linewidth=2.5,
                markersize=8, markerfacecolor=COLORS['accent_cyan'],
                markeredgecolor='white', markeredgewidth=1.5, label='Success Rate')
        ax.axvline(x=t, color=COLORS['accent_red'], linestyle='--', alpha=0.7,
                   linewidth=2, label=f'Max correctable (t={t})')
        ax.fill_between(x, y, alpha=0.15, color=COLORS['accent_cyan'])
        ax.set_title('Random Errors', color=COLORS['accent_cyan'])
        ax.set_xlabel('Number of Symbol Errors')
        ax.set_ylabel('Correction Success Rate')
        ax.set_ylim(-0.05, 1.1)
        ax.yaxis.set_major_formatter(ticker.PercentFormatter(1.0))
        ax.legend()

        # Burst errors
        ax = axes[1]
        x = list(burst_results.keys())
        y = list(burst_results.values())
        ax.plot(x, y, 's-', color=COLORS['accent_orange'], linewidth=2.5,
                markersize=8, markerfacecolor=COLORS['accent_orange'],
                markeredgecolor='white', markeredgewidth=1.5, label='Success Rate')
        ax.axvline(x=t, color=COLORS['accent_red'], linestyle='--', alpha=0.7,
                   linewidth=2, label=f'Max correctable (t={t})')
        ax.fill_between(x, y, alpha=0.15, color=COLORS['accent_orange'])
        ax.set_title('Burst Errors', color=COLORS['accent_orange'])
        ax.set_xlabel('Burst Length (symbols)')
        ax.set_ylabel('Correction Success Rate')
        ax.set_ylim(-0.05, 1.1)
        ax.yaxis.set_major_formatter(ticker.PercentFormatter(1.0))
        ax.legend()

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        return self._save(fig, 'performance_curves')

    # ═══════════════════════════════════════════════════════════════════
    #  5. RS vs BCH COMPARISON
    # ═══════════════════════════════════════════════════════════════════

    def plot_comparison(self, comparison_data: dict):
        """Grouped bar chart comparing RS and BCH codes."""
        fig, axes = plt.subplots(1, 3, figsize=(18, 7))
        fig.suptitle('⚔️  Reed-Solomon vs BCH Comparison',
                     fontsize=18, fontweight='bold', color=COLORS['accent_pink'],
                     y=0.98)

        bar_width = 0.35
        rs_color = COLORS['accent_cyan']
        bch_color = COLORS['accent_orange']

        # 1. Encoding/Decoding Speed
        ax = axes[0]
        categories = ['Encode', 'Decode']
        rs_vals = [comparison_data['rs_encode_time'], comparison_data['rs_decode_time']]
        bch_vals = [comparison_data['bch_encode_time'], comparison_data['bch_decode_time']]
        x = np.arange(len(categories))
        bars1 = ax.bar(x - bar_width/2, rs_vals, bar_width, label='Reed-Solomon',
                       color=rs_color, alpha=0.85, edgecolor='white', linewidth=0.5)
        bars2 = ax.bar(x + bar_width/2, bch_vals, bar_width, label='BCH',
                       color=bch_color, alpha=0.85, edgecolor='white', linewidth=0.5)
        ax.set_title('Speed (ms)', color=COLORS['text_primary'])
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.set_ylabel('Time (ms)')
        ax.legend()
        # Add value labels
        for bar in bars1:
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.2,
                    f'{bar.get_height():.1f}', ha='center', va='bottom',
                    color=COLORS['text_dim'], fontsize=9)
        for bar in bars2:
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.2,
                    f'{bar.get_height():.1f}', ha='center', va='bottom',
                    color=COLORS['text_dim'], fontsize=9)

        # 2. Redundancy
        ax = axes[1]
        categories = ['Redundancy %', 'Code Rate']
        rs_vals = [comparison_data['rs_redundancy'], comparison_data['rs_code_rate'] * 100]
        bch_vals = [comparison_data['bch_redundancy'], comparison_data['bch_code_rate'] * 100]
        x = np.arange(len(categories))
        ax.bar(x - bar_width/2, rs_vals, bar_width, label='Reed-Solomon',
               color=rs_color, alpha=0.85, edgecolor='white', linewidth=0.5)
        ax.bar(x + bar_width/2, bch_vals, bar_width, label='BCH',
               color=bch_color, alpha=0.85, edgecolor='white', linewidth=0.5)
        ax.set_title('Efficiency', color=COLORS['text_primary'])
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.set_ylabel('Percentage (%)')
        ax.legend()

        # 3. Error correction capability
        ax = axes[2]
        categories = ['Symbol\nErrors', 'Burst\nLength']
        rs_vals = [comparison_data['rs_symbol_correction'],
                   comparison_data['rs_burst_correction']]
        bch_vals = [comparison_data['bch_bit_correction'],
                    comparison_data['bch_burst_correction']]
        x = np.arange(len(categories))
        ax.bar(x - bar_width/2, rs_vals, bar_width, label='Reed-Solomon',
               color=rs_color, alpha=0.85, edgecolor='white', linewidth=0.5)
        ax.bar(x + bar_width/2, bch_vals, bar_width, label='BCH',
               color=bch_color, alpha=0.85, edgecolor='white', linewidth=0.5)
        ax.set_title('Correction Capability', color=COLORS['text_primary'])
        ax.set_xticks(x)
        ax.set_xticklabels(categories)
        ax.set_ylabel('Count')
        ax.legend()

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        return self._save(fig, 'rs_vs_bch_comparison')

    # ═══════════════════════════════════════════════════════════════════
    #  6. SYNDROME & POLYNOMIAL VISUALIZATION
    # ═══════════════════════════════════════════════════════════════════

    def plot_syndromes(self, syndromes, error_locator, nsym):
        """Visualize syndrome values and error-locator polynomial."""
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        fig.suptitle('🔍 Decoding Internals',
                     fontsize=18, fontweight='bold', color=COLORS['accent_purple'],
                     y=0.98)

        # Syndromes
        ax = axes[0]
        x = range(len(syndromes))
        ax.stem(x, syndromes, linefmt='-', markerfmt='o',
                basefmt=' ')
        # Recolor stems
        markerline, stemlines, baseline = ax.stem(x, syndromes)
        plt.setp(markerline, color=COLORS['accent_cyan'], markersize=8)
        plt.setp(stemlines, color=COLORS['accent_cyan'], linewidth=2)
        ax.set_title('Syndrome Values S(α^i)', color=COLORS['accent_cyan'])
        ax.set_xlabel('Syndrome Index i')
        ax.set_ylabel('S_i Value (in GF(2⁸))')
        ax.set_xlim(-0.5, len(syndromes) - 0.5)

        # Error locator polynomial coefficients
        ax = axes[1]
        x = range(len(error_locator))
        markerline, stemlines, baseline = ax.stem(x, error_locator)
        plt.setp(markerline, color=COLORS['accent_purple'], markersize=8)
        plt.setp(stemlines, color=COLORS['accent_purple'], linewidth=2)
        ax.set_title('Error Locator Polynomial Λ(x)', color=COLORS['accent_purple'])
        ax.set_xlabel('Coefficient Index')
        ax.set_ylabel('Coefficient Value (in GF(2⁸))')
        ax.set_xlim(-0.5, len(error_locator) - 0.5)

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        return self._save(fig, 'decoding_internals')

    # ═══════════════════════════════════════════════════════════════════
    #  7. COMPREHENSIVE DASHBOARD
    # ═══════════════════════════════════════════════════════════════════

    def plot_dashboard(self, message, codeword, stats, corrected,
                       decode_info, nsym):
        """Create a comprehensive 2x2 dashboard."""
        fig = plt.figure(figsize=(20, 14))
        gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)
        fig.suptitle('📡 Reed-Solomon Code — Complete Dashboard',
                     fontsize=20, fontweight='bold', color=COLORS['accent_cyan'],
                     y=0.98)

        n = len(codeword)

        # Top-left: Encoding
        ax = fig.add_subplot(gs[0, 0])
        cw_arr = np.array(codeword)
        colors = [COLORS['accent_orange'] if i < nsym else COLORS['accent_cyan']
                  for i in range(n)]
        ax.bar(range(n), cw_arr, color=colors, alpha=0.7, width=1.0)
        ax.set_title('Encoded Codeword', color=COLORS['accent_cyan'])
        ax.set_xlabel('Index')
        ax.set_ylabel('Value')
        ax.set_xlim(-1, n)

        # Top-right: Corrupted
        ax = fig.add_subplot(gs[0, 1])
        corrupted = np.array(stats.corrupted)
        cols = [COLORS['accent_red'] if i in stats.error_positions
                else COLORS['text_dim'] for i in range(n)]
        ax.bar(range(n), corrupted, color=cols, alpha=0.7, width=1.0)
        for s, e in stats.burst_ranges:
            ax.axvspan(s - 0.5, e - 0.5, alpha=0.2, color=COLORS['accent_orange'])
        ax.set_title(f'Corrupted ({stats.num_errors} errors)', color=COLORS['accent_red'])
        ax.set_xlabel('Index')
        ax.set_ylabel('Value')
        ax.set_xlim(-1, n)

        # Bottom-left: Corrected
        ax = fig.add_subplot(gs[1, 0])
        corr_arr = np.array(corrected)
        cols = [COLORS['accent_green'] if i in stats.error_positions
                else COLORS['accent_cyan'] for i in range(n)]
        ax.bar(range(n), corr_arr, color=cols, alpha=0.7, width=1.0)
        ax.set_title('Corrected ✓', color=COLORS['accent_green'])
        ax.set_xlabel('Index')
        ax.set_ylabel('Value')
        ax.set_xlim(-1, n)

        # Bottom-right: Syndromes
        ax = fig.add_subplot(gs[1, 1])
        synd = decode_info.get('syndromes', [])
        if synd:
            markerline, stemlines, baseline = ax.stem(range(len(synd)), synd)
            plt.setp(markerline, color=COLORS['accent_purple'], markersize=6)
            plt.setp(stemlines, color=COLORS['accent_purple'], linewidth=1.5)
        ax.set_title('Syndromes', color=COLORS['accent_purple'])
        ax.set_xlabel('Index')
        ax.set_ylabel('Value')

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        return self._save(fig, 'dashboard')
