console.log('[TG] background.js loaded');

chrome.action.onClicked.addListener(async (tab) => {
  console.log('[TG] icon clicked, tab url:', tab?.url);

  const url = 'https://www.deezer.com';

  const arlCookie = await chrome.cookies.get({ url, name: 'arl' });
  const sidCookie = await chrome.cookies.get({ url, name: 'sid' });
  
  const arl = arlCookie?.value;
  const sid = sidCookie?.value;
  
  if (!arl || !sid) {
    console.warn('[TG] missing cookie(s), aborting');
    chrome.notifications.create({
      type: 'basic', iconUrl: 'icon-128.png', title: 'TeamGoujon',
      message: 'Connecte-toi à Deezer d\'abord.'
    });
    return;
  }

  const { installType } = await chrome.management.getSelf();
  const baseUrl = installType === 'development'
    ? 'http://localhost:5000'
    : 'https://teamgoujon.net';
  console.log('[TG] installType:', installType, '→ baseUrl:', baseUrl);
  const endpoint = `${baseUrl}/login-via-extension`;
  console.log('[TG] POST →', endpoint);

  try {
    const r = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ arl, sid })
    });
    console.log('[TG] response status:', r.status, r.statusText);

    if (r.ok) {
      chrome.tabs.create({ url: baseUrl });
    } else {
      chrome.notifications.create({
        type: 'basic', iconUrl: 'icon-128.png', title: 'TeamGoujon',
        message: 'Échec : ' + r.status
      });
    }
  } catch (e) {
    console.error('[TG] fetch threw:', e);
    chrome.notifications.create({
      type: 'basic', iconUrl: 'icon-128.png', title: 'TeamGoujon',
      message: 'Erreur : ' + e.message
    });
  }
});