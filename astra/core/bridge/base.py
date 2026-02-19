# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

CORE_SCRIPT = r"""
window.Astra = window.Astra || {};
(function() {
 if (window.Astra.bridge_initialized) return;
 window.Astra.ensureSidebar = async (label, open = true) => {
  console.log(`[Astra] ensureSidebar: ${label} (open=${open})`);

  const testIdMap = {
   'settings': 'menu-bar-settings',
   'profile': 'menu-bar-profile',
   'status': 'menu-bar-status',
   'updates': 'menu-bar-status',
   'chats': 'menu-bar-chats'
  };
  const tid = testIdMap[label.toLowerCase()];

  const isVisible = (el) => {
   if (!el) return false;
   const style = window.getComputedStyle(el);
   if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
   const rect = el.getBoundingClientRect();
   return rect.width > 0 && rect.height > 0;
  };

  const findButton = () => {
   // Priority 1: Semantic aria-label matching the exact label
   const ariaBtn = document.querySelector(`button[aria-label="${label}" i]`) ||
       document.querySelector(`[role="button"][aria-label="${label}" i]`);
   if (isVisible(ariaBtn)) return ariaBtn;

   // Priority 2: data-testid from map
   if (tid) {
    const b = document.querySelector(`[data-testid="${tid}"]`);
    if (isVisible(b)) return b;
   }

   // Priority 3: Search all buttons for text
   return Array.from(document.querySelectorAll('button[aria-label], [role="button"]')).find(b => {
    const attr = b.getAttribute('aria-label') || b.getAttribute('title') || b.innerText || "";
    return attr.toLowerCase().includes(label.toLowerCase()) && isVisible(b);
   });
  };

  const getActiveDrawer = () => {
   const isVisible = (el) => {
    if (!el) return false;
    const style = window.getComputedStyle(el);
    return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
   };

   // Firefox/Modern UI robust isolation
   const scrollables = Array.from(document.querySelectorAll('div[scrollable="true"]')).filter(isVisible);
   const sideDrawer = scrollables.find(el => {
    const rect = el.getBoundingClientRect();
    return rect.x < 200 && !el.closest('#pane-side');
   });
   if (sideDrawer) return sideDrawer;

   // Legacy/Testid fallbacks
   const leftDrawer = document.querySelector('[data-testid="drawer-left"]');
   if (isVisible(leftDrawer)) return leftDrawer;

   return document.querySelector('.drawer-open') || document.querySelector('#app > div > span:nth-child(4) > div');
  };

  const checkIsOpen = () => {
   const drawer = getActiveDrawer();
   if (!drawer || !isVisible(drawer)) return false;

   const text = (drawer.innerText || "").toLowerCase();
   const header = drawer.querySelector('h1, h2, header, [data-testid="drawer-left-header"]');
   const headerText = header ? header.innerText.toLowerCase() : "";

   if (headerText.includes(label.toLowerCase())) return true;

   if (label.toLowerCase() === 'settings') {
    return ['settings', 'privacy', 'account', 'chats', 'help'].some(term => text.includes(term));
   }
   return false;
  };

  let isOpen = checkIsOpen();

  if (open) {
   if (isOpen) {
    console.log(`[Astra] Sidebar ${label} already open.`);
    return;
   }
   const btn = findButton();
   if (btn) {
    console.log(`[Astra] Clicking ${label} button...`);
    btn.click();
    await new Promise(r => setTimeout(r, 2000));

    if (!checkIsOpen()) {
     console.warn(`[Astra] Sidebar still not detected after click, retrying with semantic search...`);
     // If button didn't work, try clicking the icon specifically
     const icon = btn.querySelector('span[data-testid]') || btn;
     icon.click();
     await new Promise(r => setTimeout(r, 2000));
    }
   } else {
    console.error(`[Astra] CRITICAL: Sidebar button ${label} not found!`);
   }
  } else if (!open && isOpen) {
   console.log(`[Astra] Closing sidebar ${label}...`);
   const drawer = getActiveDrawer();
   const closeBtn = drawer ? (drawer.querySelector('button[aria-label="Back"]') ||
          drawer.querySelector('[data-testid="back"]') ||
          drawer.querySelector('button[aria-label="Close"]')) : null;
   if (closeBtn) {
    closeBtn.click();
   } else {
    // Global fallback
    const fallback = document.querySelector('button[aria-label="Back"], [data-testid="back"]');
    if (fallback) fallback.click();
   }
   await new Promise(r => setTimeout(r, 1200));
  }
 };

 window.Astra.openChat = async (chatId) => {
  console.log(`[Astra] openChat: ${chatId}`);
  const Store = window.Astra.initializeEngine();
  const chat = Store.Chat.get(chatId);

  // Try internal first
  if (chat && Store.Cmd && Store.Cmd.openChatAt) {
   try {
    await Promise.race([
     Store.Cmd.openChatAt(chat),
     new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 3000))
    ]);
    await new Promise(r => setTimeout(r, 1000));
    return true;
   } catch (e) {
    console.warn(`[Astra] Internal openChatAt failed: ${e.message}`);
   }
  }

  // DOM Fallback: Main Selector (cell-frame-container)
  console.log(`[Astra] Using DOM fallback for chat: ${chatId}`);
  const idStr = (chatId && chatId._serialized) ? chatId._serialized : String(chatId);
  const cells = document.querySelectorAll('[data-testid="cell-frame-container"]');
  for (const cell of cells) {
   if (cell.innerHTML.includes(idStr)) {
    cell.click();
    await new Promise(r => setTimeout(r, 1500));
    return true;
   }
  }

  // Legacy Fallback: Search for the title or partial match
  const userPart = idStr.split('@')[0];
  const chatElement = document.querySelector(`span[title*="${idStr}"], span[title*="${userPart}"]`);
  if (chatElement) {
   chatElement.click();
   await new Promise(r => setTimeout(r, 1500));
   return true;
  }

  // Search bar fallback
  await window.Astra.runDOMAction([
   { selector: 'div[role="textbox"][title="Search input textbox"]', action: 'type', value: idStr, wait: 500 },
   { selector: `span[title*="${userPart}"]`, action: 'click', wait: 1500 }
  ]);

  return !!document.querySelector('header');
 };

 window.Astra.runDOMAction = async (steps) => {
  console.log(`[Astra] runDOMAction: ${steps.length} steps`);
  for (let i = 0; i < steps.length; i++) {
   const step = steps[i];
   console.log(`[Astra] Step ${i}: ${step.action} on ${step.selector || step.dataTestId || 'manual element'}`);

   if (step.wait) await new Promise(r => setTimeout(r, step.wait));
   let el = step.element;

   if (!el) {
    if (step.dataTestId) {
     el = document.querySelector(`[data-testid="${step.dataTestId}"]`);
    }
    if (!el && step.selector) {
     if (step.text) {
      el = Array.from(document.querySelectorAll(step.selector)).find(e => e.innerText && e.innerText.includes(step.text));
     } else {
      el = document.querySelector(step.selector);
     }
    }
   }

   if (!el) {
    console.warn(`[Astra] Element not found for step ${i}: ${step.selector || step.dataTestId}`);
    continue;
   }

   if (step.action === 'click') {
    el.click();
   } else if (step.action === 'type') {
    el.focus();
    try {
     document.execCommand('selectAll', false, null);
     document.execCommand('delete', false, null);
     document.execCommand('insertText', false, step.value);
    } catch (e) {
     el.innerText = step.value;
    }
    el.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: step.value }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.blur();
   }
  }
 };

 window.Astra.observeDOM = (selector, callback, options = { childList: true, subtree: true }) => {
  const target = document.querySelector(selector);
  if (!target) return null;
  const observer = new MutationObserver(callback);
  observer.observe(target, options);
  return observer;
 };

 window.Astra.autoTakeover = async () => {
  const check = () => {
   const btn = Array.from(document.querySelectorAll('button, div[role="button"]')).find(b => b.innerText && b.innerText.includes('Use here'));
   if (btn) {
    console.log('[Astra] Auto-Takeover: Clicking "Use here"');
    btn.click();
   }
  };
  setInterval(check, 3000);
  check();
 };

 window.Astra.autoTakeover();

 window.Astra.bridge_initialized = true;

 // Redirect console to Python
 const consoleLevels = ['log', 'error', 'warn', 'debug'];
 consoleLevels.forEach(level => {
  const originalLog = console[level];
  console[level] = function(...args) {
   originalLog.apply(console, args);
   // Bridge logging to Python via astra_uplink
   if (window.astra_uplink) {
    try {
     // Send to Python as 'log' event
     window.astra_uplink('log', { level, msg: args.map(a => String(a)).join(' ') });
    } catch(e) {}
   }
  };
 });

 const engineRaid = function () {
  let webpackRequire = window.__w || window.require;
  const chunkName = 'webpackChunkwhatsapp_web_client';
  const chunk = window[chunkName] || window['webpackChunk_whatsapp_web_client'] || [];

  const capture = (e) => {
   if (!webpackRequire && e) {
    webpackRequire = e;
    if (!window.__w) window.__w = e;
    console.log('[Astra] Engine captured via raid.');
   }
  };

  // 1. Try to capture via push
  try {
   chunk.push([["astra_raid"], {}, capture]);
  } catch (e) {}

  // 2. Fallback: Hook future pushes
  if (chunk && !chunk._astra_hooked) {
   const originalPush = chunk.push;
   chunk.push = function(...args) {
    const res = originalPush.apply(chunk, args);
    if (args[0] && args[0][2] && !webpackRequire) {
     try { args[0][2](capture); } catch(e) {}
    }
    return res;
   };
   chunk._astra_hooked = true;
  }

  return {
   findModule: (filter) => {
    const isString = typeof filter === 'string';
    const m = webpackRequire && (webpackRequire.m || webpackRequire.c);
    if (m) {
     for (let id in m) {
      try {
       const mod = webpackRequire(id);
       if (mod) {
        const check = (target) => {
         if (!target) return false;
         if (isString) return target[filter] !== undefined || (target.default && target.default[filter] !== undefined);
         return filter(target);
        };
        if (check(mod)) return mod;
        if (mod.default && check(mod.default)) return mod.default;
        if (mod.exports && check(mod.exports)) return mod.exports;
        }
      } catch (e) {}
     }
    }
    return null;
   },
   webpackRequire
  };
 }();

 window.Astra.getChat = async (wid) => {
  const Store = window.Astra.initializeEngine();
  const chatWid = typeof wid === 'string' ? Store.WidFactory.createWid(wid) : wid;

  let chat = Store.Chat ? Store.Chat.get(chatWid) : null;
  if (!chat && Store.ChatRepo) chat = Store.ChatRepo.get(chatWid);

  if (!chat && Store.FindOrCreateChat && Store.FindOrCreateChat.findOrCreateLatestChat) {
   try { chat = (await Store.FindOrCreateChat.findOrCreateLatestChat(chatWid))?.chat; } catch(e) {}
  }

  if (!chat && Store.Chat && Store.Chat.find) {
   try { chat = await Store.Chat.find(chatWid); } catch(e) {}
  }

  return chat;
 };

 window.Astra.createWid = (input) => {
  const Store = window.Astra.initializeEngine();
  if (!input) return null;
  if (typeof input === 'object' && input._serialized) return input;
  if (typeof input === 'object' && input.user && input.server) return input; // Partial Wid object
  try {
   const serialized = typeof input === 'string' ? input : (input._serialized || (input.toString ? input.toString() : String(input)));
   return Store.WidFactory.createWid(serialized);
  } catch (e) {
   console.error('[Astra] createWid failed for:', input, e.message);
   return null;
  }
 };

 window.Astra.mR = engineRaid;
 if (engineRaid.webpackRequire && !window.require) {
  window.require = engineRaid.webpackRequire;
 }

 window.Astra.initializeEngine = function() {
  if (window.Store && window.Store.Chat && window.Store.Msg && window.Store.SendMessage) return window.Store;

  window.Store = window.Store || {};
  window.AuthStore = window.AuthStore || {};

  const moduleMap = {
   AppState: 'WAWebSocketModel',
   Conn: 'WAWebConnModel',
   Cmd: 'WAWebCmd',
   DownloadManager: 'WAWebDownloadManager',
   GroupQueryAndUpdate: 'WAWebGroupQueryJob',
   MediaPrep: 'WAWebPrepRawMedia',
   MediaObject: 'WAWebMediaStorage',
   MediaTypes: 'WAWebMmsMediaTypes',
   MediaUpload: 'WAWebMediaMmsV4Upload',
   MediaUpdate: 'WAWebMediaUpdateMsg',
   MsgKey: 'WAWebMsgKey',
   OpaqueData: 'WAWebMediaOpaqueData',
   SendMessage: 'WAWebSendMsgChatAction',
   MessageSender: 'WAWebSendMsgChatAction',
   EditMessage: 'WAWebSendMessageEditAction',
   MediaDataUtils: 'WAWebMediaDataUtils',
   BlobCache: 'WAWebMediaInMemoryBlobCache',
   SendSeen: 'WAWebUpdateUnreadChatAction',
   User: 'WAWebUserPrefsMeUser',
   WidFactory: 'WAWebWidFactory',
   ProfilePic: 'WAWebContactProfilePicThumbBridge',
   PresenceUtils: 'WAWebPresenceChatAction',
   ChatState: 'WAWebChatStateBridge',
   ConversationMsgs: 'WAWebChatLoadMessages',
   sendReactionToMsg: 'WAWebSendReactionMsgAction',
   createOrUpdateReactionsModule: 'WAWebDBCreateOrUpdateReactions',
   EphemeralFields: 'WAWebGetEphemeralFieldsMsgActionsUtils',
   MsgActionChecks: 'WAWebMsgActionCapability',
   QuotedMsg: 'WAWebQuotedMsgModelUtils',
   WidToJid: 'WAWebWidToJid',
   JidToWid: 'WAWebJidToWid',
   QueryExist: 'WAWebQueryExistsJob',
   ReplyUtils: 'WAWebMsgReply',
   WAWebStreamModel: 'WAWebStreamModel',
   FindOrCreateChat: 'WAWebFindChatAction',
   GroupCreate: 'WAWebGroupCreateJob',
   GroupUtils: 'WAWebGroupUtils',
   GroupParticipants: 'WAWebModifyParticipantsGroupAction',
   GroupInvite: 'WAWebGroupInviteJob',
   Polls: 'WAWebSendCreatePollMsgAction',
   PollsSendVote: 'WAWebPollsSendVoteMsgAction',
   PinnedMsgUtils: 'WAWebSendPinMessageAction',
   MembershipRequestUtils: 'WAWebApiMembershipApprovalRequestStore',
   HistorySync: 'WAWebSendNonMessageDataRequest',
   PrivacySettings: 'WAWebPrivacySettingsAction',
   PrivacyConstants: 'WAWebPrivacySettings',
   Settings: 'WAWebSetPushnameConnAction',
   StatusUtils: 'WAWebContactStatusBridge',
   ProfilePicRepo: 'WAWebContactProfilePicThumbBridge'
  };

  const requireFunc = window.require || window.__w;
  if (requireFunc) {
   // Suppress WA's ErrorUtils during require to avoid console noise
   const safeRequire = (name) => {
    const origReporter = window.ErrorUtils && window.ErrorUtils.reportError;
    const origError = console.error;
    try {
     if (window.ErrorUtils) window.ErrorUtils.reportError = () => {};
     console.error = () => {};
     return requireFunc(name);
    } catch (e) {
     return null;
    } finally {
     if (window.ErrorUtils && origReporter) window.ErrorUtils.reportError = origReporter;
     console.error = origError;
    }
   };

   // 1. Initial Collections Load (WAWebCollections is the foundation)
   const collections = safeRequire('WAWebCollections');
   if (collections) {
    Object.assign(window.Store, collections);
   }

   // 2. Map other modules with exact property matching
   for (let alias in moduleMap) {
    const mod = safeRequire(moduleMap[alias]);
    if (mod) {
     // Critical matching logic from Store.js
     if (alias === 'Conn') window.Store.Conn = mod.Conn;
     else if (alias === 'Cmd') window.Store.Cmd = mod.Cmd;
     else if (alias === 'AppState') window.Store.AppState = mod.Socket;
     else if (alias === 'DownloadManager') window.Store.DownloadManager = mod.downloadManager || mod.DownloadManager || mod;
     else if (alias === 'GroupQueryAndUpdate') window.Store.GroupQueryAndUpdate = mod.queryAndUpdateGroupMetadataById;
     else if (alias === 'GroupUtils') {
      window.Store.GroupUtils = {
       ...mod,
       ...safeRequire('WAWebGroupModifyInfoJob'),
       ...safeRequire('WAWebExitGroupAction')
      };
     }
     else if (alias === 'QueryExist') window.Store.QueryExist = mod.queryWidExists || mod.queryExist;
     else if (alias === 'SendMessage') window.Store.SendMessage = mod;
     else if (alias === 'User') window.Store.User = mod;
     else if (alias === 'WAWebStreamModel') window.Store.WAWebStreamModel = mod;
     else window.Store[alias] = mod.default || mod[alias] || mod;
    }
   }

   // Aliases for compatibility with Astra scripts
   window.Store.AddressFactory = window.Store.WidFactory;
   window.Store.UserCredentials = window.Store.User;
   window.Store.ChatRepo = window.Store.Chat;
   window.Store.MsgRepo = window.Store.Msg;
   window.Store.ContactRepo = window.Store.Contact;
   window.Store.ChatMeta = window.Store.ChatGetters || window.Store.Chat;

   // 3. AuthStore initialization
   window.AuthStore.Conn = window.Store.Conn;
   window.AuthStore.AppState = window.Store.AppState;
   window.AuthStore.Base64Tools = safeRequire('WABase64');
   window.AuthStore.RegistrationUtils = {
    ...safeRequire('WAWebCompanionRegClientUtils'),
    ...safeRequire('WAWebAdvSignatureApi'),
    ...safeRequire('WAWebUserPrefsInfoStore'),
    ...safeRequire('WAWebSignalStoreApi'),
   };
  }

  // Heuristics for missing modules (Expanded)
  const engineHeuristics = {
   Chat: (m) => m && m.get && m.add && (m.getModelsArray || (m.models && m.models.getModelsArray)) && m.models,
   Msg: (m) => m && m.get && m.add && (m.getModelsArray || (m.models && m.models.getModelsArray)) && m.models && m.getMessagesById,
   Contact: (m) => m && m.get && m.add && (m.getModelsArray || (m.models && m.models.getModelsArray)) && m.models && m.getMaybeMePnUser,
   SendMessage: (m) => (m.addAndSendMsgToChat && m.resendMsgToChat) || (m.sendMsgToChat && m.prepareMsg),
   MsgKey: (m) => m.prototype && m.prototype.fromString && m.prototype.obj,
   Conn: (m) => m.Conn && (m.Conn.wid || m.Conn.me),
   User: (m) => m.getMaybeMeLidUser || m.getMaybeMePnUser || m.getMePnUserOrThrow,
   WidFactory: (m) => m.createWid && m.asUserWidOrThrow,
   GroupCreate: (m) => m.createGroup && m.WAWebGroupCreateJob,
   Status: (m) => (m.setMyStatus || m.updateStatus || m.postStatus || (typeof m === 'object' && Object.values(m).some(v => v && v.postStatus))) && (m.getStatusViewers || m.viewStatus || (typeof m === 'object' && Object.values(m).some(v => v && v.getStatusViewers))),
   Settings: (m) => m.setPushname || (m.Conn && m.Conn.pushname),
   StatusV3Action: (m) => m.postStatusV3 || m.sendStatusV3 || m.postStatus || m.sendTextStatus || (typeof m === 'object' && Object.values(m).some(v => v && (v.postStatusV3 || v.postStatus || v.sendTextStatus))),
   PrivacySettings: (m) => m && (m.setPrivacyLastSeen || m.getPrivacyLastSeen || m.getPrivacyAbout || (typeof m === 'object' && Object.values(m).some(v => v && (v.setPrivacyLastSeen || v.setPrivacyAbout)))),
   Polls: (m) => m && (m.sendCreatePollMsgs || m.createPollMsg || m.postPoll || m.sendPoll || (typeof m === 'object' && Object.values(m).some(v => v && (v.sendCreatePollMsgs || v.sendPoll)))),
   BlockAction: (m) => m && (m.blockContact || m.blockUser) && (m.unblockContact || m.unblockUser),
   AccountUtils: (m) => m && (m.setPushname || m.setAbout || m.setMyStatus)
  };

  for (let alias in engineHeuristics) {
   if (!window.Store[alias]) {
    try {
     const found = engineRaid.findModule(engineHeuristics[alias]);
     if (found) {
      window.Store[alias] = found;
      console.log(`[Astra] Found heuristic match for: ${alias}`);
      if (alias === 'Conn') window.AuthStore.Conn = window.Store.Conn;
      if (alias === 'AppState') window.AuthStore.AppState = window.Store.AppState;
     } else {
      console.debug(`[Astra] Heuristic miss: ${alias}`);
     }
    } catch (e) {
     console.warn(`[Astra] Heuristic check failed for ${alias}:`, e.message);
    }
   } else {
    console.log(`[Astra] ${alias} already present in Store.`);
   }
  }

  // Additional heuristics for media/upload utilities
  try {
   if (!window.Store.AssetUploader) {
    const found = engineRaid.findModule(m => m && (m.uploadMedia || m.upload));
    if (found) {
     window.Store.AssetUploader = found;
     console.warn('[Astra] Heuristic: mapped AssetUploader');
    }
   }
   if (!window.Store.MediaBuffer) {
    const found = engineRaid.findModule(m => m && (m.createFromData || m.fromData));
    if (found) {
     window.Store.MediaBuffer = found;
     console.warn('[Astra] Heuristic: mapped MediaBuffer/OpaqueData');
    }
   }
   if (!window.Store.UploadUtils) {
    const found = engineRaid.findModule(m => m && (m.encryptAndUpload || m.encryptAndUploadWithQpl));
    if (found) {
     window.Store.UploadUtils = found;
     console.warn('[Astra] Heuristic: mapped UploadUtils');
    }
   }
   if (!window.Store.MediaUpload) {
    const found = engineRaid.findModule(m => m && (m.startMediaUploadQpl || m.uploadMedia || m.startUpload));
    if (found) {
     window.Store.MediaUpload = found;
     console.warn('[Astra] Heuristic: mapped MediaUpload');
    }
   }
  } catch (e) {
   console.warn('[Astra] Media heuristics failed:', e.message);
  }

  // --- QR Capture Stabilization (Full Reconstruction) ---
  if (window.AuthStore.Conn) {
   const getQRString = async (ref) => {
    try {
     if (!ref) return null;
     if (ref.includes(',')) return ref; // Already full

     console.log('[Astra] Attempting QR reconstruction for ref:', ref.substring(0, 10) + '...');

     const regUtils = window.AuthStore.RegistrationUtils;
     const b64 = window.AuthStore.Base64Tools;

     if (!regUtils || !regUtils.waSignalStore || !b64) {
      console.error('[Astra] QR reconstruction delayed: RegistrationUtils or Base64Tools not fully loaded.');
      return ref;
     }

     const registrationInfo = await regUtils.waSignalStore.getRegistrationInfo();
     const noiseKeyPair = await regUtils.waNoiseInfo.get();

     if (!registrationInfo || !noiseKeyPair) {
      console.error('[Astra] QR reconstruction failed: RegistrationInfo or NoiseKeyPair missing.');
      return ref;
     }

     const staticKeyB64 = b64.encodeB64(noiseKeyPair.staticKeyPair.pubKey);
     const identityKeyB64 = b64.encodeB64(registrationInfo.identityKeyPair.pubKey);
     const advSecretKey = await regUtils.getADVSecretKey();
     const platform = regUtils.DEVICE_PLATFORM;

     const fullQR = ref + ',' + staticKeyB64 + ',' + identityKeyB64 + ',' + advSecretKey + ',' + platform;
     console.log('[Astra] QR SUCCESS! Constructed full string (Length: ' + fullQR.length + ')');
     return fullQR;
    } catch (e) {
     console.error('[Astra] QR reconstruction error:', e.message);
     return ref;
    }
   };

   if (!window.Astra._qrListenerAttached) {
    const runCapture = async () => {
     // Force refresh ONLY if we are at login screen and stuck
     const isAtLogin = !!(document.querySelector('canvas') || document.querySelector('[data-testid="qrcode"]'));
     if (isAtLogin && !window.AuthStore.Conn.ref) {
      try {
       // Ultra-safe call with optional chaining
       window.Store.Cmd?.refreshQR?.();
      } catch (e) {
       console.warn('[Astra] Optional refreshQR failed:', e.message);
      }
     }

     const updateQR = async (ref) => {
      const qr = await getQRString(ref);
      if (qr) {
       window.Astra.lastQR = qr;
      }
     };

     const initialRef = window.AuthStore.Conn.ref;
     if (initialRef) await updateQR(initialRef);

     window.AuthStore.Conn.on('change:ref', async (_, ref) => {
      console.log('[Astra] Conn:change:ref triggered.');
      await updateQR(ref);
     });

     // Periodic poll as safety fallback
     setInterval(async () => {
      const currentRef = window.AuthStore.Conn.ref;
      if (currentRef && (!window.Astra.lastQR || !window.Astra.lastQR.includes(','))) {
       await updateQR(currentRef);
      }
     }, 5000);
    };

    runCapture().catch(e => console.error('[Astra] runCapture failed:', e));
    window.Astra._qrListenerAttached = true;
   }
  }

  // WA compatibility shim: normalize remote/participant
  if (window.Store.MsgKey && typeof window.Store.MsgKey.from === 'function' &&
   window.Store.WidFactory && typeof window.Store.WidFactory.createWid === 'function' &&
   !window.Store.MsgKey.__astra_from_patched) {
   const originalFrom = window.Store.MsgKey.from.bind(window.Store.MsgKey);
   const toWid = (value) => {
    if (!value) return value;
    if (typeof value.isBot === 'function') return value;
    try {
     const serialized = typeof value === 'string'
      ? value
      : (value._serialized || (value.toString ? value.toString() : null));
     if (!serialized) return value;
     return window.Store.WidFactory.createWid(serialized);
    } catch (e) {
     return value;
    }
   };

   window.Store.MsgKey.from = function(value) {
    const key = originalFrom(value);
    if (key) {
     key.remote = toWid(key.remote);
     if (key.participant) key.participant = toWid(key.participant);
    }
    return key;
   };
   window.Store.MsgKey.__astra_from_patched = true;
  }

  // Legacy compatibility for internal use
  window.InternalStore = window.Store;

  // --- Immediate Event Hooking (Elite V24) ---
  if (window.Store.Msg && typeof window.Store.Msg.on === 'function') {
   if (!window.Astra._msgListenerAttached) {
    const handleNewMsg = (msg) => {
     try {
      const serialized = window.Astra.serializeMsg(msg);
      if (!serialized) return;

      // wwaa logic: only process new messages for automation
      // or handle ciphertext resolution
      if (msg.type === 'ciphertext') {
       msg.once('change:type', (_msg) => handleNewMsg(_msg));
       return;
      }

      console.log(`[Astra] Capture: ${serialized.id} (New: ${msg.isNewMsg})`);

      if (window.Astra.emit) {
       console.log(`[Astra] Emitting 'msg' to Python for ${serialized.id}`);
       window.Astra.emit('msg', serialized);
      } else if (window.py_onMessage) {
       console.log(`[Astra] Fallback: py_onMessage for ${serialized.id}`);
       window.py_onMessage(serialized);
      }
     } catch (e) {
      console.error('[Astra] Error capturing message:', e);
     }
    };

    window.Store.Msg.on('add', handleNewMsg);
    window.Store.Msg.on('change:body', (msg) => {
     const s = window.Astra.serializeMsg(msg);
     if (window.Astra.emit) window.Astra.emit('msg_edit', s);
    });
    window.Store.Msg.on('change:ack', (msg) => {
     const s = window.Astra.serializeMsg(msg);
     if (window.Astra.emit) window.Astra.emit('msg_ack', s);
    });
    window.Store.Msg.on('change:star', (msg) => {
     const s = window.Astra.serializeMsg(msg);
     if (window.Astra.emit) window.Astra.emit('msg_star', s);
    });
    window.Store.Msg.on('change:isRevoked', (msg) => {
     const s = window.Astra.serializeMsg(msg);
     if (window.Astra.emit) window.Astra.emit('msg_revoke', s);
    });

    window.Astra._msgListenerAttached = true;
    console.log('[Astra] Message pipeline hooked (Elite V24).');
   }
  }

  // Hook Reactions (Special V24/MEX handling)
  if (window.Store.AddonReactionTable) {
   const module = window.Store.AddonReactionTable;
   if (!module._astra_hooked) {
    const ogBulkUpsert = module.bulkUpsert;
    module.bulkUpsert = ((...args) => {
     if (args[0] && Array.isArray(args[0])) {
      args[0].forEach(reaction => {
       if (window.Astra.emit) {
        window.Astra.emit('reaction', {
         id: reaction.id._serialized || reaction.id,
         msgId: reaction.reactionParentKey._serialized || reaction.reactionParentKey,
         sender: (reaction.author || reaction.from)?._serialized,
         emoji: reaction.reactionText,
         timestamp: reaction.reactionTimestamp
        });
       }
      });
     }
     return ogBulkUpsert.apply(module, args);
    }).bind(module);
    module._astra_hooked = true;
    console.log('[Astra] Reaction pipeline hooked via bulkUpsert.');
   }
  }

  return window.Store;
 };

 // "Fetch Everything" - Deep metadata sync for all entities
 window.Astra.deepSync = async function() {
  const Store = window.Astra.initializeEngine();
  console.log("[Astra] Starting deepSync (Fetch Everything)...");

  const tasks = [];
  // 1. Sync Contacts
  const contacts = (Store.ContactRepo && Store.ContactRepo.models) || (Store.Contact && Store.Contact.models) || [];
  contacts.forEach(c => {
   if (c.fetchValue) tasks.push(c.fetchValue().catch(() => {}));
   else if (c.queryContact) tasks.push(c.queryContact().catch(() => {}));
  });

  // 2. Sync Group Metadata
  const chats = (Store.ChatRepo && Store.ChatRepo.models) || (Store.Chat && Store.Chat.models) || [];
  chats.forEach(chat => {
   if (chat.isGroup && chat.groupMetadata && chat.groupMetadata.query) {
    tasks.push(chat.groupMetadata.query().catch(() => {}));
   }
  });

  await Promise.allSettled(tasks);
  console.log("[Astra] deepSync complete.");
  return true;
 };

 window.Astra.deepScanModules = function(query = '') {
  const results = [];
  const mR = window.Astra.mR;
  const wr = mR && mR.webpackRequire;
  const m = wr && (wr.m || wr.c);
  const regex = new RegExp(query, 'i');

  const scan = (mod, id) => {
   if (!mod) return;
   const exports = mod.default || mod;
   const props = Object.keys(exports);
   const idMatch = id.toString().match(regex);
   const propMatch = props.some(p => p.match(regex));

   if (!query || idMatch || propMatch) {
    results.push({ id: id.toString(), props: props.filter(p => !p.startsWith('_')) });
   }
  };

  if (m) {
   for (let id in m) {
    if (results.length > 500) break;
    try { scan(wr(id), id); } catch(e) {}
   }
  } else {
   const chunkName = 'webpackChunkwhatsapp_web_client';
   const chunk = window[chunkName] || [];
   for (let c of chunk) {
    if (results.length > 500) break;
    if (c && c[1]) {
     for (let id in c[1]) {
      if (results.length > 500) break;
      try { scan(window.require(id), id); } catch(e) {}
     }
    }
   }
  }
  return results;
 };

 window.Astra.serializeMsg = (msg) => {
  if (!msg) return null;

  const serializeWid = (wid) => {
   if (!wid) return null;
   if (typeof wid === 'string') return wid;
   if (wid._serialized) return wid._serialized;
   if (wid.serialized) return wid.serialized;
   if (wid.id && typeof wid.id === 'string') return wid.id;
   if (wid.id && wid.id._serialized) return wid.id._serialized;
   if (wid.id) return wid.id;
   return String(wid);
  };

  let s = {};
  try {
   if (msg.serialize && typeof msg.serialize === 'function') s = msg.serialize();
   else if (msg.toJSON && typeof msg.toJSON === 'function') s = msg.toJSON();
   else s = {...msg};
  } catch (e) { s = {...msg}; }

  // Ensure accurate identities
  s.id = serializeWid(msg.id) || s.id;
  if (typeof s.id === 'object' && s.id._serialized) s.id = s.id._serialized;

  s.from = serializeWid(msg.from) || s.from;
  s.to = serializeWid(msg.to) || s.to;
  s.author = serializeWid(msg.author) || s.author;
  s.body = msg.caption || msg.body || msg.text || s.body || s.text || "";

  // Sanity Check: If body is massive base64 or thumbnail trash, clear it to prevent parsing errors
  if (s.body && s.body.length > 200 && (s.body.includes(';base64,') || s.body.startsWith('9j/'))) {
   console.log(`[Astra] Suppressed massive body content (Length: ${s.body.length})`);
   s.body = "";
  }

  s.type = msg.type || s.type || 'chat';
  s.fromMe = !!(msg.fromMe || (msg.id && msg.id.fromMe) || s.fromMe);
  s.chat_id = serializeWid(msg.id ? msg.id.remote : (msg.from || msg.to)) || s.chat_id;
  s.chatId = s.chat_id;
  s.timestamp = msg.t || msg.timestamp || s.t || s.timestamp || Math.floor(Date.now() / 1000);
  s.isEditable = !!(msg.canEdit ? (typeof msg.canEdit === 'function' ? msg.canEdit() : msg.canEdit) : msg.isEditable);

  // Aggressive Quoted Identification (Industry Standard Pattern)
  let qid = null;
  try {
   if (msg.quotedMsgId) qid = serializeWid(msg.quotedMsgId);
   else if (msg.quotedMsg && msg.quotedMsg.id) qid = serializeWid(msg.quotedMsg.id);
   else if (msg.contextInfo && msg.contextInfo.stanzaId) {
    // If we only have a stanzaId, we try to reconstruct or find the full ID
    const remote = s.from || s.to;
    const fromMe = false; // Usually true/false depending on context, but stanzaId is often enough if we find it in Store
    qid = msg.contextInfo.stanzaId;

    // Search Store for actual msg object to get full serialized ID
    if (window.Store && window.Store.Msg) {
     const found = window.Store.Msg.getModelsArray().find(m => m.id.id === qid || m.id.stanzaId === qid);
     if (found) qid = found.id._serialized;
    }
   }
   else if (msg.quotedStanzaID) qid = msg.quotedStanzaID;
   else if (window.Store && window.Store.QuotedMsg) {
    const qObj = window.Store.QuotedMsg.getQuotedMsgObj(msg);
    if (qObj && qObj.id) qid = serializeWid(qObj.id);
   }
  } catch (err) { console.warn('[Astra] Quoted ID extraction error:', err); }

  s.quotedMsgId = qid;
  s.hasQuotedMsg = !!qid;
  s.ack = msg.ack !== undefined ? msg.ack : s.ack;
  s.isNewMsg = !!(msg.isNewMsg || s.isNewMsg);
  s.hasMedia = !!(s.hasMedia || ['image', 'video', 'audio', 'document', 'sticker', 'ptt'].includes(s.type));

  // Enrichment: Capture quoted context if available for logic checks
  if (s.hasQuotedMsg && !s.quotedParticipant) {
   try {
    s.quotedParticipant = serializeWid(msg.quotedParticipant || (msg.quotedMsg ? msg.quotedMsg.author : null) || (msg.contextInfo ? msg.contextInfo.participant : null));
    if (!s.quotedParticipant && window.Store && window.Store.QuotedMsg) {
     const qObj = window.Store.QuotedMsg.getQuotedMsgObj(msg);
     if (qObj) s.quotedParticipant = serializeWid(qObj.author || qObj.from);
    }
   } catch (err) { }
  }

  if (s.hasQuotedMsg) {
   console.log(`[Astra] serializeMsg: Detected Quoted ID=${s.quotedMsgId} Participant=${s.quotedParticipant}`);
  }

  return s;
 };

 window.Astra.serializeChat = (chat) => {
  if (!chat) return null;
  return {
   id: chat.id._serialized || chat.id,
   name: chat.name || chat.formattedTitle || chat.pushname || (chat.contact ? (chat.contact.name || chat.contact.pushname) : null) || (chat.id ? chat.id.user : 'Unknown'),
   isGroup: typeof chat.isGroup === 'function' ? chat.isGroup() : !!chat.isGroup,
   unreadCount: chat.unreadCount || 0,
   timestamp: chat.t || 0,
   archive: !!chat.archive,
   pin: !!chat.pin,
   isReadOnly: !!chat.isReadOnly
  };
 };

 // Auto-init — only run full discovery when WA modules are actually available
 // (i.e., after auth, not on QR page where all requires fail)
 let _initAttempts = 0;
 const _tryInit = () => {
  _initAttempts++;
  const hasModules = !!(window.require || window.__w);
  const hasStore = !!(window.Store && window.Store.Chat);
  const isAppReady = !!document.querySelector('#app .two, #app ._3q4NP, [data-testid="chat-list"]');

  if (hasStore) {
   // Already initialized
   return;
  }

  if (hasModules && (isAppReady || _initAttempts > 2)) {
   window.Astra.initializeEngine();
  } else if (_initAttempts < 10) {
   // Retry — modules load progressively
   setTimeout(_tryInit, 3000);
  }
 };
 setTimeout(_tryInit, 2000);
})();

    window.Astra.getMe = function() {
        const Store = window.Astra.initializeEngine();
        if (Store.User && Store.User.getMeUser) {
            return Store.User.getMeUser();
        }
        // Fallback for different WA versions
        if (Store.User && Store.User.getMe) {
            return Store.User.getMe();
        }
        // Last resort: check Conn
        if (window.AuthStore.Conn) {
             return window.AuthStore.Conn.wid;
        }
        return null;
    };

"""
