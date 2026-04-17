"""
test_core.py — Unit Tests for Reed-Solomon Implementation
══════════════════════════════════════════════════════════
Comprehensive tests for GF(2⁸) arithmetic, polynomial operations,
and RS encoding/decoding.
"""

import unittest
import random
from gf256 import GF256, gf
from rs_codec import ReedSolomonCodec
from channel_simulator import BurstErrorChannel, RandomErrorChannel, MixedErrorChannel


# ═══════════════════════════════════════════════════════════════════════
#  GF(2⁸) ARITHMETIC TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestGF256Arithmetic(unittest.TestCase):
    """Tests for Galois Field GF(2⁸) operations."""

    def test_addition_identity(self):
        """a + 0 = a for all a."""
        for a in range(256):
            assert gf.add(a, 0) == a

    def test_addition_commutative(self):
        """a + b = b + a."""
        for _ in range(1000):
            a, b = random.randint(0, 255), random.randint(0, 255)
            assert gf.add(a, b) == gf.add(b, a)

    def test_addition_self_inverse(self):
        """a + a = 0 in GF(2⁸)."""
        for a in range(256):
            assert gf.add(a, a) == 0

    def test_subtraction_equals_addition(self):
        """In GF(2⁸), subtraction = addition (both are XOR)."""
        for _ in range(1000):
            a, b = random.randint(0, 255), random.randint(0, 255)
            assert gf.sub(a, b) == gf.add(a, b)

    def test_multiplication_identity(self):
        """a × 1 = a for all a."""
        for a in range(256):
            assert gf.mul(a, 1) == a

    def test_multiplication_zero(self):
        """a × 0 = 0 for all a."""
        for a in range(256):
            assert gf.mul(a, 0) == 0

    def test_multiplication_commutative(self):
        """a × b = b × a."""
        for _ in range(1000):
            a, b = random.randint(0, 255), random.randint(0, 255)
            assert gf.mul(a, b) == gf.mul(b, a)

    def test_multiplication_associative(self):
        """(a × b) × c = a × (b × c)."""
        for _ in range(500):
            a = random.randint(1, 255)
            b = random.randint(1, 255)
            c = random.randint(1, 255)
            assert gf.mul(gf.mul(a, b), c) == gf.mul(a, gf.mul(b, c))

    def test_inverse(self):
        """a × a⁻¹ = 1 for all non-zero a."""
        for a in range(1, 256):
            assert gf.mul(a, gf.inverse(a)) == 1

    def test_inverse_zero_raises(self):
        """inverse(0) should raise ZeroDivisionError."""
        with pytest.raises(ZeroDivisionError):
            gf.inverse(0)

    def test_division(self):
        """a / b × b = a for non-zero b."""
        for _ in range(500):
            a = random.randint(0, 255)
            b = random.randint(1, 255)
            assert gf.mul(gf.div(a, b), b) == a

    def test_division_by_zero_raises(self):
        """Division by zero should raise."""
        with pytest.raises(ZeroDivisionError):
            gf.div(5, 0)

    def test_power(self):
        """a^n computed via power matches repeated multiplication."""
        for _ in range(100):
            a = random.randint(1, 255)
            n = random.randint(1, 10)
            result = 1
            for _ in range(n):
                result = gf.mul(result, a)
            assert gf.power(a, n) == result

    def test_exp_log_consistency(self):
        """exp(log(a)) = a for non-zero a."""
        for a in range(1, 256):
            assert gf.exp_table[gf.log_table[a]] == a

    def test_distributive(self):
        """a × (b + c) = a×b + a×c."""
        for _ in range(500):
            a = random.randint(0, 255)
            b = random.randint(0, 255)
            c = random.randint(0, 255)
            left = gf.mul(a, gf.add(b, c))
            right = gf.add(gf.mul(a, b), gf.mul(a, c))
            assert left == right


