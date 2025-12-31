# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

We actively support the latest minor version. Security patches are backported to the current minor release only.

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

**Report Here**: [nfrax.com/?feedback=1](https://www.nfrax.com/?feedback=1)

Select "Security Issue" as the feedback type.

**Expected Response Time**:
- Initial acknowledgment: within 48 hours
- Status update: within 7 days
- Resolution timeline: depends on severity (critical: 7 days, high: 30 days, medium: 90 days)

### What to Include

Please include the following in your report:

1. **Description**: Clear description of the vulnerability
2. **Reproduction Steps**: Step-by-step instructions to reproduce the issue
3. **Impact Assessment**: What an attacker could achieve by exploiting this
4. **Affected Versions**: Which versions are affected (if known)
5. **Suggested Fix**: If you have ideas for remediation (optional)

### What NOT to Do

- Do not open public GitHub issues for security vulnerabilities
- Do not exploit the vulnerability beyond what's necessary to demonstrate it
- Do not access or modify data belonging to others

## Disclosure Policy

1. **Report received**: We acknowledge receipt within 48 hours
2. **Triage**: We assess severity and validity within 7 days
3. **Fix development**: We develop and test a fix
4. **Coordinated disclosure**: We coordinate with you on disclosure timing
5. **Public disclosure**: We publish a security advisory after the fix is released

We aim for a 90-day disclosure timeline, but may request extensions for complex issues.

## Security Update Process

1. Security fixes are released as patch versions (e.g., 0.1.x -> 0.1.x+1)
2. All security releases include a GitHub Security Advisory
3. Users are notified via:
   - GitHub Security Advisories
   - CHANGELOG.md updates
   - PyPI release notes

## Financial Data Security

fin-infra handles sensitive financial data. Security issues in this package may have regulatory implications:

### Sensitive Data Categories
- **Banking credentials**: Plaid/Teller access tokens
- **Brokerage data**: Trading account information
- **Credit data**: Credit scores and reports (FCRA regulated)
- **Transaction data**: Financial transaction history
- **PII**: Names, addresses, account numbers

### Regulatory Considerations
- **PCI-DSS**: Payment card data handling
- **FCRA**: Credit report access and storage
- **GDPR/CCPA**: Personal data protection

**If you find vulnerabilities involving financial data exposure, credential leakage, or regulatory compliance issues, please report them with CRITICAL priority.**

## Security Best Practices for Users

When using fin-infra:

- **Money Calculations**: Always use `Decimal`, never `float` for monetary values.
- **Idempotency**: All financial operations must use idempotency keys.
- **Credentials**: Never log API keys or access tokens. Keep secrets in environment variables.
- **Audit Logging**: Enable audit logging for all credit pulls and financial data access.
- **Token Storage**: Encrypt Plaid/Teller tokens at rest.
- **Rate Limiting**: Use circuit breakers on all provider integrations.
- **Data Retention**: Implement proper data retention policies for financial data.

## Contact

For security inquiries: [nfrax.com/?feedback=1](https://www.nfrax.com/?feedback=1)

For general questions: Open a GitHub issue or discussion at [github.com/nfraxlab](https://github.com/nfraxlab).
