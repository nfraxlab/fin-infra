# Security Audit

**Last Audited**: January 3, 2026
**Reviewer**: AI Agent

This document records all Bandit security scanner skips and their justifications.

---

## Bandit Configuration

The following Bandit rules are skipped in `pyproject.toml`:

```toml
[tool.bandit]
exclude_dirs = ["tests", ".venv", "venv"]
skips = [
    "B101",  # assert used (intentional in tests and contracts)
    "B311",  # random for non-crypto (intentional)
    "B324",  # MD5 hash - used for cache keys only, not security
]
```

---

## Skip Justifications

### B101: Use of assert

**Locations**: Throughout codebase
**Justification**: Assertions are used for programming contracts and invariants in non-production paths. Tests use assertions extensively for validation.
**Risk**: None - assertions are appropriate here.

### B311: Random for Non-Crypto

**Locations**: Various utility functions
**Justification**: `random` module is used for non-security purposes (sampling, jitter in retries). Cryptographic operations use `secrets` module.
**Risk**: None - appropriate use of randomness.

### B324: Use of MD5

**Locations**:
1. [src/fin_infra/categorization/llm_layer.py](../src/fin_infra/categorization/llm_layer.py) line 303
2. [src/fin_infra/recurring/normalizers.py](../src/fin_infra/recurring/normalizers.py) line 333
3. [src/fin_infra/recurring/insights.py](../src/fin_infra/recurring/insights.py) line 355

**Cache Key Generation**:
```python
# categorization/llm_layer.py
hash_value = hashlib.md5(normalized.encode()).hexdigest()

# recurring/normalizers.py
hash_hex = hashlib.md5(normalized.encode()).hexdigest()

# recurring/insights.py
hash_hex = hashlib.md5(subscriptions_json.encode()).hexdigest()
```

**Justification**: MD5 is used exclusively for cache key generation - creating deterministic, compact keys from input data. This is not a security context:
- No collision resistance required
- No pre-image resistance required
- Keys are for cache lookup, not authentication or integrity

**Risk**: None - MD5 is appropriate for non-cryptographic hashing.

---

## Security Considerations for Users

1. **PII Protection**: Enable the PII masking filter via `add_financial_security()`. This automatically detects and masks SSNs, account numbers, and card numbers in logs.

2. **Token Encryption**: Encrypt provider API tokens (Plaid, Alpaca, etc.) at rest using `EncryptedToken`. Generate keys with `generate_encryption_key()`.

3. **Decimal Precision**: Always use `Decimal` for financial amounts, never `float`. This prevents rounding errors in financial calculations.

4. **Audit Logging**: Enable audit logging for PII access to meet SOC 2, GDPR, and GLBA requirements.

5. **Key Rotation**: Support multiple encryption keys via `old_keys` parameter for zero-downtime rotation.

---

## Compliance Notes

This package is designed to support:
- **PCI-DSS**: Card number masking, encryption at rest
- **SOC 2**: Audit logging, access controls
- **GDPR**: PII masking, data access logging
- **GLBA**: Financial data protection
- **CCPA**: Consumer data protection

See [security.md](security.md) for implementation details.

---

## Recommendations

1. **Enable All Protections**: Use `add_financial_security(app, enable_pii_filter=True, enable_audit_log=True)` in production.

2. **Rotate Encryption Keys**: Set up key rotation schedules for provider token encryption.

3. **Review Masked Fields**: Periodically review PII detection patterns to ensure new field types are captured.
