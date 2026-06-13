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
┌─ Feature Branch (your-feature)
│  └─ Git commit → Push to GitHub
│
└─ GitHub PR to main
   ├─ Trigger: test-unit-integration.yml
   │  ├─ Run unit tests (pytest)
   │  ├─ Run integration tests (pytest)
   │  └─ Block merge if tests fail
   │
   └─ Approve & Merge to main
      ├─ Trigger: test-unit-integration.yml (verify)
      │  └─ Unit + Integration tests pass
      │
      └─ Trigger: test-e2e-docker.yml
         ├─ Build Docker image
         ├─ Start app in container
         ├─ Run E2E tests (pytest + requests)
         └─ Tests pass
         │
         └─ Create GitHub Release (manually)
            ├─ Tag: v1.0.0 (semantic versioning)
            ├─ Publish release
            │
            └─ Trigger: deploy-prod.yml (GitHub Actions)
               ├─ Pull code at v1.0.0
               ├─ Login to Fly.io (FLY_API_TOKEN)
               └─ Deploy to production automatically
                  └─ App is live at teamgoujon.net
```

---

## Testing Architecture

### Unit Tests
- **Location:** `tests/unit/`
- **Framework:** pytest
- **Coverage:** Target 80%+
- **Scope:** Individual functions, DeezerService, auth module
- **Triggers:** Every PR to main

### Integration Tests
- **Location:** `tests/integration/`
- **Framework:** pytest
- **Scope:** Service interactions, API calls, database operations
- **Requirements:** `DEEZER_ARL`, `DEEZER_SID` in GitHub Secrets
- **Triggers:** Every PR to main

### E2E Tests
- **Location:** `tests/e2e/`
- **Framework:** pytest + requests
- **Scope:** Full user workflows (login → playlist creation → API calls)
- **Environment:** Docker container (spawned in GitHub Actions)
- **Requirements:** `DEEZER_ARL`, `DEEZER_SID` in GitHub Secrets
- **Triggers:** After main branch push (Docker + E2E in same workflow)
- **Example flows to test:**
  - Login with valid cookies → redirect to menu
  - Create playlist → verify Deezer API response
  - Invalid cookies → error message display

---

## Deployment

### Environments

**Production** (release versions only):
- URL: `https://deezer.teamgoujon.net` (via Cloudflare)
- Actual: `teamgoujon-prod.fly.dev`
- Deploys on: GitHub Actions automatically on release
- Used for: Public access, real usage
- Cost: ~€2/month

**Note:** No staging environment. E2E tests run in Docker (free, in GitHub Actions).

### Deployment Workflow

```
Create release on GitHub (manually)
    ↓ (v1.0.0, v1.1.0, etc.)
GitHub detects release event
    ↓
GitHub Actions runs deploy-prod.yml
    ↓
Automatically deploys to Fly.io production
    ↓
The app is now live at teamgoujon.net
```

**How to deploy:**
1. Go to GitHub repo → Releases → Draft new release
2. Tag: `v1.0.0` (semantic versioning)
3. Title: `Release 1.0.0`
4. Description: What's new
5. Click "Publish release"
6. **Deployment starts automatically** (check Actions tab)

**Rollback:**
```bash
# If something goes wrong, redeploy previous release
git checkout v1.0.1  # Previous tag
flyctl deploy --app teamgoujon-prod
```

### Release Process

The app displays version and release date on the UI. Here's how to manage them:

**Before creating a GitHub Release:**

1. **Update version.py** (on your feature branch or main):
   ```python
   VERSION = "1.1.0"  # Bump version number
   RELEASE_DATE = "2026-05-09"  # Today's date (YYYY-MM-DD)
   ```

2. **Commit and push to main:**
   ```bash
   git add version.py
   git commit -m "Bump version to 1.1.0"
   git push origin main
   ```

3. **Wait for tests to pass** (check GitHub Actions)

4. **Create GitHub Release** with matching tag:
   - Go to repo → Releases → Draft new release
   - Tag: `v1.1.0` (must match VERSION in version.py)
   - Title: `Release 1.1.0`
   - Description: What's new, features, bugfixes
   - Click "Publish release"

