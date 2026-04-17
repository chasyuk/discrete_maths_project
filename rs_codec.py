"""
rs_codec.py — Reed-Solomon Encoder & Decoder
═════════════════════════════════════════════
Implements systematic RS(n, k) encoding and decoding over GF(2⁸).

Encoding: Systematic encoding via polynomial division.
Decoding: Berlekamp-Massey + Chien Search + Forney Algorithm.

Default configuration: RS(255, 223) — corrects up to 16 symbol errors.
"""

from gf256 import gf, GF256
from typing import Optional


class ReedSolomonCodec:
    """
    Reed-Solomon Encoder/Decoder.

    Parameters
    ----------
    nsym : int
        Number of error-correction symbols (= n - k).
        Can correct up to nsym // 2 symbol errors.
    """

    def __init__(self, nsym: int = 32):
        self.nsym = nsym
        self.t = nsym // 2  # error correction capability
        self.gf = gf
        self.generator = gf.rs_generator_poly(nsym)
        self._log = []  # step-by-step log for visualization

    def _clear_log(self):
        self._log = []

    def _add_log(self, step: str, data: dict):
        self._log.append({"step": step, **data})

    # ═══════════════════════════════════════════════════════════════════
    #  ENCODING
    # ═══════════════════════════════════════════════════════════════════

    def encode(self, message: list) -> list:
        """
        Systematic RS encoding.

        Encodes the message by computing parity symbols and appending them.
        The codeword format is: [parity₀, ..., parity_{nsym-1}, msg₀, ..., msg_{k-1}]
        (ascending power order: low-degree = parity, high-degree = message)

        Parameters
        ----------
        message : list[int]
            Message symbols (each in 0..255). Length must be ≤ 255 - nsym.

        Returns
        -------
        list[int]
            Encoded codeword of length len(message) + nsym.
        """
        self._clear_log()

        if len(message) > 255 - self.nsym:
            raise ValueError(
                f"Message too long: {len(message)} symbols "
                f"(max {255 - self.nsym} for nsym={self.nsym})"
            )

        # Shift message to high-degree positions: msg(x) * x^nsym
        msg_shifted = [0] * self.nsym + list(message)

        self._add_log("encode_start", {
            "message": list(message),
            "generator": list(self.generator),
            "nsym": self.nsym,
        })

        # Divide by generator polynomial to get remainder (parity)
        _, remainder = self.gf.poly_div(msg_shifted, self.generator)

        # Pad remainder to nsym length
        while len(remainder) < self.nsym:
            remainder.append(0)

        # Codeword = parity + message  (ascending power)
        codeword = remainder[:self.nsym] + list(message)

        self._add_log("encode_complete", {
            "parity": remainder[:self.nsym],
            "codeword": list(codeword),
            "codeword_length": len(codeword),
        })

        return codeword

    # ═══════════════════════════════════════════════════════════════════
    #  DECODING
    # ═══════════════════════════════════════════════════════════════════

    def decode(self, received: list, return_info: bool = False) -> tuple:
        """
        Decode a received RS codeword, correcting errors if possible.

        Uses:
        1. Syndrome calculation
        2. Berlekamp-Massey algorithm (error-locator polynomial)
        3. Chien search (error locations)
        4. Forney algorithm (error magnitudes)

        Parameters
        ----------
        received : list[int]
            Received codeword (possibly corrupted). Length = n.
        return_info : bool
            If True, return detailed decoding information.

        Returns
        -------
        tuple: (corrected_message, num_errors_corrected)
            or (corrected_message, num_errors_corrected, info_dict) if return_info=True
        """
        self._clear_log()
        n = len(received)
        received = list(received)

        # ── Step 1: Syndrome Calculation ──────────────────────────────
        syndromes = self._calc_syndromes(received)

        self._add_log("syndromes", {
            "values": list(syndromes),
            "all_zero": all(s == 0 for s in syndromes),
        })

        # If all syndromes are zero → no errors
        if all(s == 0 for s in syndromes):
            message = received[self.nsym:]
            if return_info:
                return message, 0, {"syndromes": syndromes, "errors": []}
            return message, 0

        # ── Step 2: Berlekamp-Massey ──────────────────────────────────
        err_locator = self._berlekamp_massey(syndromes)
        num_errors = len(err_locator) - 1

        self._add_log("error_locator", {
            "polynomial": list(err_locator),
            "num_errors": num_errors,
        })

        if num_errors > self.t:
            raise ValueError(
                f"Too many errors to correct: {num_errors} detected, "
                f"maximum correctable is {self.t}"
            )

        # ── Step 3: Chien Search (find error locations) ───────────────
        err_positions = self._chien_search(err_locator, n)

        self._add_log("error_positions", {
            "positions": list(err_positions),
        })

        if len(err_positions) != num_errors:
            raise ValueError(
                f"Chien search found {len(err_positions)} roots but "
                f"expected {num_errors}. Decoding failure."
            )

        # ── Step 4: Forney Algorithm (error magnitudes) ───────────────
        err_magnitudes = self._forney(syndromes, err_locator, err_positions, n)

        self._add_log("error_magnitudes", {
            "magnitudes": {pos: mag for pos, mag in zip(err_positions, err_magnitudes)},
        })

        # ── Step 5: Apply Corrections ─────────────────────────────────
        corrected = list(received)
        for pos, mag in zip(err_positions, err_magnitudes):
            corrected[pos] = self.gf.add(corrected[pos], mag)

        message = corrected[self.nsym:]

        self._add_log("correction_complete", {
            "num_errors_corrected": num_errors,
            "error_positions": list(err_positions),
        })

        if return_info:
            info = {
                "syndromes": syndromes,
                "error_locator": err_locator,
                "error_positions": err_positions,
                "error_magnitudes": dict(zip(err_positions, err_magnitudes)),
                "errors": list(zip(err_positions, err_magnitudes)),
            }
            return message, num_errors, info
        return message, num_errors

    # ─── Internal Decoding Steps ──────────────────────────────────────

    def _calc_syndromes(self, received: list) -> list:
        """
        Calculate syndromes S_i = r(α^i) for i = 0, 1, ..., nsym-1.
        """
        syndromes = []
        for i in range(self.nsym):
            s = self.gf.poly_eval(received, self.gf.exp_table[i])
            syndromes.append(s)
        return syndromes

    def _berlekamp_massey(self, syndromes: list) -> list:
        """
        Berlekamp-Massey algorithm to find the error-locator polynomial Λ(x).

        Returns polynomial in ascending-power order: [Λ₀, Λ₁, ..., Λ_ν]
        where Λ₀ = 1 always.
        """
        n = len(syndromes)

        # Current error-locator polynomial
        C = [1]
        # Previous error-locator polynomial
        B = [1]
        # Discrepancy
        L = 0
        m = 1
        b = 1

        for n_iter in range(n):
            # Compute discrepancy δ
            delta = syndromes[n_iter]
            for j in range(1, L + 1):
                if j < len(C):
                    delta = self.gf.add(delta, self.gf.mul(C[j], syndromes[n_iter - j]))

            if delta == 0:
                m += 1
            elif 2 * L <= n_iter:
                T = list(C)
                coef = self.gf.div(delta, b)
                # C(x) = C(x) - δ/b * x^m * B(x)
                shifted_B = [0] * m + B
                while len(shifted_B) < len(C):
                    shifted_B.append(0)
                while len(C) < len(shifted_B):
                    C.append(0)
                for j in range(len(shifted_B)):
                    if j < len(C):
                        C[j] = self.gf.add(C[j], self.gf.mul(coef, shifted_B[j]))
                L = n_iter + 1 - L
                B = T
                b = delta
                m = 1
            else:
                coef = self.gf.div(delta, b)
                shifted_B = [0] * m + B
                while len(shifted_B) < len(C):
                    shifted_B.append(0)
                while len(C) < len(shifted_B):
                    C.append(0)
                for j in range(len(shifted_B)):
                    if j < len(C):
                        C[j] = self.gf.add(C[j], self.gf.mul(coef, shifted_B[j]))
                m += 1

        return C

    def _chien_search(self, err_locator: list, n: int) -> list:
        """
        Chien search: find roots of the error-locator polynomial.

        The error positions are j where Λ(α^{-j}) = 0,
        equivalently where Λ(α^{n-1-j}) = 0 since α^255 = 1.
        """
        num_errors = len(err_locator) - 1
        positions = []

        for i in range(n):
            # Evaluate Λ(α^(-i)) = Λ(α^(255-i))
            val = self.gf.poly_eval(err_locator, self.gf.exp_table[255 - i])
            if val == 0:
                positions.append(i)

        return positions

    def _forney(self, syndromes: list, err_locator: list,
                err_positions: list, n: int) -> list:
        """
        Forney algorithm to compute error magnitudes.

        e_j = - (X_j * Ω(X_j^{-1})) / Λ'(X_j^{-1})

        where:
        - X_j = α^{pos_j} (error locator values)
        - Ω(x) = S(x)·Λ(x) mod x^nsym (error evaluator polynomial)
        - Λ'(x) = formal derivative of Λ(x)
        """
        # Build syndrome polynomial S(x) = S₀ + S₁x + ... + S_{nsym-1}x^{nsym-1}
        S_poly = list(syndromes)

        # Error evaluator polynomial Ω(x) = S(x)·Λ(x) mod x^nsym
        omega = self.gf.poly_mul(S_poly, err_locator)
        omega = omega[:self.nsym]  # mod x^nsym

        # Formal derivative of Λ(x): Λ'(x) = Λ₁ + 2Λ₂x + 3Λ₃x² + ...
        # In GF(2), even-indexed terms vanish: Λ'(x) = Λ₁ + Λ₃x² + Λ₅x⁴ + ...
        lambda_prime = []
        for i in range(1, len(err_locator)):
            if i % 2 == 1:  # odd powers survive
                lambda_prime.append(err_locator[i])
            else:
                lambda_prime.append(0)

        magnitudes = []
        for pos in err_positions:
            # X_j^{-1} = α^{-pos} = α^{255-pos}
            Xj_inv = self.gf.exp_table[255 - pos]
            Xj = self.gf.exp_table[pos]

            # Evaluate Ω(X_j^{-1})
            omega_val = self.gf.poly_eval(omega, Xj_inv)

            # Evaluate Λ'(X_j^{-1})
            lambda_prime_val = self.gf.poly_eval(lambda_prime, Xj_inv)

            if lambda_prime_val == 0:
                raise ValueError(f"Forney: Λ'(X_j^{{-1}}) = 0 at position {pos}")

            # Error magnitude: e_j = X_j * Ω(X_j^{-1}) / Λ'(X_j^{-1})
            magnitude = self.gf.mul(Xj, self.gf.div(omega_val, lambda_prime_val))
            magnitudes.append(magnitude)

        return magnitudes

    # ═══════════════════════════════════════════════════════════════════
    #  UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════════

    def encode_string(self, text: str) -> list:
        """Encode a UTF-8 string into an RS codeword."""
        data = list(text.encode('utf-8'))
        return self.encode(data)

    def decode_string(self, received: list) -> tuple:
        """Decode an RS codeword back to a UTF-8 string."""
        message, errors = self.decode(received)
        text = bytes(message).decode('utf-8')
        return text, errors

    def get_log(self) -> list:
        """Return the step-by-step log from the last encode/decode operation."""
        return self._log


