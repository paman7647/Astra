# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

PRIVACY_CODE = r"""
(function() {
 window.Astra = window.Astra || {};

 window.Astra.setPrivacySetting = async (category, value) => {
  return await window.Astra.withLock(async () => {
  const Store = window.Astra.initializeEngine();

  const methodMap = {
   'last_seen': 'setPrivacyLastSeen',
   'profile_pic': 'setPrivacyProfilePic',
   'about': 'setPrivacyAbout',
   'status': 'setPrivacyStatus',
   'read_receipts': 'setPrivacyReadReceipts'
  };
  const method = methodMap[category];
  if (!method) throw new Error(`Unknown privacy category: ${category}`);

  const valueToPass = (category === 'read_receipts')
   ? (value === 'all' || value === true || value === 'contacts')
   : value;

  // Strategy 1: window.require() for known WA privacy modules
  const requireNames = [
   'WAWebPrivacySettingsAction',
   'WAWebPrivacySettingsModel',
   'WAWebSetPrivacySettingsAction',
   'WAWebPrivacySettingsActions',
   'WAWebPrivacyModel'
  ];
  for (const modName of requireNames) {
   try {
    const mod = window.require(modName);
    if (mod && typeof mod[method] === 'function') {
     await mod[method](valueToPass);
     return true;
    }
    if (mod && mod.default && typeof mod.default[method] === 'function') {
     await mod.default[method](valueToPass);
     return true;
    }
   } catch (_) {}
  }

  // Strategy 2: Store-based resolution
  const storeKeys = ['PrivacySettings', 'Privacy', 'Privacidad'];
  for (const key of storeKeys) {
   const mod = Store[key];
   if (!mod) continue;
   if (typeof mod[method] === 'function') {
    try { await mod[method](valueToPass); return true; } catch (_) {}
   }
   try {
    for (const sub of Object.values(mod)) {
     if (sub && typeof sub[method] === 'function') {
      await sub[method](valueToPass);
      return true;
     }
    }
   } catch (_) {}
  }

  // Strategy 3: Broad webpack module scan
  try {
   const mR = window.Astra.mR;
   if (mR && mR.findModule) {
    const privMod = mR.findModule(m => m && typeof m[method] === 'function');
    if (privMod) {
     await privMod[method](valueToPass);
     return true;
    }
   }
  } catch (_) {}

  // Strategy 4: DOM-based fallback (uses confirmed live selectors)
  return await window.Astra.setPrivacySettingDOM(category, value);
  }); // end withLock
 };

 // ──────────────────────────────────────────────────────────
 // DOM-based privacy fallback
 // Uses live-confirmed selectors from WhatsApp Web (2026-03):
 //   Settings: button[aria-label="Settings"]
 //   Privacy items: clickable divs with text content
 //   Radio buttons: role="radio" with text labels
 //   Back button: button[aria-label="Back"]
 //   Read receipts: toggle switch (role="switch")
 // ──────────────────────────────────────────────────────────

 window.Astra.setPrivacySettingDOM = async (category, value) => {
  const wait = ms => new Promise(r => setTimeout(r, ms));

  const isVisible = (el) => {
   if (!el) return false;
   const r = el.getBoundingClientRect();
   return r.width > 0 && r.height > 0;
  };

  // Find a visible element by text content within a container
  const findByText = (container, texts, selector = '*') => {
   const all = Array.from(container.querySelectorAll(selector)).filter(isVisible);
   for (const text of texts) {
    const el = all.find(e => (e.innerText || '').toLowerCase().includes(text.toLowerCase()));
    if (el) return el;
   }
   return null;
  };

  // Click the Settings nav button
  const openSettings = async () => {
   const btn = document.querySelector('button[aria-label="Settings"]') ||
               document.querySelector('[data-testid="menu-bar-settings"]');
   if (!btn || !isVisible(btn)) throw new Error('Settings button not found');
   btn.click();
   await wait(1500);
  };

  // Click a menu item by its text label
  const clickMenuItem = async (labels) => {
   const panel = document.querySelector('#app');
   for (let attempt = 0; attempt < 3; attempt++) {
    const el = findByText(panel, labels, 'div[role="button"], [role="listitem"], button');
    if (el) {
     const clickable = el.closest('[role="button"], [role="listitem"], button') || el;
     clickable.click();
     await wait(1500);
     return true;
    }
    // Also try plain text spans that are clickable
    const span = findByText(panel, labels, 'span');
    if (span) {
     const parent = span.closest('[role="button"], [role="listitem"], button, div[tabindex]');
     if (parent) { parent.click(); await wait(1500); return true; }
     span.click();
     await wait(1500);
     return true;
    }
    await wait(800);
   }
   return false;
  };

  // Select a radio option by its label text
  const selectRadio = async (label) => {
   const panel = document.querySelector('#app');
   for (let attempt = 0; attempt < 3; attempt++) {
    // Primary: role="radio" elements
    const radios = Array.from(panel.querySelectorAll('[role="radio"]')).filter(isVisible);
    const match = radios.find(r => (r.innerText || '').toLowerCase().includes(label.toLowerCase()));
    if (match) {
     match.click();
     await wait(1000);
     return true;
    }
    // Fallback: any clickable element containing the exact label text
    const el = findByText(panel, [label], 'div[role="button"], button, [role="option"]');
    if (el) { el.click(); await wait(1000); return true; }
    await wait(500);
   }
   return false;
  };

  // Click the back arrow
  const goBack = async () => {
   const btn = document.querySelector('button[aria-label="Back"]') ||
               document.querySelector('[data-testid="back"]');
   if (btn && isVisible(btn)) { btn.click(); await wait(800); }
  };

  // Close all open panels
  const closeAll = async () => {
   for (let i = 0; i < 4; i++) {
    const btn = document.querySelector('button[aria-label="Back"]') ||
                document.querySelector('[data-testid="back"]');
    if (btn && isVisible(btn)) { btn.click(); await wait(500); }
    else break;
   }
  };

  try {
   // 1. Open Settings → Privacy
   await openSettings();
   if (!(await clickMenuItem(['Privacy']))) {
    await closeAll();
    throw new Error('Privacy menu item not found');
   }

   const valueMap = {
    'all': 'Everyone',
    'contacts': 'My contacts',
    'none': 'Nobody',
    'nobody': 'Nobody'
   };

   if (category === 'read_receipts') {
    // Read receipts is a toggle switch, not radio buttons
    const toggle = document.querySelector('[role="switch"]') ||
                   document.querySelector('input[type="checkbox"]');
    if (toggle) {
     const want = (value === 'all' || value === true || value === 'contacts');
     const current = toggle.getAttribute('aria-checked') === 'true' || toggle.checked;
     if (current !== want) toggle.click();
    }
    await wait(500);
    await closeAll();
    return true;
   }

   // 2. Click the category
   const catLabels = {
    'last_seen': ['Last seen and online', 'Last seen'],
    'profile_pic': ['Profile picture', 'Profile photo'],
    'about': ['About'],
    'status': ['Status']
   };
   if (!(await clickMenuItem(catLabels[category] || [category]))) {
    await closeAll();
    throw new Error(`Privacy category "${category}" not found in DOM`);
   }

   // 3. Select the value
   const label = valueMap[value] || value;
   if (!(await selectRadio(label))) {
    await closeAll();
    throw new Error(`Privacy option "${label}" not found`);
   }

   // 4. Special: "Who can see when I'm online" (only for last_seen)
   if (category === 'last_seen') {
    await wait(500);
    const onlineLabel = value === 'all' ? 'Everyone' : 'Same as last seen';
    await selectRadio(onlineLabel);
   }

   await wait(500);
   await closeAll();
   return true;

  } catch (e) {
   try { await closeAll(); } catch (_) {}
   throw e;
  }
 };

 window.Astra.getPrivacySettings = async () => {
  return await window.Astra.withLock(async () => {
  const Store = window.Astra.initializeEngine();

  // Try require() first
  const requireNames = [
   'WAWebPrivacySettingsAction',
   'WAWebPrivacySettingsModel',
   'WAWebSetPrivacySettingsAction',
   'WAWebPrivacyModel'
  ];
  for (const modName of requireNames) {
   try {
    const mod = window.require(modName);
    const resolve = (m) => {
     if (typeof mod[m] === 'function') return mod[m]();
     if (mod.default && typeof mod.default[m] === 'function') return mod.default[m]();
     return null;
    };
    const s = {
     last_seen: await resolve('getPrivacyLastSeen'),
     profile_pic: await resolve('getPrivacyProfilePic'),
     about: await resolve('getPrivacyAbout'),
     status: await resolve('getPrivacyStatus'),
     read_receipts: await resolve('getPrivacyReadReceipts')
    };
    if (Object.values(s).some(v => v !== null)) return s;
   } catch (_) {}
  }

  // Store fallback
  const storeKeys = ['PrivacySettings', 'Privacy'];
  for (const key of storeKeys) {
   const mod = Store[key];
   if (!mod) continue;
   try {
    const resolve = (method) => {
     if (typeof mod[method] === 'function') return mod[method]();
     for (const sub of Object.values(mod)) {
      if (sub && typeof sub[method] === 'function') return sub[method]();
     }
     return null;
    };
    const s = {
     last_seen: await resolve('getPrivacyLastSeen'),
     profile_pic: await resolve('getPrivacyProfilePic'),
     about: await resolve('getPrivacyAbout'),
     status: await resolve('getPrivacyStatus'),
     read_receipts: await resolve('getPrivacyReadReceipts')
    };
    if (Object.values(s).some(v => v !== null)) return s;
   } catch (_) {}
  }

  return { last_seen: null, profile_pic: null, about: null, status: null, read_receipts: null };
  }); // end withLock
 };
})();
"""

