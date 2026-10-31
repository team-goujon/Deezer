// Shared background script for both the Chrome and Firefox builds.
// Firefox exposes the promise-based `browser` namespace; Chrome exposes
// `chrome`. This shim keeps the logic identical on both while getting real
// promises everywhere (in Firefox, chrome.* is callback-based, so
// `await chrome.cookies.get(...)` would not work).
const api = globalThis.browser ?? globalThis.chrome;

let isDev = false;
let baseUrl = 'https://teamgoujon.net';

const logInfo = (...args) => { if (isDev) console.log('[TG]', ...args); };
const logWarn = (...args) => { if (isDev) console.warn('[TG]', ...args); };
const logError = (...args) => { if (isDev) console.error('[TG]', ...args); };

const notify = (message) => api.notifications.create({
  type: 'basic', iconUrl: 'icon-128.png', title: 'TeamGoujon', message
});

const ready = api.management.getSelf().then((info) => {
  isDev = info.installType === 'development';
  baseUrl = isDev ? 'http://localhost:5000' : 'https://teamgoujon.net';
  logInfo('background.js loaded, installType:', info.installType, '→ baseUrl:', baseUrl);
});

api.action.onClicked.addListener(async (tab) => {
  await ready;
  logInfo('icon clicked, tab url:', tab?.url);

  // Firefox grants host permissions lazily (temporary add-ons in particular are
  // not granted at install), so make sure we hold every origin we need before
  // using it: reading the Deezer cookies AND reaching the backend. The toolbar
  // click is a user gesture, so permissions.request is allowed.
  const needed = {
    origins: ['https://*.deezer.com/*', `${new URL(baseUrl).origin}/*`],
  };
  if (!(await api.permissions.contains(needed))) {
    const granted = await api.permissions.request(needed);
    if (!granted) {
      logWarn('required host permissions denied');
      notify('Autorise l\'accès pour continuer.');
      return;
    }
  }

  const url = 'https://www.deezer.com';

  const arlCookie = await api.cookies.get({ url, name: 'arl' });
  const sidCookie = await api.cookies.get({ url, name: 'sid' });

  const arl = arlCookie?.value;
  const sid = sidCookie?.value;

  if (!arl || !sid) {
    logWarn('missing cookie(s), aborting');
    notify('Connecte-toi à Deezer d\'abord.');
    return;
  }

  const endpoint = `${baseUrl}/login-via-extension`;
  logInfo('POST →', endpoint);

  try {
    const r = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ arl, sid })
    });
    logInfo('response status:', r.status, r.statusText);

    if (r.ok) {
      api.tabs.create({ url: baseUrl });
    } else {
      notify('Échec : ' + r.status);
    }
  } catch (e) {
    logError('fetch threw:', e);
    notify('Erreur : ' + e.message);
  }
});