def demo():
    """Quick demonstration of RS encoding and decoding."""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel

    console = Console()
    console.print(Panel.fit(
        "[bold cyan]Reed-Solomon Codec Demo[/bold cyan]",
        border_style="bright_blue"
    ))

    # Use RS(255, 223) — 32 parity symbols, corrects up to 16 errors
    rs = ReedSolomonCodec(nsym=32)

    # Encode a message
    message = list(b"Hello, Reed-Solomon! This is a test message for error correction.")
    console.print(f"\n[bold]Original message:[/bold] {bytes(message).decode()}")
    console.print(f"[dim]Message length: {len(message)} bytes[/dim]")

    codeword = rs.encode(message)
    console.print(f"[dim]Codeword length: {len(codeword)} bytes ({rs.nsym} parity symbols)[/dim]")

    # Introduce errors
    import random
    random.seed(42)
    corrupted = list(codeword)
    num_errors = 10
    error_positions = random.sample(range(len(corrupted)), num_errors)
    for pos in error_positions:
        corrupted[pos] ^= random.randint(1, 255)

    console.print(f"\n[bold red]Introduced {num_errors} errors[/bold red] at positions: {sorted(error_positions)}")

    # Decode
    decoded, errors_corrected = rs.decode(corrupted)
    decoded_text = bytes(decoded).decode('utf-8')

    table = Table(title="Decoding Results", border_style="bright_blue")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Errors introduced", str(num_errors))
    table.add_row("Errors corrected", str(errors_corrected))
    table.add_row("Decoded message", decoded_text)
    table.add_row("Match original?", "✓ Yes" if decoded == message else "✗ No")
    console.print(table)


if __name__ == "__main__":
    demo()