5. **Deployment starts automatically!**
   - GitHub Actions runs deploy-prod.yml
   - Fly.io deploys your app
   - Users see updated version on webapp

**Example:**
```
version.py: VERSION = "1.1.0", RELEASE_DATE = "2026-05-09"
    ↓ (git commit + push)
main branch
    ↓ (tests pass)
You create GitHub Release v1.1.0
    ↓ (publish)
deploy-prod.yml runs automatically
    ↓
App deployed, users see v1.1.0 with release date
```

**Best practices:**
- Keep version.py in sync with GitHub Release tag
- Use semantic versioning: v1.0.0, v1.1.0, v2.0.0
- Update RELEASE_DATE to today's date when releasing
- Write clear release notes (what changed, what's new)

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

3. **Deploy production app:**
   ```bash
   cd /path/to/Deezer
   flyctl launch --name teamgoujon-prod
   # Accept defaults, choose deployment region
   flyctl deploy
   ```

4. **Create org for team collaboration (optional):**
   ```bash
   flyctl orgs create --name teamgoujon
   flyctl orgs invite-member AAubin --org teamgoujon
   ```

### Common Commands

```bash
# View logs
flyctl logs --app teamgoujon-prod

# Check app status
flyctl status --app teamgoujon-prod

# Redeploy
flyctl deploy --app teamgoujon-prod

# Open app in browser
flyctl open --app teamgoujon-prod
```

---

## GitHub Actions Workflows

### `test-unit-integration.yml` (Runs on: PR to main)
- Runs unit + integration tests from branch 24-add-unit-tests
- Uses `DEEZER_ARL`, `DEEZER_SID` secrets (integration tests only)
- Reports coverage
- Blocks merge if tests fail

### `test-e2e-docker.yml` (Runs on: Push to main)
- Builds Docker image
- Starts Flask app in container
- Runs E2E tests against localhost:5000
- Uses `DEEZER_ARL`, `DEEZER_SID` secrets
- Reports results
- **No external hosting needed** (free, runs in GitHub Actions)

### `deploy-prod.yml` (Runs on: GitHub Release published)
- **Automatically** deploys production to Fly.io
- Triggered when you publish a release (e.g., v1.0.0)
- Uses `FLY_API_TOKEN` secret
- **No manual steps required** after publishing release

---

## GitHub Secrets Setup

In your repo, add these secrets:

| Secret | Value | Used by |
|--------|-------|---------|
| `DEEZER_ARL` | Test Deezer ARL cookie | Integration + E2E tests |
| `DEEZER_SID` | Test Deezer SID cookie | Integration + E2E tests |
| `FLY_API_TOKEN` | Fly.io API token | Auto-deploy workflow |

**Find Deezer SID and DEEZER ARL:**
To find the cookie, you can run (locally) the script get_cookies.py, with `DEEZER_EMAIL` and `DEEZER_PWD` as local environment variables to print SID AND ARL in your terminal.

**To create secrets:**
1. Go to repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each secret above

**To get FLY_API_TOKEN:**
```bash
flyctl auth token
# Paste the output as FLY_API_TOKEN secret
```

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
# Method 1: With local Flask app
python webapp.py  # In terminal 1
export DEEZER_ARL="your_test_arl"
export DEEZER_SID="your_test_sid"
pytest tests/e2e --base-url=http://localhost:5000  # In terminal 2

# Method 2: With Docker (same as GitHub Actions)
docker build -t deezer .
docker run -d --name deezer-test -p 5000:5000 \
  -e DEEZER_ARL="your_test_arl" \
  -e DEEZER_SID="your_test_sid" \
  deezer
pytest tests/e2e --base-url=http://localhost:5000
docker stop deezer-test
```

### Debugging
- Check Fly.io logs: `flyctl logs --app teamgoujon-prod`
- View workflow runs: GitHub repo → Actions tab
- Test locally first before pushing

### Adding new tests
- Unit tests: Add to `tests/unit/`
- Integration tests: Add to `tests/integration/`
- E2E tests: Add to `tests/e2e/`
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
- Reach out to the team
- Check Fly.io docs: https://fly.io/docs/
