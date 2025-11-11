# Security Guidelines for fin-infra

## 🚨 NEVER Commit These Files

The following files contain sensitive credentials and must **NEVER** be committed to git:

### ❌ Prohibited Files
- `.env` - Environment variables with API keys
- `.env.local`, `.env.*.local` - Local environment overrides
- `*.pem` - Certificate files (Teller, SSL, etc.)
- `*.key` - Private keys
- `*.crt` - Certificate files
- `*.p12`, `*.pfx` - Certificate bundles
- `teller_certificate.pem` - Teller client certificate
- `teller_private_key.pem` - Teller private key
- Any file in `secrets/` or `credentials/` directories

### ✅ Safe to Commit
- `.env.example` - Template with dummy values
- `README.md`, documentation files
- Source code (`src/**/*.py`)
- Tests (`tests/**/*.py`)
- Configuration templates

## 🔐 How to Handle Certificates (Teller, etc.)

### Local Development
1. **Keep certificates OUTSIDE the repo:**
   ```bash
   # Recommended: Store in a secure location
   mkdir -p ~/.fin-infra/certs
   cp /path/to/teller_certificate.pem ~/.fin-infra/certs/
   cp /path/to/teller_private_key.pem ~/.fin-infra/certs/
   chmod 600 ~/.fin-infra/certs/*
   ```

2. **Update .env to point to secure location:**
   ```bash
   TELLER_CERTIFICATE_PATH=~/.fin-infra/certs/teller_certificate.pem
   TELLER_PRIVATE_KEY_PATH=~/.fin-infra/certs/teller_private_key.pem
   ```

### Team Collaboration
- **Use a secrets manager:** 1Password, AWS Secrets Manager, HashiCorp Vault
- **Share via secure channels:** Encrypted Slack DM, 1Password shared vault
- **Never via email or Slack unencrypted**

### Production Deployment
1. **Use environment variables:**
   - Railway: Use project secrets
   - AWS: Use Secrets Manager or Parameter Store
   - Kubernetes: Use sealed secrets or external secrets operator

2. **Mount certificates as secrets:**
   ```yaml
   # Kubernetes example
   apiVersion: v1
   kind: Secret
   metadata:
     name: teller-certs
   type: Opaque
   data:
     certificate.pem: <base64-encoded-cert>
     private_key.pem: <base64-encoded-key>
   ```

3. **Set env vars to point to mounted paths:**
   ```bash
   TELLER_CERTIFICATE_PATH=/run/secrets/teller/certificate.pem
   TELLER_PRIVATE_KEY_PATH=/run/secrets/teller/private_key.pem
   ```

## 🛡️ Security Best Practices

### Certificate Management
1. **Restrict permissions:** `chmod 600 *.pem` (owner read/write only)
2. **Regular rotation:** Rotate certificates every 6-12 months
3. **Separate environments:** Use different certs for sandbox vs production
4. **Audit access:** Monitor who can access certificate files

### API Key Management
1. **Use environment variables:** Never hardcode keys in source code
2. **Principle of least privilege:** Use read-only keys when possible
3. **Rotate regularly:** Change API keys every 90 days
4. **Monitor usage:** Set up alerts for unusual API activity

### .env File Safety
1. **Never commit `.env`:** Always in `.gitignore`
2. **Use `.env.example`:** Commit template with dummy values
3. **Document requirements:** Comment each variable's purpose
4. **Validate locally:** Add checks to ensure required vars are set

## 🚨 Emergency: What if Secrets are Committed?

If you accidentally commit secrets to git:

### Immediate Actions
1. **Revoke/rotate the compromised credentials IMMEDIATELY:**
   - Teller: Generate new certificates in dashboard
   - Alpha Vantage: Generate new API key
   - Plaid: Rotate secrets in dashboard

2. **Remove from git history:**
   ```bash
   # Use BFG Repo-Cleaner (recommended)
   brew install bfg
   bfg --delete-files teller_*.pem
   bfg --delete-files .env
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   
   # Force push (WARNING: Coordinate with team)
   git push origin --force --all
   git push origin --force --tags
   ```

3. **Verify removal:**
   ```bash
   # Check all branches and history
   git log --all --full-history -- "*.pem" ".env"
   # Should return empty
   ```

4. **Notify team:**
   - Alert all developers to pull fresh
   - Confirm old credentials are revoked
   - Share new credentials via secure channel

## ✅ Quick Security Checklist

Before every commit:
- [ ] Run `git status` and verify no `.env` or `*.pem` files listed
- [ ] Check `.gitignore` includes sensitive file patterns
- [ ] Verify no hardcoded API keys in code (`grep -r "api.*key.*=" src/`)
- [ ] Ensure test fixtures use dummy/mock credentials
- [ ] Confirm environment variables are documented in `.env.example`

## 📚 Additional Resources

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [GitHub: Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [12-Factor App: Store config in environment](https://12factor.net/config)

## 🆘 Questions?

If you're unsure whether a file is safe to commit:
1. Check if it's in `.gitignore`
2. Ask yourself: "Would this file let someone access our services?"
3. If yes → **DO NOT COMMIT**
4. When in doubt, ask the team

**Remember:** It's easier to add a file later than to remove it from git history! 🔒
