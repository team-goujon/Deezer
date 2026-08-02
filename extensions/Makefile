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
#   VERSION=x.y.z      override the version written to the assembled manifest
#
# Examples:
#   make build-firefox              assemble a dev build for Firefox
#   make build PROD=1               assemble production builds for both browsers
#   make lint-firefox               assemble then run Mozilla's web-ext lint
#   make run-firefox                assemble then launch a temporary Firefox

SHARED  := shared
DIST    := dist
SHIPPED := background.js icon-16.png icon-48.png icon-128.png

VERSION ?=
PROD    ?=

.PHONY: build build-chrome build-firefox clean lint-firefox run-firefox

build: build-chrome build-firefox

build-chrome:
	@$(MAKE) --no-print-directory _assemble BROWSER=chrome

build-firefox:
	@$(MAKE) --no-print-directory _assemble BROWSER=firefox

# Internal: assemble dist/$(BROWSER) from shared + the browser manifest.
_assemble:
	@rm -rf $(DIST)/$(BROWSER)
	@mkdir -p $(DIST)/$(BROWSER)
	@for f in $(SHIPPED); do cp $(SHARED)/$$f $(DIST)/$(BROWSER)/$$f; done
	@cp $(BROWSER)/manifest.json $(DIST)/$(BROWSER)/manifest.json
	@if [ -n "$(VERSION)" ]; then \
	  jq --arg v "$(VERSION)" '.version = $$v' $(DIST)/$(BROWSER)/manifest.json > $(DIST)/$(BROWSER)/.m && \
	  mv $(DIST)/$(BROWSER)/.m $(DIST)/$(BROWSER)/manifest.json; \
	fi
	@if [ -n "$(PROD)" ]; then \
	  jq '.host_permissions = [.host_permissions[] | select(startswith("http://localhost") | not)]' \
	    $(DIST)/$(BROWSER)/manifest.json > $(DIST)/$(BROWSER)/.m && \
	  mv $(DIST)/$(BROWSER)/.m $(DIST)/$(BROWSER)/manifest.json; \
	fi
	@echo "Assembled $(DIST)/$(BROWSER) (VERSION=$(VERSION) PROD=$(PROD))"

clean:
	@rm -rf $(DIST)

lint-firefox: build-firefox
	@npx --yes web-ext lint --source-dir $(DIST)/firefox --self-hosted

run-firefox: build-firefox
	@npx --yes web-ext run --source-dir $(DIST)/firefox
