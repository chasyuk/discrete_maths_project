"""
gf256.py — Galois Field GF(2⁸) Arithmetic
═══════════════════════════════════════════
Implements arithmetic over GF(2⁸) using the irreducible polynomial:
    p(x) = x⁸ + x⁴ + x³ + x² + 1  (0x11D)

This is the standard field used in Reed-Solomon codes (QR, CD/DVD, DVB, CCSDS).
All operations use precomputed exp/log lookup tables for O(1) performance.
"""


class GF256:
    """
    Galois Field GF(2⁸) with irreducible polynomial 0x11D.

    Uses generator α = 2 (primitive element) to build exp/log tables.
    All elements are integers in [0, 255].
    """

    PRIMITIVE_POLY = 0x11D  # x⁸ + x⁴ + x³ + x² + 1
    FIELD_SIZE = 256
    MAX_VAL = 255

    def __init__(self):
        """Build exp and log lookup tables using generator α=2."""
        self.exp_table = [0] * 512  # double-sized for convenience
        self.log_table = [0] * 256

        x = 1
        for i in range(255):
            self.exp_table[i] = x
            self.log_table[x] = i
            x <<= 1
            if x & 0x100:
                x ^= self.PRIMITIVE_POLY
        # Extend exp table for easy mod-free multiplication
        for i in range(255, 512):
            self.exp_table[i] = self.exp_table[i - 255]

    # ─── Primitive Field Operations ───────────────────────────────────

    def add(self, a: int, b: int) -> int:
        """Addition in GF(2⁸) is XOR."""
        return a ^ b

    def sub(self, a: int, b: int) -> int:
        """Subtraction in GF(2⁸) is the same as addition (XOR)."""
        return a ^ b

    def mul(self, a: int, b: int) -> int:
        """Multiply two field elements using log/exp tables."""
        if a == 0 or b == 0:
            return 0
        return self.exp_table[self.log_table[a] + self.log_table[b]]

    def div(self, a: int, b: int) -> int:
        """Divide a by b in GF(2⁸)."""
        if b == 0:
            raise ZeroDivisionError("Division by zero in GF(2⁸)")
        if a == 0:
            return 0
        return self.exp_table[(self.log_table[a] - self.log_table[b]) % 255]

    def power(self, a: int, n: int) -> int:
        """Raise a to the power n in GF(2⁸)."""
        if a == 0:
            return 0
        return self.exp_table[(self.log_table[a] * n) % 255]

    def inverse(self, a: int) -> int:
        """Multiplicative inverse of a in GF(2⁸)."""
        if a == 0:
            raise ZeroDivisionError("Zero has no inverse in GF(2⁸)")
        return self.exp_table[255 - self.log_table[a]]

    # ─── Polynomial Operations ────────────────────────────────────────
    # Polynomials are represented as lists: [a₀, a₁, ..., aₙ]
    # where index = power of x, i.e. poly[i] = coefficient of xⁱ

    def poly_eval(self, poly: list, x: int) -> int:
        """Evaluate polynomial at point x using Horner's method."""
        result = 0
        for i in range(len(poly) - 1, -1, -1):
            result = self.add(self.mul(result, x), poly[i])
        return result

    def poly_add(self, p: list, q: list) -> list:
        """Add two polynomials in GF(2⁸)."""
        size = max(len(p), len(q))
        result = [0] * size
        for i in range(len(p)):
            result[i] = self.add(result[i], p[i])
        for i in range(len(q)):
            result[i] = self.add(result[i], q[i])
        return result

    def poly_scale(self, p: list, scalar: int) -> list:
        """Multiply a polynomial by a scalar."""
        return [self.mul(c, scalar) for c in p]

    def poly_mul(self, p: list, q: list) -> list:
        """Multiply two polynomials in GF(2⁸)."""
        result = [0] * (len(p) + len(q) - 1)
        for i, a in enumerate(p):
            for j, b in enumerate(q):
                result[i + j] = self.add(result[i + j], self.mul(a, b))
        return result

    def poly_div(self, dividend: list, divisor: list) -> tuple:
        """
        Polynomial division in GF(2⁸).
        Returns (quotient, remainder).
        Polynomials are in ascending-power order.
        """
        if len(divisor) == 0 or all(c == 0 for c in divisor):
            raise ZeroDivisionError("Polynomial division by zero")

        # Work with copies in descending order for standard long division
        dividend_desc = list(reversed(dividend))
        divisor_desc = list(reversed(divisor))

        out = list(dividend_desc)
        normalizer = divisor_desc[0]

        for i in range(len(dividend_desc) - len(divisor_desc) + 1):
            out[i] = self.div(out[i], normalizer)
            coef = out[i]
            if coef != 0:
                for j in range(1, len(divisor_desc)):
                    out[i + j] = self.add(out[i + j], self.mul(divisor_desc[j], coef))

        sep = len(dividend_desc) - len(divisor_desc) + 1
        quotient = list(reversed(out[:sep]))
        remainder = list(reversed(out[sep:]))

        # Trim trailing (leading in ascending) zeros
        while len(quotient) > 1 and quotient[-1] == 0:
            quotient.pop()
        while len(remainder) > 1 and remainder[-1] == 0:
            remainder.pop()

        return quotient, remainder

    def poly_strip(self, p: list) -> list:
        """Remove trailing zero coefficients (high-degree zeros)."""
        result = list(p)
        while len(result) > 1 and result[-1] == 0:
            result.pop()
        return result

    # ─── Generator Polynomial ────────────────────────────────────────

    def rs_generator_poly(self, nsym: int) -> list:
        """
        Build the RS generator polynomial:
            g(x) = (x - α⁰)(x - α¹)...(x - α^(nsym-1))
        where α = 2 (primitive element).

        nsym = number of error-correction symbols (= n - k).
        """
        g = [1]
        for i in range(nsym):
            # (x - α^i) in ascending order is [-α^i, 1] = [α^i, 1] (since -1 = 1 in GF(2))
            g = self.poly_mul(g, [self.exp_table[i], 1])
        return g


# Global instance for convenience
gf = GF256()


if __name__ == "__main__":
    # Quick self-test
    print("GF(2⁸) Self-Test")
    print("=" * 40)

    assert gf.add(0x53, 0xCA) == (0x53 ^ 0xCA)
    print(f"✓ 0x53 + 0xCA = 0x{gf.add(0x53, 0xCA):02X}")

    # Multiplication: a * inverse(a) == 1
    for a in range(1, 256):
        assert gf.mul(a, gf.inverse(a)) == 1
    print("✓ a × a⁻¹ = 1 for all non-zero a")

    # Polynomial eval
    p = [1, 2, 3]  # 1 + 2x + 3x²
    val = gf.poly_eval(p, 5)
    expected = gf.add(gf.add(1, gf.mul(2, 5)), gf.mul(3, gf.mul(5, 5)))
    assert val == expected
    print(f"✓ Polynomial evaluation: p(5) = {val}")

    # Generator polynomial
    gen = gf.rs_generator_poly(4)
    print(f"✓ Generator polynomial (nsym=4): {gen}")

    print("\nAll GF(2⁸) tests passed! ✓")