# ═══════════════════════════════════════════════════════════════════════
#  POLYNOMIAL OPERATION TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestPolynomialOps:
    """Tests for polynomial operations over GF(2⁸)."""

    def test_poly_eval_constant(self):
        """Evaluate constant polynomial."""
        assert gf.poly_eval([42], 100) == 42

    def test_poly_eval_linear(self):
        """Evaluate p(x) = 3 + 5x at x=2: 3 + 5×2 = 3 ⊕ mul(5,2)."""
        result = gf.poly_eval([3, 5], 2)
        expected = gf.add(3, gf.mul(5, 2))
        assert result == expected

    def test_poly_eval_at_zero(self):
        """p(0) should equal the constant term."""
        p = [7, 13, 42, 100]
        assert gf.poly_eval(p, 0) == 7

    def test_poly_add_identity(self):
        """p + [0] = p."""
        p = [1, 2, 3]
        result = gf.poly_add(p, [0])
        assert result[:len(p)] == p

    def test_poly_add_self(self):
        """p + p = 0 in GF(2⁸)."""
        p = [1, 2, 3, 4]
        result = gf.poly_add(p, p)
        assert all(c == 0 for c in result)

    def test_poly_mul_identity(self):
        """p × [1] = p."""
        p = [1, 2, 3]
        result = gf.poly_mul(p, [1])
        assert result == p

    def test_poly_mul_known(self):
        """(1 + x)(1 + x) = 1 + 2x + x² = 1 + x² in GF(2)."""
        # In GF(2⁸): add(2, 2) = 0, so [1, 1] × [1, 1] = [1, 0, 1]
        result = gf.poly_mul([1, 1], [1, 1])
        assert result == [1, 0, 1]

    def test_poly_div_exact(self):
        """(p × q) / q = p with zero remainder."""
        p = [1, 2, 3]
        q = [4, 1]
        product = gf.poly_mul(p, q)
        quotient, remainder = gf.poly_div(product, q)
        # Quotient should match p (up to strip)
        quotient = gf.poly_strip(quotient)
        assert quotient == p or gf.poly_strip(quotient) == gf.poly_strip(p)

    def test_poly_scale(self):
        """scalar × p should scale each coefficient."""
        p = [1, 2, 3]
        result = gf.poly_scale(p, 5)
        for i in range(len(p)):
            assert result[i] == gf.mul(p[i], 5)

    def test_generator_poly_roots(self):
        """Generator polynomial should have α⁰, α¹, ..., α^(nsym-1) as roots."""
        nsym = 8
        gen = gf.rs_generator_poly(nsym)
        for i in range(nsym):
            root = gf.exp_table[i]
            val = gf.poly_eval(gen, root)
            assert val == 0, f"g(α^{i}) = {val}, expected 0"


