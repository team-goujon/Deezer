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
| `make lint-firefox` | assemble then run Mozilla's `web-ext lint` |
| `make run-firefox` | assemble then launch a temporary Firefox |
| `make clean` | remove `dist/` |

**Options**
- `PROD=1` strips the dev-only `http://localhost:5000/*` host permission
- `VERSION=x.y.z` overrides the version written to the assembled manifest.

## Local tests

**Chrome**
- Run `make build-chrome`
- Then in the browser load
`extensions/dist/chrome/`: `chrome://extensions` → Load unpacked

**Firefox**
- Run `make build-firefox`
- Then in the browser load `extensions/dist/firefox/`: `about:debugging` → This Firefox → Load Temporary Add-on

## Chrome release

The Chrome extension is **not** released through GitHub Releases (that list is
reserved for the webapp). The `release-extension.yml` workflow is triggered
manually and produces a zip artifact; the Chrome Web Store is the real version
registry once auto-publish is enabled.

On each run the workflow:
1. Bumps `.version` in `chrome/manifest.json`, **commits it** (authored by the
   Team Goujon GitHub App) and pushes a `ext-v<version>` **tag**. This is the
   version history, no GitHub Release involved.
2. Assembles a production build with `make build-chrome PROD=1` (localhost
   stripped) and zips it as the `teamgoujon-chrome-extension-<version>` artifact.

**Required repo config** (Settings → Secrets and variables → Actions):

| Name | Kind | Value |
|------|------|-------|
| `APP_CLIENT_ID` | Variable | Team Goujon GitHub App client ID (`Iv23...`) |
| `APP_PRIVATE_KEY` | Secret | The app's private key (PEM contents) |

The app needs "Contents: Read and write" permission and must be installed on the
repo. If the default branch is protected, allow the app to bypass it.

### How to build a release zip

1. Merge extension changes to `main`.
2. **Actions → Release Chrome Extension → Run workflow**, enter the version
   (e.g. `1.0.0`), and run it.
3. The workflow commits the bump and pushes tag `ext-v1.0.0`.
4. Download the `teamgoujon-chrome-extension-<version>` artifact from the run.

The bump commit carries `[skip ci]` so it does not trigger the webapp tests.

### First publication (one-time, manual)

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

### Automatic Chrome Web Store publishing (phase 2)

Uncomment the "Publish to Chrome Web Store" step in `release-extension.yml` and
add these repo secrets: `CWS_EXTENSION_ID`, `CWS_CLIENT_ID`, `CWS_CLIENT_SECRET`,
`CWS_REFRESH_TOKEN`.

## Firefox release

The `release-firefox-extension.yml` workflow mirrors the Chrome one, but Firefox
requires the package to be **signed by Mozilla** to be installable, so packaging
is a `web-ext sign` on the **unlisted** channel (self-distribution). It returns a
signed `.xpi` uploaded as an artifact. The add-on is not listed on AMO.

On each run the workflow:
1. Bumps `.version` in `firefox/manifest.json`, commits it (Team Goujon App) and
   pushes a `firefox-v<version>` **tag**. A version can only be signed once.
2. Assembles with `make build-firefox PROD=1` (localhost stripped).
3. Runs `web-ext sign --channel unlisted`, which uploads the build to AMO,
   Mozilla validates and signs it, and the signed `.xpi` is downloaded and
   uploaded as the `teamgoujon-firefox-extension-<version>` artifact.

**Required repo config** (in addition to `APP_CLIENT_ID` / `APP_PRIVATE_KEY`):

| Name | Kind | Value |
|------|------|-------|
| `AMO_JWT_ISSUER` | Secret | addons.mozilla.org API key / issuer (`user:...`) |
| `AMO_JWT_SECRET` | Secret | addons.mozilla.org API secret |

Generate them at https://addons.mozilla.org/developers/addon/api/key/. The add-on
is identified by `browser_specific_settings.gecko.id`
(`music-connector@teamgoujon.net`); the first run creates the unlisted add-on
under your AMO account.

### Distribution (self-hosted)

Unlisted means Mozilla **signs but does not host** the add-on. Host the signed
`.xpi` yourself (e.g. on teamgoujon.net) and point the login page's "Add to
Firefox" button at it.

For auto-updates of a self-hosted add-on, add
`browser_specific_settings.gecko.update_url` to the manifest, pointing at an
`updates.json` you host that lists versions and their `.xpi` URLs. Without it,
users keep the installed version until they reinstall manually.
