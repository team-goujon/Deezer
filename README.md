# Deezer Playlist Creator

A Flask web application that automates Deezer playlist creation from artist lists. Features manual cookie-based authentication, user-friendly UI, and automated testing infrastructure.

## Quick Start

### Local Development

1. **Setup environment:**
   ```bash
   cp config.ini.sample config.ini
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

2. **Run locally:**
   ```bash
   python webapp.py
   # Visit http://localhost:5000
   ```

3. **Run tests:**
   ```bash
   pytest tests/unit tests/integration  # Unit + integration tests
   pytest tests/e2e                     # E2E tests (requires running app)
   ```

---

## Development Workflow

### Git Branches

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready code |
| Feature branches | Feature development |
| Release tags (`v1.0.0`) | Production releases |

### Workflow Diagram

```
┌─ Feature Branch
│  └─ Git commit → Push
│
└─ GitHub PR to main
   └─ Checks run:
      ├─ Unit Tests (pytest)
      ├─ Integration Tests (pytest)
      ├─ Coverage (pytest)
      └─ Linting/Type checking (optional)
   └─ Merge to main
      │
      └─ Staging Deployment
         ├─ Fly.io auto-deploys to staging
         └─ E2E Tests run (GitHub Actions)
            ├─ Hit: https://deezer-staging-xyz.fly.dev
            └─ Use: DEEZER_ARL, DEEZER_SID (GitHub Secrets)
         │
         └─ Approval for Production
            │
            └─ GitHub Release (v1.0.0, v1.1.0, etc.)
               │
               ├─ Option A: Manual Deploy
               │  └─ Run: flyctl deploy --app deezer-prod
               │
               └─ Option B: Auto Deploy (future)
                  └─ GitHub Actions auto-deploys on release
```

---

## Testing Architecture

### Unit Tests
- **Location:** `tests/unit/`
- **Owner:** Sam (branch 24-add-unit-tests)
- **Framework:** pytest
- **Coverage:** Target 80%+
- **Scope:** Individual functions, DeezerService, auth module
- **Triggers:** Every PR to main

### Integration Tests
- **Location:** `tests/integration/`
- **Owner:** Sam
- **Framework:** pytest
- **Scope:** Service interactions, API calls, database operations
- **Requirements:** Test Deezer cookies
- **Triggers:** Every PR to main

### E2E Tests
- **Location:** `tests/e2e/`
- **Owner:** You
- **Framework:** pytest + requests
- **Scope:** Full user workflows (login → playlist creation → API calls)
- **Requirements:** `DEEZER_ARL`, `DEEZER_SID` in GitHub Secrets
- **Triggers:** After main branch deployment to staging
- **Example flows to test:**
  - Login with valid cookies → redirect to menu
  - Create playlist → verify Deezer API response
  - Invalid cookies → error message display

---

## Deployment

### Environments

**Staging** (always-on testing):
- URL: `https://deezer-staging-xyz.fly.dev`
- Auto-deploys on: Every push to `main`
- Used for: E2E tests, manual QA
- Cost: ~$2/month

**Production** (release versions only):
- URL: `https://deezer-prod-xyz.fly.dev`
- Deploys on: Manual or automated (see options below)
- Used for: Public access, real usage
- Cost: ~$2/month

### Deployment Options

#### Option A: Manual Deployment (Current)
1. Create release on GitHub UI (v1.0.0)
2. When ready, deploy manually:
   ```bash
   flyctl deploy --app deezer-prod
   ```
3. Verify production is working

#### Option B: Automated Production Deployment (Future)
- GitHub Actions automatically deploys to production when you publish a release
- Added workflow: `.github/workflows/deploy-prod.yml`
- Requires: `FLY_API_TOKEN` in GitHub Secrets

---

## Fly.io Setup

### Initial Setup (One-time)

1. **Create Fly.io account:**
   - https://fly.io
   - Install CLI: `curl -L https://fly.io/install.sh | sh`

