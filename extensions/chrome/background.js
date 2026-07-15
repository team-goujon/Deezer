let isDev = false;
let baseUrl = 'https://teamgoujon.net';

const logInfo = (...args) => { if (isDev) console.log('[TG]', ...args); };
const logWarn = (...args) => { if (isDev) console.warn('[TG]', ...args); };
const logError = (...args) => { if (isDev) console.error('[TG]', ...args); };

const ready = chrome.management.getSelf().then((info) => {
  isDev = info.installType === 'development';
  baseUrl = isDev ? 'http://localhost:5000' : 'https://teamgoujon.net';
  logInfo('background.js loaded, installType:', info.installType, '→ baseUrl:', baseUrl);
});

chrome.action.onClicked.addListener(async (tab) => {
  await ready;
  logInfo('icon clicked, tab url:', tab?.url);

  const url = 'https://www.deezer.com';

  const arlCookie = await chrome.cookies.get({ url, name: 'arl' });
  const sidCookie = await chrome.cookies.get({ url, name: 'sid' });

  const arl = arlCookie?.value;
  const sid = sidCookie?.value;

  if (!arl || !sid) {
    logWarn('missing cookie(s), aborting');
    chrome.notifications.create({
      type: 'basic', iconUrl: 'icon-128.png', title: 'TeamGoujon',
      message: 'Connecte-toi à Deezer d\'abord.'
    });
    return;
  }

  const endpoint = `${baseUrl}/login-via-extension`;
  logInfo('POST →', endpoint);

  try {
    const r = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ arl, sid })
    });
    logInfo('response status:', r.status, r.statusText);

    if (r.ok) {
      chrome.tabs.create({ url: baseUrl });
    } else {
      chrome.notifications.create({
        type: 'basic', iconUrl: 'icon-128.png', title: 'TeamGoujon',
        message: 'Échec : ' + r.status
      });
    }
  } catch (e) {
    logError('fetch threw:', e);
    chrome.notifications.create({
      type: 'basic', iconUrl: 'icon-128.png', title: 'TeamGoujon',
      message: 'Erreur : ' + e.message
    });
  }
});
