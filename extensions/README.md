# Browser extensions

The **TeamGoujon Music Connector** extension lets a user log in to the TeamGoujon
web app in one click, by reading their Deezer session cookies (`arl`, `sid`) and
posting them to `/login-via-extension` instead of pasting them by hand.

## Structure

```
extensions/
   shared/                single source of the common code and assets
      background.js       shared logic (cross-browser via a browser/chrome shim)
      icon-16/48/128.png
      PRIVACY.md          privacy policy source (hosted at /privacy)
   chrome/
      manifest.json       Chrome-specific (background.service_worker)
   firefox/
      manifest.json       Firefox-specific (background.scripts + gecko settings)
   Makefile               assembles dist/<browser> from shared + manifest
   README.md              this README.md
   dist/<browser>/        build output (git-ignored)
```

**Note**
- `background.js` is identical for both browsers. Firefox exposes the promise-based `browser` namespace and Chrome exposes `chrome`
- a one-line shim
(`const api = globalThis.browser ?? globalThis.chrome`) keeps the code the same
while getting real promises on both.

## Dev vs prod

The backend is chosen at runtime from `management.getSelf().installType`:

- **Dev:** load `dist/<browser>/` unpacked. `installType` is `development`, so
  `background.js` targets `http://localhost:5000` and prints `[TG]` debug logs.
- **Prod:** once installed from a store / signed build, `installType` is no
  longer `development`, so the backend becomes `https://teamgoujon.net` and debug
  logs are silenced.

## Build with Makefile

Run from `extensions/`:
```
make build-firefox
```
or from the repo root
```
make -C extensions build-firefox
```

| Target | Effect |
|--------|--------|
| `make build-chrome` / `make build-firefox` | assemble `dist/<browser>/` |
| `make build` | assemble both |
| `make bump-chrome VERSION=x.y.z` / `make bump-firefox VERSION=x.y.z` | write the version into `<browser>/manifest.json` (used by the release workflow) |
| `make package-chrome` | prod build + zip into `dist/artifacts/chrome.zip` |
| `make package-firefox` | prod build + Mozilla-signed `.xpi` into `dist/artifacts/` (needs `WEB_EXT_API_KEY` / `WEB_EXT_API_SECRET`) |
| `make lint-firefox` | assemble then run Mozilla's `web-ext lint` |
| `make run-firefox` | assemble then launch a temporary Firefox |
| `make clean` | remove `dist/` |

**Options**
- `PROD=1` strips the dev-only `http://localhost:5000/*` host permission from the assembled build.

## Local tests

**Chrome**
- Run `make build-chrome`
- Then in the browser load
`extensions/dist/chrome/`: `chrome://extensions` → Load unpacked

**Firefox**
- Run `make build-firefox`
- Then in the browser load `extensions/dist/firefox/`: `about:debugging` → This Firefox → Load Temporary Add-on

## Releasing

Both extensions are released by a single manual workflow,
`.github/workflows/release-extension.yml` ("Release Browser Extensions"), with two
inputs: `version` (e.g. `1.0.0`) and `browser` (`all` by default, or `chrome` /
`firefox`). It runs in three jobs:

1. **prepare** — computes the browser matrix and fails early if a target tag
   already exists (checked via the API).
2. **release** — a matrix over the selected browsers (parallel). Each bumps the
   version in its checkout (not committed), assembles a production build (localhost
   stripped) and packages it (`make package-<browser>`): Chrome as a zip, Firefox as
   a Mozilla-signed `.xpi`. Uploads both the package and the bumped manifest.
3. **finalize** — only if every release job succeeded: restores the bumped
   manifest(s), makes a **single commit**, and pushes the tags
   (`ext-<browser>-v<version>`, e.g. `ext-chrome-v1.0.0` / `ext-firefox-v1.0.0`).

Committing and tagging last means a failed build leaves no dangling tag. The bump
commit carries `[skip ci]`. No GitHub Release is created; that list is reserved for
the webapp.

**Required repo config** (Settings → Secrets and variables → Actions):

| Name | Kind | Value |
|------|------|-------|
| `APP_CLIENT_ID` | Variable | Team Goujon GitHub App client ID (`Iv23...`) |
| `APP_PRIVATE_KEY` | Secret | The app's private key (PEM contents) |
| `AMO_JWT_ISSUER` | Secret | addons.mozilla.org API key / issuer (Firefox only) |
| `AMO_JWT_SECRET` | Secret | addons.mozilla.org API secret (Firefox only) |

The GitHub App needs "Contents: Read and write" and must be installed on the repo;
if the default branch is protected, allow it to bypass. AMO credentials come from
https://addons.mozilla.org/developers/addon/api/key/.

To release: **Actions → Release Browser Extensions → Run workflow**, pick the
version and browser(s), then download the artifact(s) from the run.

### Chrome

Packaged as a zip artifact (`teamgoujon-chrome-extension-<version>`); upload to the
Chrome Web Store is manual. Tag `ext-chrome-v<version>`.

**First publication (one-time, manual)**

1. Create a Chrome Web Store developer account (one-time $5 fee):
   https://chrome.google.com/webstore/devconsole
2. Download the zip artifact from the workflow run.
3. New item, upload the zip, fill the listing (description, at least one
   screenshot 1280x800), set **Visibility to Unlisted**.
4. Privacy policy URL: `https://teamgoujon.net/privacy`. Justify each permission
   (`cookies`, `notifications`, host permissions).
5. Submit for review.
6. After approval, put the store URL in `config.ini` under
   `[extension] chrome_store_url` so the login page's "Add to Chrome" button
   links to it.

**Automatic publishing (phase 2):** uncomment the "Publish to Chrome Web Store"
step in `release-extension.yml` and add secrets `CWS_EXTENSION_ID`,
`CWS_CLIENT_ID`, `CWS_CLIENT_SECRET`, `CWS_REFRESH_TOKEN`.

### Firefox

Firefox requires the package to be **signed by Mozilla** to be installable, so it
is packaged with `web-ext sign --channel unlisted` (self-distribution): the build
is uploaded to AMO, Mozilla validates and signs it, and the signed `.xpi` is the
`teamgoujon-firefox-extension-<version>` artifact. Not listed on AMO. Tag
`ext-firefox-v<version>`; a version can only be signed once.

The add-on is identified by `browser_specific_settings.gecko.id`
(`music-connector@teamgoujon.net`); the first run creates the unlisted add-on under
your AMO account.

**Distribution (self-hosted):** unlisted means Mozilla signs but does not host the
add-on. Host the signed `.xpi` yourself (e.g. on teamgoujon.net) and point the
login page's "Add to Firefox" button at it. For auto-updates, add
`browser_specific_settings.gecko.update_url` to the manifest, pointing at an
`updates.json` you host that lists versions and their `.xpi` URLs. Without it,
users keep the installed version until they reinstall manually.