# ═══════════════════════════════════════════════════════════════════════
#  REED-SOLOMON CODEC TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestReedSolomonCodec:
    """Tests for RS encoding and decoding."""

    @pytest.fixture
    def rs8(self):
        """RS codec with nsym=8 (corrects up to 4 errors)."""
        return ReedSolomonCodec(nsym=8)

    @pytest.fixture
    def rs16(self):
        """RS codec with nsym=16 (corrects up to 8 errors)."""
        return ReedSolomonCodec(nsym=16)

    @pytest.fixture
    def rs32(self):
        """RS codec with nsym=32 (corrects up to 16 errors)."""
        return ReedSolomonCodec(nsym=32)

    def test_encode_decode_no_errors(self, rs16):
        """Encode → decode with no errors should return original message."""
        message = list(b"Hello, World!")
        codeword = rs16.encode(message)
        decoded, errors = rs16.decode(codeword)
        assert decoded == message
        assert errors == 0

    def test_encode_decode_no_errors_various(self, rs16):
        """Test with various messages."""
        messages = [
            list(b"A"),
            list(b"Test"),
            list(b"Reed-Solomon"),
            list(range(50)),
            [0] * 20,
            [255] * 20,
        ]
        for msg in messages:
            codeword = rs16.encode(msg)
            decoded, errors = rs16.decode(codeword)
            assert decoded == msg, f"Failed for message: {msg[:10]}..."
            assert errors == 0

    def test_codeword_evaluates_to_zero(self, rs16):
        """A valid codeword should have all-zero syndromes."""
        message = list(b"Test syndrome check")
        codeword = rs16.encode(message)
        # Check syndromes
        for i in range(rs16.nsym):
            s = gf.poly_eval(codeword, gf.exp_table[i])
            assert s == 0, f"S_{i} = {s}, expected 0"

    def test_single_error_correction(self, rs8):
        """Correct a single symbol error."""
        message = list(b"Single error test")
        codeword = rs8.encode(message)

        for pos in [0, len(codeword) // 2, len(codeword) - 1]:
            corrupted = list(codeword)
            corrupted[pos] ^= 0x55
            decoded, errors = rs8.decode(corrupted)
            assert decoded == message
            assert errors == 1

    def test_max_errors_correction(self, rs8):
        """Correct exactly t = nsym/2 = 4 errors."""
        message = list(b"Max error test!")
        codeword = rs8.encode(message)

        random.seed(42)
        corrupted = list(codeword)
        positions = random.sample(range(len(corrupted)), 4)
        for pos in positions:
            corrupted[pos] ^= random.randint(1, 255)

        decoded, errors = rs8.decode(corrupted)
        assert decoded == message
        assert errors == 4

    def test_random_errors_within_capacity(self, rs16):
        """Random errors within correction capacity should be fixed."""
        message = list(b"Random errors within capacity test message")
        codeword = rs16.encode(message)

        for trial in range(20):
            random.seed(trial)
            num_errors = random.randint(1, 8)  # t = 8
            corrupted = list(codeword)
            positions = random.sample(range(len(corrupted)), num_errors)
            for pos in positions:
                corrupted[pos] ^= random.randint(1, 255)

            decoded, errors = rs16.decode(corrupted)
            assert decoded == message, f"Trial {trial}: failed with {num_errors} errors"
            assert errors == num_errors

    def test_too_many_errors_raises(self, rs8):
        """Errors exceeding capacity should raise ValueError."""
        message = list(b"Too many errors")
        codeword = rs8.encode(message)

        corrupted = list(codeword)
        # Inject t+1 = 5 errors
        random.seed(99)
        positions = random.sample(range(len(corrupted)), 5)
        for pos in positions:
            corrupted[pos] ^= random.randint(1, 255)

        with pytest.raises(ValueError):
            rs8.decode(corrupted)

    def test_burst_error_correction(self, rs16):
        """Burst errors within capacity should be correctable."""
        message = list(b"Burst error correction test")
        codeword = rs16.encode(message)

        # 6-symbol burst (within t=8)
        corrupted = list(codeword)
        burst_start = 10
        for i in range(6):
            corrupted[burst_start + i] ^= (i + 1) * 17

        decoded, errors = rs16.decode(corrupted)
        assert decoded == message
        assert errors == 6

    def test_encode_string(self, rs16):
        """String encoding/decoding convenience methods."""
        text = "Привіт, RS!"
        codeword = rs16.encode_string(text)
        decoded_text, errors = rs16.decode_string(codeword)
        assert decoded_text == text
        assert errors == 0

    def test_message_too_long_raises(self, rs8):
        """Message exceeding max length should raise ValueError."""
        message = list(range(255))  # Too long for nsym=8 (max = 247)
        with pytest.raises(ValueError):
            rs8.encode(message)

    def test_decode_returns_info(self, rs16):
        """decode with return_info=True should return dict."""
        message = list(b"Info test")
        codeword = rs16.encode(message)
        corrupted = list(codeword)
        corrupted[5] ^= 42

        decoded, errors, info = rs16.decode(corrupted, return_info=True)
        assert decoded == message
        assert 'syndromes' in info
        assert 'error_positions' in info
        assert 'error_magnitudes' in info
        assert 5 in info['error_positions']

    def test_systematic_encoding(self, rs16):
        """Check that message appears at the end of systematic encoding."""
        message = list(b"Systematic check")
        codeword = rs16.encode(message)
        # In systematic encoding, message symbols are at the end
        assert codeword[rs16.nsym:] == message


# ═══════════════════════════════════════════════════════════════════════
#  CHANNEL SIMULATOR TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestChannelSimulator:
    """Tests for channel error simulators."""

    def test_burst_channel_error_count(self):
        """Burst channel should inject approximately burst_length errors."""
        data = list(range(100))
        ch = BurstErrorChannel(burst_length=10, num_bursts=1, seed=42)
        stats = ch.transmit(data)
        assert stats.num_errors == 10
        # Errors should be contiguous
        positions = stats.error_positions
        assert max(positions) - min(positions) < 11

    def test_random_channel_error_count(self):
        """Random channel should inject exactly num_errors errors."""
        data = list(range(100))
        ch = RandomErrorChannel(num_errors=5, seed=42)
        stats = ch.transmit(data)
        assert stats.num_errors == 5

    def test_channel_preserves_length(self):
        """Channel should not change codeword length."""
        data = list(range(100))
        ch = BurstErrorChannel(burst_length=5, seed=42)
        stats = ch.transmit(data)
        assert len(stats.corrupted) == len(data)

    def test_burst_channel_actually_corrupts(self):
        """Corrupted data should differ from original at error positions."""
        data = list(range(100))
        ch = BurstErrorChannel(burst_length=5, seed=42)
        stats = ch.transmit(data)
        for pos in stats.error_positions:
            assert stats.corrupted[pos] != data[pos]

    def test_seed_reproducibility(self):
        """Same seed should produce same errors."""
        data = list(range(100))
        ch1 = BurstErrorChannel(burst_length=5, seed=42)
        ch2 = BurstErrorChannel(burst_length=5, seed=42)
        stats1 = ch1.transmit(data)
        stats2 = ch2.transmit(data)
        assert stats1.corrupted == stats2.corrupted


# ═══════════════════════════════════════════════════════════════════════
#  INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestIntegration:
    """End-to-end integration tests."""

    def test_full_pipeline_burst(self):
        """Full: encode → burst errors → decode."""
        rs = ReedSolomonCodec(nsym=16)
        message = list(b"Full pipeline burst test!")
        codeword = rs.encode(message)

        ch = BurstErrorChannel(burst_length=6, seed=42)
        stats = ch.transmit(codeword)

        decoded, errors = rs.decode(stats.corrupted)
        assert decoded == message

    def test_full_pipeline_random(self):
        """Full: encode → random errors → decode."""
        rs = ReedSolomonCodec(nsym=32)
        message = list(b"Full pipeline random test message for RS codes!")
        codeword = rs.encode(message)

        ch = RandomErrorChannel(num_errors=12, seed=42)
        stats = ch.transmit(codeword)

        decoded, errors = rs.decode(stats.corrupted)
        assert decoded == message
        assert errors == 12

    def test_full_pipeline_mixed(self):
        """Full: encode → mixed errors → decode."""
        rs = ReedSolomonCodec(nsym=32)
        message = list(b"Mixed error pipeline test!")
        codeword = rs.encode(message)

        ch = MixedErrorChannel(burst_length=4, num_bursts=1,
                              num_random=3, seed=42)
        stats = ch.transmit(codeword)

        if stats.num_errors <= 16:
            decoded, errors = rs.decode(stats.corrupted)
            assert decoded == message


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
