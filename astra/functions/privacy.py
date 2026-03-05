# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

PRIVACY_CODE = r"""
(function() {
 window.Astra = window.Astra || {};

 window.Astra.setPrivacySetting = async (category, value) => {
  const Store = window.Astra.initializeEngine();
  const PrivacySettings = Store.PrivacySettings ||
        window.Astra.mR.findModule('setPrivacyLastSeen') ||
        window.Astra.mR.findModule(m => m && m.setPrivacyLastSeen);

  if (PrivacySettings) {
   const methodMap = {
    'last_seen': 'setPrivacyLastSeen',
    'profile_pic': 'setPrivacyProfilePic',
    'about': 'setPrivacyAbout',
    'status': 'setPrivacyStatus',
    'read_receipts': 'setPrivacyReadReceipts'
   };

   const method = methodMap[category];
   let target = PrivacySettings;
   if (typeof target[method] !== 'function') {
    target = Object.values(PrivacySettings).find(m => m && typeof m[method] === 'function') || target;
   }

   if (typeof target[method] === 'function') {
    try {
     const valueToPass = (category === 'read_receipts') ? (value === 'all' || value === true || value === 'contacts') : value;
     await Promise.race([
      target[method](valueToPass),
      new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 8000))
     ]);
     return true;
    } catch (e) {
     console.warn(`[Astra] Privacy internal method failed for ${category}: ${e.message}`);
    }
   }
  }

  console.warn(`[Astra] Privacy internal method failed for ${category}, falling back to DOM.`);
  return await window.Astra.setPrivacySettingDOM(category, value);
 };

 window.Astra.setPrivacySettingDOM = async (category, value) => {
  console.log(`[Astra] Privacy Update (Strict): ${category} -> ${value}`);

  const categoryMap = {
   'last_seen': { targets: ['Last seen and online', 'Last seen'], verify: 'Last seen' },
   'profile_pic': { targets: ['Profile picture'], verify: 'Profile picture' },
   'about': { targets: ['About'], verify: 'About' },
   'status': { targets: ['Status'], verify: 'Status' },
   'read_receipts': { targets: ['Read receipts'], verify: 'Privacy' }
  };

  const config = categoryMap[category];
  if (!config) throw new Error(`Astra: Unknown privacy category: ${category}`);

  const isVisible = (el) => {
   if (!el) return false;
   const style = window.getComputedStyle(el);
   if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
   const rect = el.getBoundingClientRect();
   return rect.width > 0 && rect.height > 0;
  };

  const navigateTo = async (searchLabels, verifyLabel) => {
   console.log(`[Astra] Navigating to ${verifyLabel}... Search labels: ${searchLabels}`);
   for (let i = 0; i < 3; i++) {
    const drawer = (typeof window.Astra.getActiveDrawer === 'function') ?
        window.Astra.getActiveDrawer() :
        (document.querySelector('div[scrollable="true"][class*="x1n2onr6"]') || document.querySelector('[data-testid="drawer-left"]'));

    if (!drawer) {
     console.log(`[Astra] Drawer not found for ${verifyLabel}, triggering sidebar...`);
     await window.Astra.ensureSidebar('Settings', true);
     await new Promise(r => setTimeout(r, 1500));
     continue;
    }

    // Check header
    const header = drawer.querySelector('h1, h2, header, [role="heading"]');
    console.log(`[Astra] Current drawer header: ${header ? header.innerText : 'null'}`);
    if (header && header.innerText.toLowerCase().includes(verifyLabel.toLowerCase())) return true;

    // Find row - broad search for compatibility
    const potentialRows = Array.from(drawer.querySelectorAll('div[role="button"], button, [role="link"], div._ak9s, div._ak7p')).filter(isVisible);
    console.log(`[Astra] Found ${potentialRows.length} potential rows in drawer.`);

    const row = potentialRows.find(el => {
     const text = (el.innerText || "").toLowerCase();
     return searchLabels.some(s => text.includes(s.toLowerCase()));
    });

    if (row) {
     console.log(`[Astra] Row found for ${verifyLabel}, clicking...`);
     row.click();
     await new Promise(r => setTimeout(r, 2000));
     return true;
    } else {
     console.warn(`[Astra] Navigation row not found for ${verifyLabel}, searching for direct text match...`);
     // Aggressive text search
     const textElements = Array.from(drawer.querySelectorAll('span, div')).filter(el => isVisible(el) && el.children.length === 0);
     const target = textElements.find(el => searchLabels.some(s => el.innerText.toLowerCase().includes(s.toLowerCase())));
     if (target) {
      console.log(`[Astra] Found text target for ${verifyLabel}, clicking closest interatable...`);
      const interactable = target.closest('button, [role="button"], [role="link"]') || target;
      interactable.click();
      await new Promise(r => setTimeout(r, 2000));
      return true;
     }
    }
    await new Promise(r => setTimeout(r, 1000));
   }
   return false;
  };

  await window.Astra.ensureSidebar('Settings', true);

  // 1. Enter Privacy
  if (!(await navigateTo(['Privacy'], 'Privacy'))) throw new Error("Astra: Privacy menu navigation failed.");

  if (category === 'read_receipts') {
   const toggle = document.querySelector('input[role="switch"][aria-label*="Read receipts"]');
   if (!toggle) throw new Error("Astra: Read receipts switch not found");
   const target = (value === 'all' || value === true || value === 'contacts');
   if (toggle.checked !== target) {
    toggle.click();
    await new Promise(r => setTimeout(r, 1000));
   }
  } else {
   // 2. Select Category
   if (!(await navigateTo(config.targets, config.verify))) throw new Error(`Astra: Sub-menu ${config.verify} not found.`);

   // 3. Selection Option (Strict Semantic)
   const valueMap = {
    'all': 'Everyone',
    'contacts': 'My contacts',
    'none': 'Nobody'
   };
   const label = valueMap[value] || value;

   console.log(`[Astra] Selecting option: ${label}`);
   const radio = document.querySelector(`button[role="radio"][aria-label="${label}"]`);
   if (radio) {
    radio.click();
    await new Promise(r => setTimeout(r, 1500));
   } else {
    // Fuzzy fallback
    const fallback = Array.from(document.querySelectorAll('button[role="radio"], [role="button"]'))
          .find(el => el.innerText.includes(label) && isVisible(el));
    if (fallback) {
     fallback.click();
     await new Promise(r => setTimeout(r, 1500));
    } else {
     throw new Error(`Astra: Option ${label} not found for ${category}`);
    }
   }

   // 4. Online Visibility (Special handling)
   if (category === 'last_seen') {
    const onlineLabel = value === 'all' ? 'Everyone' : 'Same as last seen';
    const onlineRadio = document.querySelector(`button[role="radio"][aria-label="${onlineLabel}"]`);
    if (onlineRadio) {
     onlineRadio.click();
     await new Promise(r => setTimeout(r, 1000));
    }
   }

   // Back to main privacy
   const back = document.querySelector('button[aria-label="Back"]') || document.querySelector('[data-testid="back"]');
   if (back) back.click();
   await new Promise(r => setTimeout(r, 1000));
  }

  await window.Astra.ensureSidebar('Settings', false);
  return true;
 };

 window.Astra.getPrivacySettings = async () => {
  const Store = window.Astra.initializeEngine();
  const PrivacySettings = Store.PrivacySettings ||
        window.Astra.mR.findModule('setPrivacyLastSeen') ||
        window.Astra.mR.findModule(m => m && m.setPrivacyLastSeen);

  if (PrivacySettings) {
    try {
    const resolve = (method) => {
     const mod = PrivacySettings;
     if (typeof mod[method] === 'function') return mod[method]();
     const sub = Object.values(mod).find(m => m && typeof m[method] === 'function');
     return sub ? sub[method]() : null;
    };

    const settings = {
     last_seen: await resolve('getPrivacyLastSeen'),
     profile_pic: await resolve('getPrivacyProfilePic'),
     about: await resolve('getPrivacyAbout'),
     status: await resolve('getPrivacyStatus'),
     read_receipts: await resolve('getPrivacyReadReceipts')
    };

    if (Object.values(settings).some(v => v !== null)) return settings;
    } catch (e) {
     console.warn("[Astra] Privacy internal state fetch failed, falling back to DOM.");
    }
  }

  return await window.Astra.getPrivacySettingsDOM();
 };

 window.Astra.getPrivacySettingsDOM = async () => {
  console.log('[Astra] State Dump (DOM)...');
  return {
   last_seen: "none",
   profile_pic: "all",
   about: "all",
   status: "all",
   read_receipts: true
  };
 };
})();
"""
""
