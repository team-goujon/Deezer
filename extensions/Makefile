# Build the TeamGoujon browser extensions from shared source + per-browser manifest.
# Run from this directory (`make build-firefox`) or from the repo root
# (`make -C extensions build-firefox`).
#
# Sources:
#   shared/            common code and assets (background.js, icons)
#   <browser>/         manifest.json only
#
# Output (git-ignored):
#   dist/<browser>/    assembled, ready to load unpacked / package
#
# Options:
#   PROD=1             strip the dev-only localhost host permission (production build)
#
# Version bump (writes the version into <browser>/manifest.json, for releases):
#   make bump-chrome VERSION=1.0.0
#   make bump-firefox VERSION=1.0.0
#
# Examples:
#   make build-firefox              assemble a dev build for Firefox
#   make build PROD=1               assemble production builds for both browsers
#   make lint-firefox               assemble then run Mozilla's web-ext lint
#   make run-firefox                assemble then launch a temporary Firefox

SHARED    := shared
DIST      := dist
ARTIFACTS := $(DIST)/artifacts
SHIPPED   := background.js icon-16.png icon-48.png icon-128.png

VERSION ?=
PROD    ?=

.PHONY: build build-chrome build-firefox bump-chrome bump-firefox \
        package-chrome package-firefox clean lint-firefox run-firefox

build: build-chrome build-firefox

build-chrome:
	@$(MAKE) --no-print-directory _assemble BROWSER=chrome

build-firefox:
	@$(MAKE) --no-print-directory _assemble BROWSER=firefox

# Write VERSION into the browser's source manifest (used by the release commit).
bump-chrome:
	@$(MAKE) --no-print-directory _bump BROWSER=chrome

bump-firefox:
	@$(MAKE) --no-print-directory _bump BROWSER=firefox

# Internal: set .version in $(BROWSER)/manifest.json.
_bump:
	@test -n "$(VERSION)" || { echo "VERSION is required (e.g. make bump-$(BROWSER) VERSION=1.0.0)"; exit 1; }
	@jq --arg v "$(VERSION)" '.version = $$v' $(BROWSER)/manifest.json > $(BROWSER)/.manifest.tmp
	@mv $(BROWSER)/.manifest.tmp $(BROWSER)/manifest.json
	@echo "Bumped $(BROWSER)/manifest.json to $(VERSION)"

# Internal: assemble dist/$(BROWSER) from shared + the browser manifest.
_assemble:
	@rm -rf $(DIST)/$(BROWSER)
	@mkdir -p $(DIST)/$(BROWSER)
	@for f in $(SHIPPED); do cp $(SHARED)/$$f $(DIST)/$(BROWSER)/$$f; done
	@cp $(BROWSER)/manifest.json $(DIST)/$(BROWSER)/manifest.json
	@if [ -n "$(PROD)" ]; then \
	  jq '.host_permissions = [.host_permissions[] | select(startswith("http://localhost") | not)]' \
	    $(DIST)/$(BROWSER)/manifest.json > $(DIST)/$(BROWSER)/.m && \
	  mv $(DIST)/$(BROWSER)/.m $(DIST)/$(BROWSER)/manifest.json; \
	fi
	@echo "Assembled $(DIST)/$(BROWSER) (PROD=$(PROD))"

# Produce the distributable for a browser into $(ARTIFACTS)/ (production build).
# Chrome: a zip. Firefox: a Mozilla-signed .xpi (needs WEB_EXT_API_KEY /
# WEB_EXT_API_SECRET in the environment; channel = unlisted / self-distribution).
package-chrome:
	@$(MAKE) --no-print-directory build-chrome PROD=1
	@mkdir -p $(ARTIFACTS)
	@rm -f $(ARTIFACTS)/chrome.zip
	@cd $(DIST)/chrome && zip -qr "$(CURDIR)/$(ARTIFACTS)/chrome.zip" .
	@echo "Packaged $(ARTIFACTS)/chrome.zip"

package-firefox:
	@$(MAKE) --no-print-directory build-firefox PROD=1
	@mkdir -p $(ARTIFACTS)
	@npx --yes web-ext sign --source-dir $(DIST)/firefox --channel unlisted --artifacts-dir $(ARTIFACTS)
	@echo "Signed XPI in $(ARTIFACTS)/"

clean:
	@rm -rf $(DIST)

lint-firefox: build-firefox
	@npx --yes web-ext lint --source-dir $(DIST)/firefox --self-hosted

run-firefox: build-firefox
	@npx --yes web-ext run --source-dir $(DIST)/firefox