2. **Authenticate:**
   ```bash
   flyctl auth login
   ```

3. **Deploy staging app:**
   ```bash
   cd /path/to/Deezer
   flyctl launch --name deezer-staging
   # Accept defaults, choose deployment region
   flyctl deploy
   ```

4. **Deploy production app:**
   ```bash
   flyctl launch --name deezer-prod
   # Accept defaults
   flyctl deploy
   ```

5. **Create org for team collaboration:**
   ```bash
   flyctl orgs create --name deezer-team
   flyctl orgs invite-member AAubin --org deezer-team
   ```

### Common Commands

```bash
# View logs
flyctl logs --app deezer-staging

# Check app status
flyctl status --app deezer-staging

# Redeploy
flyctl deploy --app deezer-staging

# Open app in browser
flyctl open --app deezer-staging
```

---

## GitHub Actions Workflows

### `test-unit-integration.yml` (Runs on: PR to main)
- Runs unit + integration tests from `24-add-unit-tests` branch
- Reports coverage
- Blocks merge if tests fail

### `deploy-staging.yml` (Runs on: Push to main)
- Deploys main branch to Fly.io staging
- Waits for app to be healthy

### `test-e2e-staging.yml` (Runs on: After staging deployment)
- Runs E2E tests against staging URL
- Uses `DEEZER_ARL`, `DEEZER_SID` secrets
- Reports results

### `deploy-prod.yml` (Optional: Runs on: GitHub Release published)
- Auto-deploys production (if enabled)
- Uses `FLY_API_TOKEN` secret

---

## GitHub Secrets Setup

In your repo, add these secrets:

| Secret | Value | Used by |
|--------|-------|---------|
| `DEEZER_ARL` | Test Deezer ARL cookie | E2E tests |
| `DEEZER_SID` | Test Deezer SID cookie | E2E tests |
| `FLY_API_TOKEN` | Fly.io API token | Auto-deploy workflows |

**To create secrets:**
1. Go to repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each secret above

---

## Authentication

The app uses **manual cookie-based authentication** (no Selenium bot detection):

1. User extracts `arl` and `sid` cookies from browser DevTools
2. Pastes them into the login form
3. App validates cookies via Deezer API
4. Session created with authenticated user data

See [service/auth.py](service/auth.py) for implementation details.

---

## Development Tips

### Running E2E tests locally
```bash
# Start app in one terminal
python webapp.py

# In another terminal, set env vars and run tests
export DEEZER_ARL="your_test_arl"
export DEEZER_SID="your_test_sid"
pytest tests/e2e --base-url=http://localhost:5000
```

### Debugging
- Check logs: `flyctl logs --app deezer-staging`
- View workflow runs: GitHub repo → Actions tab
- Test locally first before pushing

### Adding new tests
- Unit tests: Add to `tests/unit/` (SAM)
- Integration tests: Add to `tests/integration/` (SAM)
- E2E tests: Add to `tests/e2e/` (you)
- All tests use pytest framework

---

## Roadmap

### V1
- class managing auth (call via browser to authenticate on deezer ?) and primary functions (create playlist, get songs, add songs, etc.)
- class that provides secondary function (that uses primary functions)
- script that create the playlist

### V1.1
- manage error
- add logger
- automate cookies collection

### V2
- user interface
- unit tests + e2e tests?
- use docker locally

### V3
- list the artists used for the playlist, and enables user to edit it before creation
- enables user to edit list of songs in the playlist before creation
- manages artist and song preferences (ban artist and/or songs)
- load previous playlist created for editing

---

## Support & Troubleshooting

**App won't start locally:**
```bash
rm -rf __pycache__ sessions
pip install --upgrade -r requirements.txt
python webapp.py
```

**Tests failing:**
- Check Deezer cookies are valid (not expired)
- Verify GitHub Secrets are set correctly
- Check Fly.io app is running and healthy

**Questions?**
- Reach out to your team (you + Sam)
- Check Fly.io docs: https://fly.io/docs/
