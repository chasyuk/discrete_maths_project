# 🔐 Reed-Solomon Error Correction Codes

> A comprehensive Python implementation of Reed-Solomon codes over GF(2⁸), including encoding, decoding, channel simulation, QR code demonstration, and BCH comparison.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Mathematical Background](#mathematical-background)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Features](#features)
- [Architecture](#architecture)
- [Examples](#examples)

---

## 🎯 Overview

Reed-Solomon (RS) codes are a family of non-binary cyclic error-correcting codes invented by Irving S. Reed and Gustave Solomon in 1960. They are among the most widely used error-correcting codes in digital communications and storage systems.

**This project implements:**

- ✅ Complete GF(2⁸) field arithmetic with precomputed lookup tables
- ✅ Systematic RS encoding via polynomial division
- ✅ RS decoding using Berlekamp-Massey + Chien Search + Forney Algorithm
- ✅ Burst/random/mixed error channel simulators
- ✅ Monte Carlo performance analysis
- ✅ QR code error correction demonstration
- ✅ RS vs BCH comparative analysis
- ✅ Premium dark-themed visualizations

### Real-World Applications

| Application | RS Code Used | Purpose |
|------------|-------------|---------|
| **QR Codes** | RS(255, k) | Recover from dirt, damage, partial obscuring |
| **CD/DVD** | RS(255, 223) + CIRC | Correct scratches and fingerprints |
| **Blu-ray** | RS(248, 216) | High-density error correction |
| **DVB (Digital TV)** | RS(204, 188) | Broadcast channel errors |
| **Deep Space (CCSDS)** | RS(255, 223) | Correct noise in space communication |
| **Data Storage** | Various RS | RAID-6, flash memory, HDDs |

---

## 📐 Mathematical Background

### Galois Field GF(2⁸)

All arithmetic is performed in GF(2⁸) — a finite field with 256 elements (0–255).

- **Irreducible polynomial:** `p(x) = x⁸ + x⁴ + x³ + x² + 1` (0x11D)
- **Primitive element:** α = 2
- **Addition/Subtraction:** XOR operation
- **Multiplication:** Uses precomputed exp/log lookup tables for O(1)
- **Division:** `a/b = exp[log(a) - log(b) mod 255]`

### RS(n, k) Code Parameters

- **n** = codeword length (≤ 255 for GF(2⁸))
- **k** = message length
- **nsym = n − k** = number of parity symbols
- **t = nsym / 2** = maximum correctable symbol errors

### Decoding Pipeline

```
Received codeword r(x)
    │
    ├─► Syndrome Calculation: S_i = r(α^i)
    │
    ├─► Berlekamp-Massey: Find error-locator Λ(x)
    │
    ├─► Chien Search: Find error positions
    │
    ├─► Forney Algorithm: Compute error magnitudes
    │
    └─► Apply corrections → Decoded message
```

---

## 📁 Project Structure

```
discrete_maths_project/
├── gf256.py               # GF(2⁸) field arithmetic
├── rs_codec.py            # Reed-Solomon encoder & decoder
├── channel_simulator.py   # Error channel simulators
├── visualizer.py          # Premium visualization engine
├── qr_demo.py             # QR code application demo
├── comparison.py          # RS vs BCH comparison
├── main.py                # CLI entry point
├── test_core.py           # Unit & integration tests
├── requirements.txt       # Dependencies
├── README.md              # This file
├── results.md             # Detailed results & conclusions
└── output/                # Generated visualizations
    ├── encoding_pipeline.png
    ├── burst_error_map.png
    ├── correction_visualization.png
    ├── performance_curves.png
    ├── rs_vs_bch_comparison.png
    ├── decoding_internals.png
    ├── dashboard.png
    └── qr_demo.png
```

---

## 🚀 Installation

```bash
# Clone / navigate to the project
cd discrete_maths_project

# Install dependencies
pip install -r requirements.txt
```

**Dependencies:** `numpy`, `matplotlib`, `qrcode`, `Pillow`, `rich`, `pytest`

---

## 💻 Usage

### Full Demo (recommended first run)

```bash
python main.py full-demo
```

This runs all demonstrations and saves visualizations to `output/`.

### Individual Commands

```bash
# Encode a message
python main.py encode -m "Hello, World!"

# Decode with error injection
python main.py decode -m "Hello, World!" -e 5

# Run channel simulation with visualizations
python main.py simulate --nsym 16 --trials 50

# QR code RS demonstration
python main.py qr-demo -m "My QR message"

# RS vs BCH comparison
python main.py compare --trials 100
```

### Custom RS Parameters

```bash
# Use RS with 16 parity symbols (corrects up to 8 errors)
python main.py encode -m "Test" --nsym 16

# Use RS with 64 parity symbols (corrects up to 32 errors)
python main.py simulate --nsym 64
```

### Run Tests

```bash
python -m pytest test_core.py -v
```

---

## ✨ Features

### 1. GF(2⁸) Arithmetic (`gf256.py`)

- Precomputed exp/log tables for O(1) multiplication
- All field operations: add, sub, mul, div, pow, inverse
- Polynomial operations: eval, add, mul, div, scale
- Generator polynomial construction

### 2. RS Codec (`rs_codec.py`)

- **Encoder:** Systematic encoding via polynomial division
- **Decoder:** Full pipeline:
  - Syndrome calculation
  - Berlekamp-Massey algorithm (error-locator polynomial)
  - Chien search (error positions)
  - Forney algorithm (error magnitudes)
- Step-by-step logging for educational purposes
- String encoding/decoding convenience methods

### 3. Channel Simulators (`channel_simulator.py`)

- `BurstErrorChannel` — contiguous burst errors (scratches, fading)
- `RandomErrorChannel` — uniformly distributed symbol errors
- `MixedErrorChannel` — combination of both
- `MonteCarloSimulator` — statistical performance analysis

### 4. Visualizations (`visualizer.py`)

Premium dark-themed Matplotlib charts:

- Encoding pipeline diagram
- Burst error heatmap
- Before/after correction comparison
- Performance curves (success rate vs error count)
- RS vs BCH grouped bar charts
- Syndrome & polynomial stem plots
- Comprehensive 2×2 dashboard

### 5. QR Code Demo (`qr_demo.py`)

- Generate QR codes from text
- Simulate physical damage (scratches, dirt)
- Demonstrate RS error recovery
- Side-by-side visual comparison

### 6. RS vs BCH Comparison (`comparison.py`)

- Simplified BCH codec implementation
- Speed benchmarks (encoding/decoding time)
- Efficiency metrics (code rate, redundancy)
- Error correction capability comparison

---

## 🏗 Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────────┐
│   gf256.py  │────►│  rs_codec.py │────►│ channel_simulator │
│  GF(2⁸)    │     │  Encode/     │     │ Burst/Random/     │
│  Arithmetic │     │  Decode      │     │ Mixed channels    │
└─────────────┘     └──────────────┘     └───────────────────┘
       │                   │                       │
       │                   ▼                       │
       │            ┌──────────────┐               │
       └───────────►│ visualizer.py│◄──────────────┘
                    │ Premium      │
                    │ Charts       │
                    └──────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌────────────┐
        │ qr_demo  │ │comparison│ │  main.py   │
        │ .py      │ │ .py      │ │  CLI       │
        └──────────┘ └──────────┘ └────────────┘
```

---

## 📊 Examples

### Encoding & Decoding

```python
from rs_codec import ReedSolomonCodec

# Create RS codec with 32 parity symbols (corrects 16 errors)
rs = ReedSolomonCodec(nsym=32)

# Encode
message = list(b"Hello, Reed-Solomon!")
codeword = rs.encode(message)

# Corrupt (simulate 10 errors)
import random
corrupted = list(codeword)
for pos in random.sample(range(len(corrupted)), 10):
    corrupted[pos] ^= random.randint(1, 255)

# Decode & correct
decoded, num_errors = rs.decode(corrupted)
print(bytes(decoded).decode())  # "Hello, Reed-Solomon!"
print(f"Corrected {num_errors} errors")
```

### GF(2⁸) Arithmetic

```python
from gf256 import gf

# Basic operations
print(gf.add(0x53, 0xCA))       # XOR
print(gf.mul(0x53, 0xCA))       # Field multiplication
print(gf.inverse(0x53))         # Multiplicative inverse
print(gf.power(2, 8))           # 2⁸ in GF(2⁸)

# Verify: a × a⁻¹ = 1
a = 0x53
assert gf.mul(a, gf.inverse(a)) == 1
```

---

## 📝 License

Academic project for Discrete Mathematics course.

## 👤 Author

Discrete Mathematics Project — Reed-Solomon Codes
