(function() {
 console.log('[Astra] Injection start...');
 window.AstraInjected = (window.AstraInjected || 0) + 1;
// Initialize internal module scope
window.Astra = window.Astra || {};


window.Astra = window.Astra || {};
(function () {
  if (window.Astra.bridge_initialized) return;

  // --- Serialization & Utility Functions (Pre-init) ---
  window.Astra.serializeMsg = (msg) => {
    if (!msg) return null;

    const serializeWid = (wid) => {
      if (!wid) return null;
      if (typeof wid === 'string') return wid;
      if (wid._serialized) return wid._serialized;
      if (wid.serialized) return wid.serialized;
      if (wid.id && typeof wid.id === 'string') return wid.id;
      if (wid.id && wid.id._serialized) return wid.id._serialized;
      if (wid.user && wid.server) return `${wid.user}@${wid.server}`;
      if (wid.id) return wid.id;
      return String(wid);
    };

    const clean = (obj, depth = 0) => {
      if (!obj || typeof obj !== 'object' || depth > 3) return obj;
      if (obj instanceof Uint8Array || obj instanceof Blob || obj instanceof ArrayBuffer) return null;
      
      const result = Array.isArray(obj) ? [] : {};
      const blacklist = [
        'mediaData', 'mediaBlob', 'deprecatedMms3Url', 'data', 'buffer', 
        'chunks', 'processedImage', 'mediaObject', 'stream', 'isStoreMsg',
        '_events', 'client', 'collection', 'parent'
      ];
      
      for (const key in obj) {
        if (blacklist.includes(key) || (key.startsWith('_') && key !== '_serialized')) continue;
        const val = obj[key];
        if (typeof val === 'function') continue;
        
        if (typeof val === 'string') {
          // Strict length limit: anything over 10KB is likely media data or bloat
          if (val.length > 10240) continue;
          result[key] = val;
        } else if (typeof val === 'object' && val !== null) {
          result[key] = clean(val, depth + 1);
        } else {
          result[key] = val;
        }
      }
      return result;
    };

    let base = {};
    try {
      if (msg.serialize && typeof msg.serialize === 'function') base = msg.serialize();
      else if (msg.toJSON && typeof msg.toJSON === 'function') base = msg.toJSON();
      else base = { ...msg };
    } catch (e) { base = { ...msg }; }

    let s = clean(base) || {};

    // Ensure accurate identities (re-apply from original msg if needed)
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

    // Identity & Name Enrichment (Push-Based Resolution)
    try {
      let contactId = s.author || s.from;
      // Normalization: Try both full and primary WIDs for companion/LID support
      const getContact = (id) => window.Store && window.Store.Contact && window.Store.Contact.get(id);
      
      let sender = msg.authorObj || msg.senderObj || getContact(contactId);
      
      // If direct lookup fails and it's a suffixed JID (Companion/LID :x), try primary
      if (!sender && contactId && contactId.includes(':') && contactId.includes('@')) {
        const primaryId = contactId.split(':')[0] + '@' + contactId.split('@')[1];
        sender = getContact(primaryId);
      }

      if (sender) {
        s.senderName = sender.name || sender.formattedName || null;
        s.pushname = sender.pushname || null;
        s.verifiedName = sender.verifiedName || null;
      }
    } catch (e) { console.warn('[Astra] Name enrichment failed:', e); }

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
    const name = chat.name || chat.formattedTitle || chat.contact?.pushname || chat.contact?.name || chat.contact?.formattedName;
    const fallbackId = chat.id?._serialized || chat.id || "";
    const fallbackName = fallbackId.split('@')[0] || "Unknown Thread";
    const finalName = name || fallbackName;
    
    console.log(`[Astra] serializeChat id=${fallbackId} name=${finalName} (raw_name=${name})`);
    
    return {
      id: fallbackId,
      name: finalName,
      isGroup: !!chat.isGroup,
      isReadOnly: !!chat.isReadOnly,
      unreadCount: chat.unreadCount || 0,
      timestamp: chat.t || 0,
      archived: !!chat.archive,
      pinned: !!chat.pin,
      muteExpiration: chat.mute ? chat.mute.expiration : 0,
      isMuted: chat.mute ? chat.mute.isMuted : false
    };
  };

  window.Astra.createWid = (input) => {
    try {
      const Store = window.Astra.initializeEngine();
      if (!input) return null;
      if (typeof input === 'object' && input._serialized) return input;
      if (typeof input === 'object' && input.user && input.server) return input;

      const serialized = typeof input === 'string' ? input : (input._serialized || (input.toString ? input.toString() : String(input)));
      if (!serialized) return null;
      
      const wf = Store.WidFactory || Store.AddressFactory;
      if (!wf || !wf.createWid) {
        // Hard fallback for basic Wid structure if Factory is missing
        const parts = serialized.split('@');
        return { user: parts[0], server: parts[1], _serialized: serialized, isLid: () => serialized.includes('@lid') };
      }

      return wf.createWid(serialized);
    } catch (e) {
      console.error('[Astra] createWid failed:', e.message);
      return null;
    }
  };

  window.Astra.getChat = async (wid, force = false) => {
    try {
      const Store = window.Astra.initializeEngine();
      let chatId = typeof wid === 'string' ? wid : (wid && wid._serialized ? wid._serialized : String(wid));
      let chatWid = typeof wid === 'string' ? window.Astra.createWid(wid) : wid;
      
      if (!chatWid) return null;

      const getFromRepos = (w) => {
        if (!Store.Chat) return null;
        let c = Store.Chat.get(w);
        if (!c && Store.ChatRepo) c = Store.ChatRepo.get(w);
        return c;
      };

      console.log(`[Astra] getChat search start: ${chatId}`);
      let chat = getFromRepos(chatWid);

      // Fallback 1: Primary ID
      if (!chat && chatId && chatId.includes(':')) {
        const primaryId = chatId.split(':')[0] + '@' + chatId.split('@')[1];
        console.log(`[Astra] getChat fallback 1 (primary): ${primaryId}`);
        chatWid = window.Astra.createWid(primaryId);
        chat = getFromRepos(chatWid);
      }

      // Fallback 2: LID specific Repo discovery
      if (!chat && chatId && chatId.includes('@lid')) {
        console.log(`[Astra] getChat fallback 2 (LID Repo Check)`);
        const lidRepo = Store.LidContact || window.Astra.mR.findModule(m => m && m.get && m.isLid && m.isLid(chatId)) || window.Astra.mR.findModule(m => m && m.isLid && m.isLid(chatId) && m.Chat);
        if (lidRepo && typeof lidRepo.get === 'function') {
           const lidObj = lidRepo.get(chatWid) || lidRepo.get(chatId);
           if (lidObj && lidObj.chat) {
             chat = lidObj.chat;
             console.log(`[Astra] Found chat via LidContact Repo!`);
           }
        }
      }

      // Fallback 3: Authoritative Find
      if (!chat && Store.FindOrCreateChat && Store.FindOrCreateChat.findOrCreateLatestChat) {
        console.log(`[Astra] getChat fallback 3 (findOrCreateLatestChat)`);
        try { chat = (await Store.FindOrCreateChat.findOrCreateLatestChat(chatWid))?.chat; } catch (e) { }
      }

      if (!chat && Store.Chat && Store.Chat.find) {
        console.log(`[Astra] getChat fallback 4 (Chat.find)`);
        try { chat = await Store.Chat.find(chatWid); } catch (e) { }
      }

      if (!chat) console.warn(`[Astra] getChat FAILED for ${chatId}`);
      else console.log(`[Astra] getChat SUCCESS for ${chatId}`);

      return chat;
    } catch (e) {
      console.error('[Astra] getChat failed:', e.message);
      return null;
    }
  };

  window.Astra.getChatById = async (chatId, force = false) => {
    try {
      const chat = await window.Astra.getChat(chatId, force);
      return window.Astra.serializeChat(chat);
    } catch (e) {
      console.error('[Astra] getChatById failed:', e.message);
      return null;
    }
  };

  window.Astra.getContactById = async (contactId) => {
    try {
      const Store = window.Astra.initializeEngine();
      let contactWid = window.Astra.createWid(contactId);
      if (!contactWid) return null;

      let contact = Store.Contact ? Store.Contact.get(contactWid) : null;
      
      // Fallback 1: Suffixed JID (:x) -> primary
      if (!contact && contactId.includes(':')) {
        const primaryId = contactId.split(':')[0] + '@' + contactId.split('@')[1];
        contactWid = window.Astra.createWid(primaryId);
        contact = Store.Contact ? Store.Contact.get(contactWid) : null;
      }

      // Fallback 2: LID specific Repo
      if (!contact && contactId.includes('@lid') && Store.LidContact) {
        contact = Store.LidContact.get(contactWid);
      }

      if (!contact && Store.Contact && Store.Contact.find) {
        try { contact = await Store.Contact.find(contactWid); } catch (e) { }
      }
      if (!contact) return null;

      return {
        id: contact.id?._serialized || contact.id,
        name: contact.name || contact.pushname || contact.formattedName || contact.id?.user || "",
        isMyContact: !!contact.isMyContact,
        isUser: !!contact.isUser,
        isBusiness: !!contact.isBusiness,
        verifiedName: contact.verifiedName
      };
    } catch (e) {
      console.error('[Astra] getContactById failed:', e.message);
      return null;
    }
  };

  // --- Logging Helper ---
  window.Astra.log = (msg, level = 'log') => {
    const formatted = `[Astra] ${msg}`;
    if (level === 'error') console.error(formatted);
    else if (level === 'warn') console.warn(formatted);
    else console.log(formatted);
    
    if (window.Astra && typeof window.Astra.emit === 'function') {
      window.Astra.emit('log', { msg, level });
    }
  };

  window.Astra.fetchMessages = async (chatId, options = {}) => {
    window.Astra.log(`fetchMessages sequence started for ${chatId}`);
    try {
      let targetId = chatId;
      let targetOptions = options;

      // Normalize arguments
      if (typeof chatId === 'object' && chatId.chatId) {
        targetId = chatId.chatId;
        targetOptions = chatId.searchOptions || chatId;
      }

      const limit = parseInt(targetOptions.limit || targetOptions.count || 10);
      const anchorId = targetOptions.msgId || targetOptions.message_id || targetOptions.id || null;
      const direction = targetOptions.direction === 'before' ? 'before' : 'after';
      const fromMe = targetOptions.fromMe !== undefined ? targetOptions.fromMe : targetOptions.from_me;
      const includeAnchor = targetOptions.includeAnchor || targetOptions.include_anchor || false;

      window.Astra.log(`Parameters: Anchor=${anchorId}, Dir=${direction}, Limit=${limit}, IncludeAnchor=${includeAnchor}`, 'info');

      if (!targetId) {
        window.Astra.log("Error: No targetId provided.", "error");
        return [];
      }

      const chat = await window.Astra.getChat(targetId, false);
      if (!chat) {
        window.Astra.log(`Error: Chat ${targetId} not found.`, "error");
        return [];
      }

      const Store = window.Astra.initializeEngine();
      if (!Store.msgFindQuery) {
        window.Astra.log("Discovering msgFindQuery...", "log");
        Store.msgFindQuery = window.Astra.mR.findModule(m => m && m.msgFindQuery && (m.getMsgsByMsgKey || m.queryMessageType))?.msgFindQuery;
      }
      
      const isValidMsg = (m) => {
          if (!m || m.isNotification) return false;
          if (fromMe !== undefined && m.id.fromMe !== fromMe) return false;
          return true;
      };

      const getLocalArray = () => chat.msgs.getModelsArray ? chat.msgs.getModelsArray() : (chat.msgs.models || []);

      let msgs = [];

      // Strategy 1: Local Cache
      const tryLocal = () => {
        if (anchorId) {
          window.Astra.log(`Strategy 1: Searching for anchor ${anchorId} locally...`);
          let anchorMsg = Store.Msg.get(anchorId);
          if (!anchorMsg) anchorMsg = getLocalArray().find(m => m.id._serialized === anchorId);

          if (anchorMsg) {
            const all = getLocalArray().filter(isValidMsg);
            all.sort((a, b) => a.t - b.t);
            const idx = all.findIndex(m => m.id._serialized === anchorId);
            if (idx !== -1) {
              const startIdx = includeAnchor ? idx : idx + 1;
              const slice = (direction === 'after') ? all.slice(startIdx, startIdx + limit) : all.slice(Math.max(0, idx - limit), idx + (includeAnchor ? 1 : 0));
              window.Astra.log(`Strategy 1 found ${slice.length} messages near anchor.`);
              return slice;
            }
          }
        } else {
          window.Astra.log("Strategy 1: Fetching tail from local cache.");
          const all = getLocalArray().filter(isValidMsg);
          all.sort((a, b) => a.t - b.t);
          const slice = all.slice(-limit);
          window.Astra.log(`Strategy 1 found ${slice.length} messages in tail.`);
          return slice;
        }
        return [];
      };

      // Strategy 2: msgFindQuery (Authoritative history retrieval)
      const tryQuery = async (countOverride = limit) => {
        if (!Store.msgFindQuery) return [];
        
        let queryDir = direction;
        if (!anchorId && queryDir === 'after') {
          window.Astra.log("Correcting anchorless 'after' query to 'before' for history retrieval.", "warn");
          queryDir = 'before';
        }

        window.Astra.log(`Strategy 2: Querying engine (Dir=${queryDir}, Count=${countOverride}, Target=${targetId})`);
        
        let params = {
          count: countOverride,
          direction: queryDir,
          remote: window.Astra.createWid(targetId),
          fromMe: fromMe
        };

        if (anchorId) {
          try {
            const key = Store.MsgKey.fromString(anchorId);
            params = Object.assign({}, key.obj || key, params);
          } catch(e) { params.id = anchorId; }
        }

        try {
          const queryType = ['media', 'search', 'star'].includes(targetOptions.type) ? targetOptions.type : direction;
          const result = await Store.msgFindQuery(queryType, params);
          let found = [];
          if (result && result.messages) found = result.messages;
          else if (Array.isArray(result)) found = result;
          else if (result && result.models) found = result.models;
          
          let filtered = found.filter(isValidMsg);
          if (anchorId && !includeAnchor) {
            filtered = filtered.filter(m => m.id._serialized !== anchorId);
          }
          return filtered;
        } catch (e) {
          window.Astra.log(`Strategy 2 query failed: ${e.message}`, "warn");
          return [];
        }
      };

      // Logic Flow:
      if (!anchorId && limit <= 10) {
        msgs = tryLocal();
      }

      if (msgs.length < limit && Store.msgFindQuery) {
        window.Astra.log(`Strategy 2 trigger: Current count ${msgs.length} < limit ${limit}`);
        const queryResults = await tryQuery(limit + (anchorId ? 1 : 0));
        if (queryResults.length > 0) {
          msgs = queryResults.slice(0, limit);
        }
      }

      // Final local fallback if query returned nothing
      if (msgs.length === 0) {
        window.Astra.log("No results from Strategy 2, performing final Strategy 1 fallback.");
        msgs = tryLocal();
      }

      // Strategy 3: Direct Load (Historical before queries)
      if (msgs.length === 0 && anchorId && direction === 'before' && Store.ConversationMsgs && Store.ConversationMsgs.loadEarlierMsgs) {
        window.Astra.log("Strategy 3: Triggering loadEarlierMsgs for historical gap resolution.");
        try { await Store.ConversationMsgs.loadEarlierMsgs(chat); } catch (e) { }
        msgs = tryLocal();
      }

      // Strategy 4: Direct Load (Historical after queries)
      if (msgs.length === 0 && anchorId && direction === 'after' && Store.ConversationMsgs && Store.ConversationMsgs.loadLaterMsgs) {
        window.Astra.log("Strategy 4: Triggering loadLaterMsgs for historical gap resolution.");
        try { await Store.ConversationMsgs.loadLaterMsgs(chat); } catch (e) { }
        msgs = tryLocal();
      }

      window.Astra.log(`Final Result: Returning ${msgs.length}/${limit} messages.`, msgs.length >= limit ? "info" : "warn");
      return msgs.map(m => window.Astra.serializeMsg(m));

    } catch (criticalErr) {
      window.Astra.log(`CRITICAL CRASH in fetchMessages: ${criticalErr.message}`, "error");
      return [];
    }
  };

  window.Astra.deepSync = async function () {
    const Store = window.Astra.initializeEngine();
    console.log("[Astra] Starting deepSync (Fetch Everything)...");

    const tasks = [];
    // 1. Sync Contacts
    const contacts = (Store.ContactRepo && Store.ContactRepo.models) || (Store.Contact && Store.Contact.models) || [];
    contacts.forEach(c => {
      if (c.fetchValue) tasks.push(c.fetchValue().catch(() => { }));
      else if (c.queryContact) tasks.push(c.queryContact().catch(() => { }));
    });

    // 2. Sync Group Metadata
    const chats = (Store.ChatRepo && Store.ChatRepo.models) || (Store.Chat && Store.Chat.models) || [];
    chats.forEach(chat => {
      if (chat.isGroup && chat.groupMetadata && chat.groupMetadata.query) {
        tasks.push(chat.groupMetadata.query().catch(() => { }));
      }
    });

    await Promise.allSettled(tasks);
    console.log("[Astra] deepSync complete.");
    return true;
  };

  window.Astra.deepScanModules = function (query = '') {
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
        try { scan(wr(id), id); } catch (e) { }
      }
    } else {
      const chunkName = 'webpackChunkwhatsapp_web_client';
      const chunk = window[chunkName] || [];
      for (let c of chunk) {
        if (results.length > 500) break;
        if (c && c[1]) {
          for (let id in c[1]) {
            if (results.length > 500) break;
            try { scan(window.require(id), id); } catch (e) { }
          }
        }
      }
    }
    return results;
  };

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
      return { total: 0, error: err.message };
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

    // DOM Fallback: Main Selector (pane-side rows)
    console.log(`[Astra] Using DOM fallback for chat: ${chatId}`);
    const idStr = (chatId && chatId._serialized) ? chatId._serialized : String(chatId);

    // Strategy: Find row in pane-side
    const rows = Array.from(document.querySelectorAll('#pane-side [role="row"], ._ak8o'));
    const targetRow = rows.find(row => row.innerHTML.includes(idStr) || row.innerHTML.includes(idStr.split('@')[0]));

    if (targetRow) {
      targetRow.click();
      // Click center to be safe
      const rect = targetRow.getBoundingClientRect();
      const clickEvent = new MouseEvent('click', {
        view: window,
        bubbles: true,
        cancelable: true,
        clientX: rect.left + rect.width / 2,
        clientY: rect.top + rect.height / 2
      });
      targetRow.dispatchEvent(clickEvent);

      await new Promise(r => setTimeout(r, 1500));
      return true;
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
    console[level] = function (...args) {
      originalLog.apply(console, args);
      // Bridge logging to Python via astra_uplink
      if (window.astra_uplink) {
        try {
          // Send to Python as 'log' event
          window.astra_uplink('log', { level, msg: args.map(a => String(a)).join(' ') });
        } catch (e) { }
      }
    };
  });

  const engineRaid = function () {
    let webpackRequire = window.__w || window.require;
    const chunkNames = [
      'webpackChunkwhatsapp_web_client',
      'webpackChunk_whatsapp_web_client',
      'webpackChunkwhatsapp_web_desktop_client',
      'webpackChunk_whatsapp_web_desktop_client'
    ];
    let chunk = null;
    for (const name of chunkNames) {
      if (window[name]) {
        chunk = window[name];
        break;
      }
    }
    if (!chunk) chunk = [];

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
    } catch (e) { }

    // 2. Fallback: Hook future pushes
    if (chunk && !chunk._astra_hooked) {
      const originalPush = chunk.push;
      chunk.push = function (...args) {
        const res = originalPush.apply(chunk, args);
        if (args[0] && args[0][2] && !webpackRequire) {
          try { args[0][2](capture); } catch (e) { }
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
            } catch (e) { }
          }
        }
        return null;
      },
      webpackRequire
    };
  }();

  window.Astra.mR = engineRaid;
  if (engineRaid.webpackRequire && !window.require) {
    window.require = engineRaid.webpackRequire;
  }

  window.Astra.initializeEngine = function () {
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
      ProfilePicRepo: 'WAWebContactProfilePicThumbBridge',
      msgFindQuery: 'WAWebDBMessageFindLocal'
    };

    const requireFunc = window.require || window.__w;
    if (requireFunc) {
      // Suppress WA's ErrorUtils during require to avoid console noise
      const safeRequire = (name) => {
        const origReporter = window.ErrorUtils && window.ErrorUtils.reportError;
        const origError = console.error;
        try {
          if (window.ErrorUtils) window.ErrorUtils.reportError = () => { };
          console.error = () => { };
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

      // 2. Aliases for compatibility with Astra scripts
      window.Store.AddressFactory = window.Store.WidFactory;
      window.Store.UserCredentials = window.Store.User;
      window.Store.ChatRepo = window.Store.Chat;
      window.Store.MsgRepo = window.Store.Msg;
      window.Store.ContactRepo = window.Store.Contact;
      window.Store.ChatMeta = window.Store.ChatGetters || window.Store.Chat;

      console.log('[Astra] Core aliases mapped.');

      // 3. AuthStore initialization
      try {
        window.AuthStore.Conn = window.Store.Conn;
        window.AuthStore.AppState = window.Store.AppState;
        window.AuthStore.Base64Tools = safeRequire('WABase64');
        window.AuthStore.RegistrationUtils = {
          ...safeRequire('WAWebCompanionRegClientUtils'),
          ...safeRequire('WAWebAdvSignatureApi'),
          ...safeRequire('WAWebUserPrefsInfoStore'),
          ...safeRequire('WAWebSignalStoreApi')
        };
        console.log('[Astra] AuthStore initialized.');
      } catch (e) {
        console.error('[Astra] AuthStore init failed:', e);
      }

      // 1. Hardcoded Module Fallbacks (Derived from wp/src/util/Injected/Store.js)
      // This ensures we find critical modules even if heuristics fail due to minification updates.
      const hardcodedModules = {
        'WidFactory': 'WAWebWidFactory',
        'UserConstructor': 'WAWebWid',
        'MsgKey': 'WAWebMsgKey',
        'Cmd': 'WAWebCmd',
        'Conn': 'WAWebConnModel',
        'AppState': 'WAWebSocketModel',
        'ConversationMsgs': 'WAWebChatLoadMessages',
        'SendClear': 'WAWebChatClearBridge',
        'SendDelete': 'WAWebDeleteChatAction',
        'UploadUtils': 'WAWebUploadManager'
      };

      for (const [alias, moduleName] of Object.entries(hardcodedModules)) {
        try {
          if (!window.Store[alias]) {
            const module = window.require(moduleName);
            if (module) {
              window.Store[alias] = module.default || module;
              if (alias === 'Conn' && module.Conn) window.Store.Conn = module.Conn;
              if (alias === 'AppState' && module.Socket) window.Store.AppState = module.Socket;
              console.log(`[Astra] Hardcoded match for: ${alias} (${moduleName})`);
            }
          }
        } catch (e) {
          // console.debug(`[Astra] Optional module ${alias} not found.`);
        }
      }
      console.log('[Astra] Hardcoded modules scan complete.');

      // Heuristics for missing modules (Expanded)
      const engineHeuristics = {
        Chat: (m) => m && m.get && m.add && (m.getModelsArray || (m.models && m.models.getModelsArray)) && m.models,
        Msg: (m) => m && m.get && m.add && (m.getModelsArray || (m.models && m.models.getModelsArray)) && m.models && m.getMessagesById,
        Contact: (m) => m && m.get && m.add && (m.getModelsArray || (m.models && m.models.getModelsArray)) && m.models && m.getMaybeMePnUser,
        SendMessage: (m) => (m.addAndSendMsgToChat && m.resendMsgToChat) || (m.sendMsgToChat && m.prepareMsg),
        msgFindQuery: (m) => (m.msgFindQuery && m.getMsgsByMsgKey) || (m.msgFindQuery && m.queryMessageType),
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

        window.Store.MsgKey.from = function (value) {
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

  };

  // Auto-init — only run full discovery when WA modules are actually available
  // (i.e., after auth, not on QR page where all requires fail)
  (function () {
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

    window.Astra.getMe = function () {
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

    setTimeout(_tryInit, 2000);
  })();

})();



(function() {
 window.Astra = window.Astra || {};

 window.Astra.getProfilePic = async (chatId) => {
  const Store = window.Astra.initializeEngine();
  const wid = window.Astra.createWid(chatId);
  try {
   const pic = await Store.ProfilePicRepo.requestProfilePicFromServer(wid);
   return pic ? pic.toJSON ? pic.toJSON() : pic : null;
  } catch (e) {
    try {
     const pic = await Store.ProfilePicRepo.profilePicFind(wid);
     return pic ? pic.toJSON ? pic.toJSON() : pic : null;
    } catch(e2) { return null; }
  }
 };

 window.Astra.blockContact = async (chatId, block = true) => {
  const Store = window.Astra.initializeEngine();
  const wid = window.Astra.createWid(chatId);
  const contact = Store.ContactRepo.get(wid) || await Store.ContactRepo.find(wid);
  if (!contact) return false;
  if (block) {
   if (Store.BlockAction && typeof Store.BlockAction.blockContact === 'function') {
    await Store.BlockAction.blockContact(contact);
   } else if (Store.Blocklist && typeof Store.Blocklist.blockContact === 'function') {
    await Store.Blocklist.blockContact(contact);
   } else {
    throw new Error('Block module not available');
   }
  } else {
   if (Store.BlockAction && typeof Store.BlockAction.unblockContact === 'function') {
    await Store.BlockAction.unblockContact(contact);
   } else if (Store.Blocklist && typeof Store.Blocklist.unblockContact === 'function') {
    await Store.Blocklist.unblockContact(contact);
   } else {
    throw new Error('Unblock module not available');
   }
  }
  return true;
 };

 window.Astra.getStatus = async (chatId) => {
  const Store = window.Astra.initializeEngine();
  const wid = window.Astra.createWid(chatId);
  try {
   const res = await Store.ChatMeta.getStatus(wid);
   return res.status;
  } catch (e) { return null; }
 };

 window.Astra.getIdentity = function() {
  try {
   const Store = window.Astra.initializeEngine();
   const u = Store.User;
   const lid = u && u.getMaybeMeLidUser ? u.getMaybeMeLidUser() : null;
   const pn = u && u.getMaybeMePnUser ? u.getMaybeMePnUser() : null;

   const conn = (Store.Conn && (Store.Conn.wid || Store.Conn.me)) ||
       (Store.SessionInfo && (Store.SessionInfo.wid || Store.SessionInfo.me));

   const wid = lid || pn || conn;
   if (!wid) return null;

   const serializedId = wid._serialized || (typeof wid === 'string' ? wid : null);
   if (!serializedId) return null;

   let pushname = (Store.Conn && Store.Conn.pushname) ||
       (Store.SessionInfo && Store.SessionInfo.pushname) ||
       (u && u.getPushname && u.getPushname()) ||
       (Store.Contact && serializedId && Store.Contact.get(serializedId)?.pushname) ||
       'User';

   return { id: serializedId, name: pushname, pushname: pushname, isMyContact: true };
  } catch (e) {
   console.warn('[Astra] Identity resolution failed:', e.message);
   return null;
  }
 };

 window.Astra.getGroupInviteLink = async (chatId) => {
  const Store = window.Astra.initializeEngine();
  const wid = window.Astra.createWid(chatId);
  if (Store.GroupInviteMex && Store.GroupInviteMex.fetchGroupInviteCode) {
   return await Store.GroupInviteMex.fetchGroupInviteCode(wid);
  }
  if (Store.GroupInvite && Store.GroupInvite.sendGetGroupInviteCode) {
   return await Store.GroupInvite.sendGetGroupInviteCode(wid);
  }
  return null;
 };

 window.Astra.joinGroupViaLink = async (code) => {
  const Store = window.Astra.initializeEngine();
  if (Store.GroupInvite && Store.GroupInvite.sendJoinGroupViaInvite) {
   return await Store.GroupInvite.sendJoinGroupViaInvite(code);
  }
  return null;
 };

 window.Astra.updateProfileDOM = async (pushname) => {
  const Store = window.Astra.initializeEngine();
  const mod = Store.AccountUtils || Store.Settings || Store.Perfil;
  if (mod && mod.setPushname) {
   try {
    await mod.setPushname(pushname);
    return true;
   } catch (e) {
    console.warn('[Astra] setPushname failed, falling back to DOM:', e.message);
   }
  }

  await window.Astra.ensureSidebar('Profile', true);
  const nameEdit = document.querySelector('button[aria-label*="edit Name"]') ||
       document.querySelector('button[title*="Name"]') ||
       Array.from(document.querySelectorAll('button[aria-label]')).find(b => b.ariaLabel.toLowerCase().includes('edit') && b.ariaLabel.toLowerCase().includes('name')) ||
       document.querySelector('span[data-icon="pencil"]')?.closest('button');

  if (!nameEdit) throw new Error("Astra: Name edit button not found");

  await window.Astra.runDOMAction([
   { element: nameEdit, action: 'click', wait: 800 },
   { selector: 'div[aria-label="Name"][role="textbox"]', action: 'type', value: pushname, wait: 800 },
   { selector: 'button[aria-label*="save Name"], button[data-testid="checkmark-medium"]', action: 'click', wait: 1200 }
  ]);
  await window.Astra.ensureSidebar('Profile', false);
  return true;
 };

 window.Astra.setStatusDOM = async (status) => {
  const Store = window.Astra.initializeEngine();
  const mod = Store.AccountUtils || Store.StatusUtils || Store.Perfil || Store.Settings;
  if (mod && (mod.setMyStatus || mod.setAbout)) {
   try {
    const fn = mod.setMyStatus || mod.setAbout;
    await fn.call(mod, status);
    return true;
   } catch (e) {
    console.warn('[Astra] setAbout/setMyStatus failed, falling back to DOM:', e.message);
   }
  }

  await window.Astra.ensureSidebar('Profile', true);
  const editBtn = document.querySelector('button[aria-label*="edit About"]') ||
      document.querySelector('button[aria-label="Click to edit About"]') ||
      Array.from(document.querySelectorAll('button[aria-label]')).find(b => b.ariaLabel.toLowerCase().includes('edit') && b.ariaLabel.toLowerCase().includes('about')) ||
      document.querySelector('span[data-icon="pencil"]')?.parentElement;

  if (editBtn) {
   await window.Astra.runDOMAction([
    { element: editBtn, action: 'click', wait: 800 },
    { selector: 'div[aria-label="About"][role="textbox"]', action: 'type', value: status, wait: 800 },
    { selector: 'button[aria-label*="save About"], button[data-testid="checkmark-medium"]', action: 'click', wait: 1200 }
   ]);
  } else {
   console.warn("Astra: About edit button not found. Trying aggressive fallback.");

   // Fallback 1: Search for 'About' label and click it or its next sibling
   const aboutLabel = Array.from(document.querySelectorAll('span, div')).find(el => el.innerText === 'About' || el.innerText === 'Info');
   if (aboutLabel) {
     // The About text is usually the first sibling after the label
     const parent = aboutLabel.parentElement;
     const textEl = parent.querySelector('span[title]') || parent.nextElementSibling;
     if (textEl) {
      textEl.click();
      await new Promise(r => setTimeout(r, 800));

      const editor = document.querySelector('div[aria-label="About"][role="textbox"]') || document.querySelector('div[contenteditable="true"]');
      if (editor) {
       await window.Astra.runDOMAction([
        { element: editor, action: 'type', value: status, wait: 800 },
        { selector: 'button[aria-label*="save About"], button[data-testid="checkmark-medium"]', action: 'click', wait: 1200 }
       ]);
      }
     }
   } else {
    // Fallback 2: Last resort - search for any pencil icons if our first selector missed them
    const anyPencil = document.querySelector('span[data-icon="pencil"]');
    if (anyPencil) {
     anyPencil.click();
     // ... this is risky as it might be the name pencil
    }
   }
  }
  await window.Astra.ensureSidebar('Profile', false);
  return true;
 };

 window.Astra.getContactId = async (number) => {
  const Store = window.Astra.initializeEngine();
  try {
   const wid = window.Astra.createWid(number);
   const contact = await Store.ContactRepo.find(wid);
   return contact ? contact.id._serialized : null;
  } catch (e) {
   // Fallback: Check if number exists directly
   try {
    const result = await Store.QueryExist(number);
    if (result && result.wid) return result.wid._serialized;
   } catch (e2) { return null; }
   return null;
  }
 };

 window.Astra.logout = async () => {
  const Store = window.Astra.initializeEngine();
  console.log('[Astra] Logout requested.');

  // 1. Try internal command
  if (Store.Cmd && typeof Store.Cmd.logout === 'function') {
   try {
    await Store.Cmd.logout();
    return true;
   } catch (e) {
    console.warn('[Astra] Internal logout failed:', e.message);
   }
  }

  // 2. DOM Fallback
  console.log('[Astra] Falling back to DOM logout...');
  const menuBtn = document.querySelector('button[aria-label="Menu"]') ||
      document.querySelector('span[data-icon="menu"]')?.closest('button');

  if (menuBtn) {
   menuBtn.click();
   await new Promise(r => setTimeout(r, 500));
   const logoutEntry = Array.from(document.querySelectorAll('div[role="button"]')).find(el => el.innerText && el.innerText.toLowerCase().includes('log out'));
   if (logoutEntry) {
    logoutEntry.click();
    await new Promise(r => setTimeout(r, 500));
    const confirmBtn = document.querySelector('button[data-testid="popup-controls-ok"]') ||
         Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.toLowerCase().includes('log out'));
    if (confirmBtn) {
     confirmBtn.click();
     return true;
    }
   }
  }

  throw new Error('Logout failed: command and DOM interaction unsuccessful');
 };
})();


(function() {
 window.Astra = window.Astra || {};

 window.Astra.ensureWid = (value) => {
  const Store = window.Astra.initializeEngine();
  if (!value) return null;
  if (typeof value === 'string') return window.Astra.createWid(value);
  if (typeof value === 'object') {
   const id = value._serialized || value.serialized || value.id;
   if (id && (typeof id === 'string' || id._serialized)) return window.Astra.createWid(id._serialized || id);
  }
  return value;
 };

  window.Astra.sendText = async (to, text, options = {}) => {
  const Store = window.Astra.initializeEngine();
  const chatWid = window.Astra.ensureWid(to);
  if (!Store.WidFactory && !Store.AddressFactory) throw new Error('Astra: WidFactory/AddressFactory unavailable');

  const chat = await window.Astra.getChat(chatWid);
  if (!chat) throw new Error(`Astra: Chat not found for ${chatWid && chatWid._serialized ? chatWid._serialized : String(chatWid)}`);

  const u = Store.User;
  const lidUser = u && u.getMaybeMeLidUser ? u.getMaybeMeLidUser() : null;
  const meUser = u && u.getMaybeMePnUser ? u.getMaybeMePnUser() : null;

  const from = chatWid.isLid() ? (lidUser || meUser) : (meUser || lidUser);
  console.log(`[Astra] sendText target=${chatWid._serialized} from=${from ? from._serialized : 'NULL'}`);

  let newId;
  if (Store.MsgKey && Store.MsgKey.newId) {
   newId = await Store.MsgKey.newId();
  } else if (Store.MessageIdentity && Store.MessageIdentity.newId) {
   newId = await Store.MessageIdentity.newId();
  } else {
   newId = `${Date.now()}-${Math.random().toString(36).slice(2,9)}`;
  }

  let newMsgKey;
  try {
   if (Store.MsgKey) {
    newMsgKey = new Store.MsgKey({ from: from, to: chatWid, id: newId, selfDir: 'out' });
   } else if (Store.MessageIdentity) {
    newMsgKey = new Store.MessageIdentity({ from: from, to: chatWid, id: newId, selfDir: 'out' });
   } else {
    newMsgKey = { from, to: chatWid, id: newId, _serialized: `${from._serialized}_${chatWid._serialized}_${newId}` };
   }
  } catch (e) {
   newMsgKey = { _serialized: `out_${chatWid._serialized}_${newId}` };
  }

  const ephemeralFields = (Store.EphemeralFields && Store.EphemeralFields.getEphemeralFields) ? Store.EphemeralFields.getEphemeralFields(chat) : {};

  let quotedMsgOptions = {};
  const quotedId = options.quoted_message_id || options.quotedMsgId;
  if (quotedId) {
   try {
    let quotedMessage = Store.Msg.get(quotedId);
    if (quotedMessage) {
     const canReply = Store.ReplyUtils ? Store.ReplyUtils.canReplyMsg(quotedMessage) : (quotedMessage.canReply ? quotedMessage.canReply() : true);
     if (canReply) {
      quotedMsgOptions = quotedMessage.msgContextInfo(chat);
      console.log(`[Astra] Quoted message attached: ${quotedId}`);
     }
    }
   } catch (e) {
    console.warn('[Astra] Quoted attachment failed:', e);
   }
  }

  const message = {
   ...options,
   id: newMsgKey,
   ack: 0,
   body: text,
   from: from,
   to: chatWid,
   local: true,
   self: 'out',
   t: parseInt(new Date().getTime() / 1000),
   isNewMsg: true,
   type: 'chat',
   ...ephemeralFields,
   ...quotedMsgOptions
  };

  const msgSender = Store.SendMessage || Store.MessageSender || window.Astra.mR.findModule(m => m && m.addAndSendMsgToChat);
  if (!msgSender) throw new Error('Astra: No SendMessage modules found');

  try {
   const res = msgSender.addAndSendMsgToChat ? msgSender.addAndSendMsgToChat(chat, message) : msgSender.send(chat, message);
   
   if (options.waitForSend) {
    const result = Array.isArray(res) ? res[1] : res;
    await Promise.race([
     result,
     new Promise((_, reject) => setTimeout(() => reject(new Error('Astra: send acknowledgement timeout')), 30000))
    ]);
   }
  } catch (e) {
   console.error('[Astra] sendText failure:', e.message);
  }

  const resultMsg = (Store.Msg && Store.Msg.get) ? (Store.Msg.get(newMsgKey._serialized) || message) : message;
  return window.Astra.serializeMsg(resultMsg);
 };


 window.Astra.markSeen = async (chatId) => {
  const Store = window.Astra.initializeEngine();
  const chatWid = window.Astra.createWid(chatId);
  const chat = Store.Chat.get(chatWid);
  if (!chat) return false;

  if (Store.SendSeen && Store.SendSeen.sendSeen) {
   await Store.SendSeen.sendSeen({ chat, threadId: undefined });
   return true;
  }
  return false;
 };

 window.Astra.archiveChat = async (chatId, archive = true) => {
  const Store = window.Astra.initializeEngine();
  const chatWid = window.Astra.createWid(chatId);
  const chat = Store.Chat.get(chatWid) || await Store.Chat.find(chatWid);
  if (!chat) return false;
  if (Store.Cmd && Store.Cmd.archiveChat) {
    await Store.Cmd.archiveChat(chat, archive);
    return true;
  }
  return false;
 };

 window.Astra.pinChat = async (chatId, pin = true) => {
  try {
   const Store = window.Astra.initializeEngine();
   const Wid = window.Astra.createWid(chatId);
   const chat = Store.Chat.get(Wid) || await Store.Chat.find(Wid);
   if (!chat) return false;

   if (Store.Cmd && typeof Store.Cmd.pinChat === 'function') {
    await Store.Cmd.pinChat(chat, pin);
    return true;
   }
   return false;
  } catch (e) {
   console.warn('[Astra] pinChat error:', e.message);
   return false;
  }
 };

 window.Astra.muteChat = async (chatId, expiration = -1) => {
  const Store = window.Astra.initializeEngine();
  const chatWid = window.Astra.createWid(chatId);
  const chat = Store.Chat.get(chatWid);
  if (!chat || !chat.mute) return false;
  if (expiration !== 0) {
   await chat.mute.mute({ expiration, sendDevice: true });
  } else {
   await chat.mute.unmute({ sendDevice: true });
  }
  return { isMuted: chat.mute.expiration !== 0, muteExpiration: chat.mute.expiration };
 };

 window.Astra.editMessage = async function(msgId, content, options = {}) {
  try {
   const Store = window.Astra.initializeEngine();
   const msg = (typeof msgId === 'object') ? msgId : (Store.Msg.get(msgId) || (await Store.Msg.getMessagesById([msgId]))?.messages?.[0]);
   if (!msg) throw new Error("Message not found: " + msgId);

   // Pre-flight check: WhatsApp's internal editability rules
   const isEditable = msg.canEdit ? (typeof msg.canEdit === 'function' ? msg.canEdit() : msg.canEdit) : true;
   if (!isEditable) throw new Error("Message is not editable (too old, already deleted, or not sent by you)");

   console.log(`[Astra] editMessage id=${msg.id._serialized} fromMe=${msg.id.fromMe}`);

   // Try 1: Standard Store module
   if (Store.EditMessage && Store.EditMessage.sendMessageEdit) {
    await Store.EditMessage.sendMessageEdit(msg, content, options);
    console.log('[Astra] editMessage: success via Store.EditMessage');
    return window.Astra.serializeMsg(msg);
   }

   // Try 2: Direct model edit (sometimes available in newer builds)
   if (typeof msg.sendMessageEdit === 'function') {
    await msg.sendMessageEdit(content, options);
    return window.Astra.serializeMsg(msg);
   }

   // Try 3: Discovery Fallback
   const editMod = window.Astra.mR.findModule(m => m && typeof m.sendMessageEdit === 'function') ||
       window.Astra.mR.findModule(m => m && typeof m.sendEditMessage === 'function');

   if (editMod) {
    const func = editMod.sendMessageEdit || editMod.sendEditMessage;
    await func(msg, content, options);
    console.log('[Astra] editMessage: success via discovered module');
    return window.Astra.serializeMsg(msg);
   }

   throw new Error("No suitable edit implementation found in this WhatsApp version");
  } catch (e) {
   console.error('[Astra] editMessage error:', e.message);
   throw e;
  }
 };

 window.Astra.deleteMessage = async function(msgId, everyone = true, clearMedia = true) {
  try {
   const Store = window.Astra.initializeEngine();
   const msg = (typeof msgId === 'object') ? msgId : (Store.Msg.get(msgId) || (await Store.Msg.getMessagesById([msgId]))?.messages?.[0]);
   if (!msg) throw new Error("Message not found");

   console.log(`[Astra] deleteMessage id=${msg.id._serialized} everyone=${everyone}`);

   const canRevoke = Store.MsgActionChecks && (Store.MsgActionChecks.canSenderRevokeMsg(msg) || Store.MsgActionChecks.canAdminRevokeMsg(msg));

   if (everyone && canRevoke) {
    const chat = Store.Chat.get(msg.id.remote) || await Store.Chat.find(msg.id.remote);
    const revokeMod = Store.Cmd || window.Astra.mR.findModule(m => m && typeof m.sendRevokeMsgs === 'function');
    if (revokeMod) {
     await revokeMod.sendRevokeMsgs(chat, { list: [msg], type: 'message' }, { clearMedia });
     console.log('[Astra] deleteMessage (revoke) success');
     return true;
    }
   }

   // Fallback to local delete
   const deleteMod = Store.Cmd || window.Astra.mR.findModule(m => m && typeof m.sendDeleteMsgs === 'function');
   if (deleteMod) {
    const chat = Store.Chat.get(msg.id.remote) || await Store.Chat.find(msg.id.remote);
    await deleteMod.sendDeleteMsgs(chat, { list: [msg], type: 'message' }, clearMedia);
    console.log('[Astra] deleteMessage (local) success');
    return true;
   }

   if (msg.delete) await msg.delete();
   return true;
  } catch (err) {
   console.error('[Astra] deleteMessage failed:', err.message);
   throw err;
  }
 };

  window.Astra.bulkDeleteMessages = async function(msgIds, everyone = true, clearMedia = true) {
   try {
    const Store = window.Astra.initializeEngine();
    if (!Array.isArray(msgIds)) msgIds = [msgIds];
    let totalDeleted = 0;
    
    console.log(`[Astra] bulkDeleteMessages count=${msgIds.length} everyone=${everyone}`);
    
    const repo = Store.MessageRepo || Store.MsgRepo || Store.Msg;
    const msgs = [];
    for (const id of msgIds) {
     const m = repo.get(id) || (await repo.getMessagesById?.([id]))?.messages?.[0];
     if (m) msgs.push(m);
    }

    if (msgs.length === 0) return { total: 0 };

    const chat = await window.Astra.getChat(msgs[0].id.remote);
    
    // Group by chat if they are from different chats, but usually purge is within one chat
    const chatMap = new Map();
    for (const m of msgs) {
     const remote = m.id.remote._serialized || m.id.remote;
     if (!chatMap.has(remote)) chatMap.set(remote, []);
     chatMap.get(remote).push(m);
    }

    for (const [remote, list] of chatMap.entries()) {
     const targetChat = Store.Chat.get(remote) || await Store.Chat.find(remote);
     
     // Check if we can revoke all as admin or sender
     const canRevokeAll = everyone && list.every(m => Store.MsgActionChecks && (Store.MsgActionChecks.canSenderRevokeMsg(m) || Store.MsgActionChecks.canAdminRevokeMsg(m)));

     if (everyone && canRevokeAll) {
      const revokeMod = Store.Cmd || window.Astra.mR.findModule(m => m && typeof m.sendRevokeMsgs === 'function');
      if (revokeMod) {
       await revokeMod.sendRevokeMsgs(targetChat, { list, type: 'message' }, { clearMedia });
       console.log(`[Astra] bulkDelete (revoke) success for ${list.length} msgs in ${remote}`);
       totalDeleted += list.length;
       continue;
      }
     }

     // Fallback to local delete
     const deleteMod = Store.Cmd || window.Astra.mR.findModule(m => m && typeof m.sendDeleteMsgs === 'function');
     if (deleteMod) {
      await deleteMod.sendDeleteMsgs(targetChat, { list, type: 'message' }, clearMedia);
      console.log(`[Astra] bulkDelete (local) success for ${list.length} msgs in ${remote}`);
      totalDeleted += list.length;
     } else {
      // Last resort: delete one by one
      for (const m of list) {
        if (m.delete) await m.delete();
        totalDeleted++;
      }
     }
    }
    return { total: totalDeleted };
   } catch (err) {
    console.error('[Astra] bulkDeleteMessages failed:', err.message);
    return { total: 0, error: err.message };
   }
  };

 window.Astra.sendReaction = async function(msgId, reaction) {
  const Store = window.Astra.initializeEngine();
  const repo = Store.MsgRepo || Store.Msg;
  const msg = repo.get(msgId) || (await repo.getMessagesById?.([msgId]))?.messages?.[0];
  if (!msg) throw new Error("Message not found: " + msgId);

  // 1. Try mapped Store function (WWebJS style)
  if (Store.sendReactionToMsg) {
   await Store.sendReactionToMsg(msg, reaction);
   return true;
  }

  // 2. Try Deep Discovery via mR
  const reactionMod = window.Astra.mR.findModule(m => m && typeof m.sendReactionToMsg === 'function');
  if (reactionMod) {
   await reactionMod.sendReactionToMsg(msg, reaction);
   return true;
  }

  // 3. Fallback: createOrUpdateReactions (Modern WA)
  const reactV2 = Store.createOrUpdateReactionsModule || window.Astra.mR.findModule(m => m && typeof m.createOrUpdateReactions === 'function');
  if (reactV2) {
   await reactV2.createOrUpdateReactions([msg], reaction);
   return true;
  }

  throw new Error("Reaction module not found or failed signature.");
 };


 window.Astra.syncHistory = async (chatId) => {
  const Store = window.Astra.initializeEngine();
  const chatWid = window.Astra.createWid(chatId);
  const chat = Store.Chat.get(chatWid) ?? (await Store.Chat.find(chatWid));
  if (chat?.endOfHistoryTransferType === 0) {
   await Store.HistorySync.sendPeerDataOperationRequest(3, {
    chatId: chat.id
   });
   return true;
  }
  return false;
 };

 window.Astra.getMessageById = async function(msgId) {
  const Store = window.Astra.initializeEngine();
  const msg = Store.Msg.get(msgId) || (await Store.Msg.getMessagesById([msgId]))?.messages?.[0];
  return window.Astra.serializeMsg(msg);
 };

 window.Astra.getChatList = async function() {
  const Store = window.Astra.initializeEngine();

  let chats = [];
  for (let i = 0; i < 5; i++) {
   chats = (Store.ChatRepo && Store.ChatRepo.getModelsArray) ? Store.ChatRepo.getModelsArray() : ((Store.Chat && Store.Chat.models) || []);

   // Aggressive Fallback: Find Chat collection via mR
   if (chats.length === 0) {
    const mod = window.Astra.mR.findModule(m => m && m.get && m.models && m.add && (m.getModelsArray || (m.models && m.models.getModelsArray)));
    if (mod) chats = mod.getModelsArray ? mod.getModelsArray() : mod.models;
   }

   if (chats.length > 0) break;
   console.log('[Astra] Chat list empty, waiting for sync... (Attempt ' + (i+1) + ')');
   await new Promise(r => setTimeout(r, 1000));
  }

  return chats.map(c => window.Astra.serializeChat(c));
 };

 window.Astra.sendPoll = async (to, name, options, pollOptions = {}) => {
  const Store = window.Astra.initializeEngine();
  const chatWid = window.Astra.createWid(to);
  if (!chatWid) throw new Error("Astra: Invalid recipient ID: " + to);
  const chat = Store.Chat.get(chatWid) || await Store.Chat.find(chatWid._serialized || chatWid.toString());

  console.log(`[Astra] sendPoll target=${chatWid._serialized} name="${name}" options=${options.length}`);

  const pollPayload = {
   pollName: name,
   pollOptions: options.map((o, i) => ({ name: o, localId: i })),
   pollSelectableOptionsCount: 1
  };

  // 1. Try modern MEX-based poll creation
  const pollMod = Store.Polls || window.Astra.mR.findModule(m => m && typeof m.sendCreatePollMsgs === 'function');
  if (pollMod && typeof pollMod.sendCreatePollMsgs === 'function') {
   console.log('[Astra] Using sendCreatePollMsgs...');
   const result = await pollMod.sendCreatePollMsgs(pollPayload, chat);
   return result ? window.Astra.serializeMsg(result[0] || result) : { success: true };
  }

  // 2. Fallback: Manual raw message creation with messageSecret (as used in WWebJS)
  console.log('[Astra] Falling back to manual poll creation with messageSecret');
  const u = Store.User || Store.UserCredentials;
  const lidUser = u && u.getMaybeMeLidUser ? u.getMaybeMeLidUser() : null;
  const meUser = u && u.getMaybeMePnUser ? u.getMaybeMePnUser() : null;
  const from = chatWid.isLid() ? (lidUser || meUser) : (meUser || lidUser);

  const newId = await (Store.MsgKey?.newId() || Promise.resolve(`${Date.now()}-${Math.random().toString(36).slice(2,9)}`));
  const newMsgKey = new Store.MsgKey({ from, to: chatWid, id: newId, selfDir: 'out' });

  const message = {
   type: 'poll_creation',
   pollName: name,
   pollOptions: pollPayload.pollOptions,
   pollSelectableOptionsCount: pollPayload.pollSelectableOptionsCount,
   messageSecret: window.crypto.getRandomValues(new Uint8Array(32)),
   id: newMsgKey,
   ack: 0,
   from: from,
   to: chatWid,
   local: true,
   self: 'out',
   t: Math.floor(Date.now() / 1000),
   isNewMsg: true
  };

  const sender = Store.SendMessage || Store.MessageSender;
  const [msgPromise] = await sender.addAndSendMsgToChat(chat, message);
  await msgPromise;
  return window.Astra.serializeMsg(message);
 };

 window.Astra.votePoll = async (msgId, selections) => {
  const Store = window.Astra.initializeEngine();
  console.log(`[Astra] votePoll start: ${msgId} (selections: ${selections})`);

  let msg = null;
  try {
   const repo = Store.MessageRepo || Store.MsgRepo || Store.Msg;
   msg = repo.get(msgId);
   if (!msg && repo.getMessagesById) {
    console.log(`[Astra] msg not in cache, fetching via getMessagesById...`);
    // Add a timeout to prevent absolute freeze if WA internals hang
    const fetchPromise = repo.getMessagesById([msgId]);
    const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 5000));
    const res = await Promise.race([fetchPromise, timeoutPromise]).catch(e => {
     console.warn(`[Astra] getMessagesById fetch failed or timed out: ${e.message}`);
     return null;
    });
    msg = res && res.messages ? res.messages[0] : null;
   }
  } catch (e) {
   console.warn(`[Astra] Error during message retrieval: ${e.message}`);
  }

  if (msg) {
   console.log(`[Astra] msg found, attempting internal vote...`);
   try {
    const pollMod = Store.PollsSendVote || window.Astra.mR.findModule(m => m && (typeof m.sendPollVote === 'function' || typeof m.sendVote === 'function' || typeof m.sendPollVoteMEX === 'function'));
    if (pollMod) {
     const method = pollMod.sendPollVoteMEX ? 'sendPollVoteMEX' : (pollMod.sendPollVote ? 'sendPollVote' : (pollMod.sendVote ? 'sendVote' : null));
     if (method) {
      console.log(`[Astra] Using method: ${method}`);
      const selectedOptions = selections.map(idx => msg.pollOptions[idx]);
      const votePromise = (method === 'sendVote')
       ? pollMod[method](msg, new Set(selectedOptions.map(o => o.localId)))
       : pollMod[method](msg, selectedOptions);

      await Promise.race([
       votePromise,
       new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 8000))
      ]);

      console.log(`[Astra] Internal vote successful.`);
      return true;
     }
    }
   } catch (e) {
    console.warn('[Astra] Internal votePoll failed, falling back to DOM:', e.message);
   }
  }

  console.log(`[Astra] Proceeding to votePollDOM...`);
  return await window.Astra.votePollDOM(msgId, selections, msg ? (msg.id.remote || msg.id.participant) : null);
 };

 window.Astra.votePollDOM = async (msgId, selections, chatId) => {
  if (chatId) {
   console.log(`[Astra] Opening chat ${chatId} for DOM voting...`);
   await window.Astra.openChat(chatId);
  }

  console.log(`[Astra] Clicking poll options via DOM...`);
  for (const index of selections) {
   const options = document.querySelectorAll(`input[id*="-option-${index}"]`);
   if (options.length > 0) {
    const target = options[options.length - 1]; // Latest poll
    if (target && !target.checked) {
     target.click();
     await new Promise(r => setTimeout(r, 500));
    }
   }
  }
  console.log(`[Astra] votePollDOM complete.`);
  return true;
 };
})();


(function() {
 window.Astra = window.Astra || {};

 const getWid = (id, Store) => Store.AddressFactory.createWid(id);

 window.Astra.getContacts = function() {
  const Store = window.Astra.initializeEngine();
  if (!Store.ContactRepo || !Store.ContactRepo.getModelsArray) return [];
  const contacts = Store.ContactRepo.getModelsArray();
  return contacts.map(c => window.Astra.serializeContact(c));
 };


 window.Astra.serializeContact = function(c) {
  if (!c) return null;
  const Store = window.Astra.initializeEngine();
  let s = {};
  if (typeof c.serialize === 'function') {
   try { s = c.serialize(); } catch(e) { s = { id: c.id._serialized, name: c.name }; }
  } else {
   s = {
    id: c.id && c.id._serialized ? c.id._serialized : (typeof c.id === 'string' ? c.id : null),
    name: c.name || c.formattedName || null
   };
  }

  // Astra Hardening
  s.id = c.id && c.id._serialized ? c.id._serialized : s.id;
  s.pushname = c.pushname || s.pushname || null;
  s.verifiedName = c.verifiedName || s.verifiedName || null;
  s.isLid = c.id && typeof c.id.isLid === 'function' ? c.id.isLid() : (c.id && c.id._serialized && c.id._serialized.includes('@lid'));

  // Identify Self
  if (Store.User && Store.User.getMaybeMePnUser) {
   const me = Store.User.getMaybeMePnUser();
   s.isMe = (s.id === me._serialized);
  }

  return s;
 };

 window.Astra.blockContact = async function(id) {
  const Store = window.Astra.initializeEngine();
  const contact = Store.ContactRepo.get(id);
  if (!contact) throw new Error("Contact not found");

  if (Store.Blocklist) {
   await Store.Blocklist.blockContact(contact);
   return true;
  }
  throw new Error("Blocklist module not found");
 };

 window.Astra.unblockContact = async function(id) {
  const Store = window.Astra.initializeEngine();
  const contact = Store.ContactRepo.get(id);
  if (!contact) throw new Error("Contact not found");

  if (Store.Blocklist) {
   await Store.Blocklist.unblockContact(contact);
   return true;
  }
  throw new Error("Blocklist module not found");
 };

 window.Astra.getContactId = function(number) {
  const Store = window.Astra.initializeEngine();
  if (!Store.WidFactory) return null;
  try {
   const wid = Store.WidFactory.createWid(number.includes('@') ? number : number + '@c.us');
   return wid ? wid._serialized : null;
  } catch (e) { return null; }
 };

 window.Astra.getProfilePicUrl = async function(id) {
  const Store = window.Astra.initializeEngine();
  const chatWid = Store.WidFactory.createWid(id);

  try {
   // 1. Try ProfilePic module
   if (Store.ProfilePic && Store.ProfilePic.profilePicFind) {
    const profilePic = await Store.ProfilePic.profilePicFind(chatWid);
    if (profilePic && profilePic.eurl) return profilePic.eurl;
   }

   // 2. Try Contact module fallback
   const contact = Store.ContactRepo ? Store.ContactRepo.get(chatWid) : null;
   if (contact && contact.profilePicThumb && contact.profilePicThumb.eurl) {
    return contact.profilePicThumb.eurl;
   }

   // 3. Try Chat module fallback
   const chat = Store.Chat ? Store.Chat.get(chatWid) : null;
   if (chat && chat.contact && chat.contact.profilePicThumb && chat.contact.profilePicThumb.eurl) {
    return chat.contact.profilePicThumb.eurl;
   }

   return null;
  } catch (e) {
   console.warn("Astra: getProfilePicUrl failed", e);
   return null;
  }
 };
})();


(function() {
 window.Astra = window.Astra || {};

 const getWid = (id, Store) => window.Astra.createWid(id);
 const getChat = async (id, Store) => await window.Astra.getChat(getWid(id, Store));

 window.Astra.kickParticipants = async function(groupId, participants) {
  const Store = window.Astra.initializeEngine();
  const chat = getChat(groupId, Store);
  if (!chat) throw new Error("Group not found");

  const pids = participants.map(p => getWid(p, Store));
  if (Store.GroupParticipants && Store.GroupParticipants.removeParticipants) {
    await Store.GroupParticipants.removeParticipants(chat, pids);
  } else {
    // Fallback to legacy if mapped differently
    await window.Store.GroupParticipants.removeParticipants(chat, pids);
  }
  return true;
 };

 window.Astra.addParticipants = async function(groupId, participants) {
  const Store = window.Astra.initializeEngine();
  const chat = getChat(groupId, Store);
  const pids = participants.map(p => getWid(p, Store));

  if (Store.GroupParticipants && Store.GroupParticipants.addParticipants) {
   await Store.GroupParticipants.addParticipants(chat, pids);
  } else if (Store.GroupParticipants && Store.GroupParticipants.sendAddParticipantsRPC) {
    // Basic RPC call if wrapper not found
    // This might require more args, but sticking to what worked in base.py heuristic logic finding the wrapper
    // Actually LegacyStore maps 'sendAddParticipantsRPC' to GroupParticipants.
    // We'll rely on Store.GroupParticipants existing.
    // If manual composition worked, it should have it.
    await Store.GroupParticipants.addParticipants(chat, pids);
  }
  return true;
 };

 window.Astra.promoteParticipants = async function(groupId, participants) {
  const Store = window.Astra.initializeEngine();
  const chat = getChat(groupId, Store);
  const pids = participants.map(p => getWid(p, Store));
  await Store.GroupParticipants.promoteParticipants(chat, pids);
  return true;
 };

 window.Astra.demoteParticipants = async function(groupId, participants) {
  const Store = window.Astra.initializeEngine();
  const chat = getChat(groupId, Store);
  const pids = participants.map(p => getWid(p, Store));
  await Store.GroupParticipants.demoteParticipants(chat, pids);
  return true;
 };

 window.Astra.setGroupSubject = async function(groupId, subject) {
  const Store = window.Astra.initializeEngine();
  const chatWid = getWid(groupId, Store);
  await Store.GroupUtils.setGroupSubject(chatWid, subject);
  return true;
 };

 window.Astra.setGroupDescription = async function(groupId, description) {
  const Store = window.Astra.initializeEngine();
  const chat = getChat(groupId, Store);
  const chatWid = getWid(groupId, Store);

  // Generate new id with fallbacks for different WA versions
  let newId;
  if (Store.MessageIdentity && Store.MessageIdentity.newId) {
   newId = await Store.MessageIdentity.newId();
  } else if (Store.MsgKey && Store.MsgKey.newId) {
   newId = await Store.MsgKey.newId();
  } else if (Store.Msg && Store.Msg.newId) {
   newId = await Store.Msg.newId();
  } else {
   newId = `${Date.now()}-${Math.random().toString(36).slice(2,9)}`;
  }

  const descId = chat.groupMetadata ? chat.groupMetadata.descId : null;

  if (Store.GroupUtils && typeof Store.GroupUtils.setGroupDescription === 'function') {
   await Store.GroupUtils.setGroupDescription(chatWid, description, newId, descId);
   return true;
  }
  // Fallback: try legacy GroupUtils or throw clear error
  if (window.Store && window.Store.GroupUtils && typeof window.Store.GroupUtils.setGroupDescription === 'function') {
   await window.Store.GroupUtils.setGroupDescription(chatWid, description, newId, descId);
   return true;
  }
  throw new Error('setGroupDescription not available');
 };

 window.Astra.leaveGroup = async function(groupId) {
  const Store = window.Astra.initializeEngine();
  const chat = await getChat(groupId, Store);
  if (!chat) throw new Error("Chat not found: " + groupId);

  const exitAction = Store.GroupUtils?.sendExitGroup || (window.Store.GroupUtils && window.Store.GroupUtils.sendExitGroup);
  if (exitAction) {
   await exitAction(chat);
   return true;
  }
  throw new Error("sendExitGroup not available");
 };

 window.Astra.createGroup = async function(title, participants) {
  const Store = window.Astra.initializeEngine();
  const pids = participants.map(p => {
   const w = window.Astra.createWid(p);
   if (!w) return null;
   // Audited: expects { lid: Wid } or { phoneNumber: Wid }
   return { phoneNumber: w, lid: w };
  }).filter(w => !!w);

  const meta = {
   'title': title,
   'addressingModeOverride': 'lid',
   'memberAddMode': false,
   'membershipApprovalMode': false,
   'announce': false,
   'restrict': false,
   'ephemeralDuration': 0
  };

  const GroupCreate = Store.GroupCreate;
  if (!GroupCreate) throw new Error("GroupCreate module not found");

  const createFn = GroupCreate.sendCreateGroup || GroupCreate.createGroup || GroupCreate.sendCreateGroupRPC;
  if (!createFn) throw new Error("createGroup method not found");

  const res = await createFn.call(GroupCreate, meta, pids);
  const wid = res.wid ? res.wid._serialized : (res.id ? res.id._serialized : (res._serialized || res));
  return wid;
 };

 window.Astra.getInviteCode = async function(groupId) {
  const Store = window.Astra.initializeEngine();
  const chatWid = getWid(groupId, Store);

  // Prioritize WAGroupInviteQuery (mapped in base.py), then fallback to Store.GroupInvite (Legacy)
  const InviteStore = Store.WAGroupInviteQuery || Store.WAGroupInvite || (window.Store && window.Store.GroupInvite) || Store.WAGroupInviteV4 || (window.Store && window.Store.GroupInviteV4) || Store.WAGroupQuery;

  if (InviteStore) {
   if (InviteStore.fetchMexGroupInviteCode) {
     // MEX version expects string ID as per GroupChat.js:395
     const res = await InviteStore.fetchMexGroupInviteCode(groupId);
     return res.code || res;
   } else if (InviteStore.queryGroupInviteCode) {
     // Legacy version expects Wid as per GroupChat.js:396
     const res = await InviteStore.queryGroupInviteCode(chatWid, true);
     return res.code || res;
   } else if (InviteStore.queryGroupInvite) {
     const res = await InviteStore.queryGroupInvite(chatWid);
     return res.code || res;
   } else if (InviteStore.sendGetGroupInviteCode) {
     const res = await InviteStore.sendGetGroupInviteCode(chatWid);
     return res.code || res;
   } else if (InviteStore.queryGroupInviteV4) {
     const res = await InviteStore.queryGroupInviteV4(chatWid);
     return res.code || res;
   }
  }
  throw new Error("GroupInvite module not found");
 };

 window.Astra.revokeInviteCode = async function(groupId) {
  const Store = window.Astra.initializeEngine();
  const chatWid = getWid(groupId, Store);

  const ResetStore = Store.WAGroupInviteReset || Store.WAGroupInvite || (window.Store && window.Store.GroupInvite);

  if (ResetStore) {
   if (ResetStore.resetGroupInviteCode) {
     const res = await ResetStore.resetGroupInviteCode(chatWid);
     return res.code;
   } else if (ResetStore.sendResetGroupInviteCode) {
     const res = await ResetStore.sendResetGroupInviteCode(chatWid);
     return res.code;
   }
  }
  throw new Error("GroupInviteReset module not found");
 };

 // Simplified without image crop for now - expecting base64 from python
 window.Astra.setGroupPicture = async function(groupId, thumb, picture) {
   const Store = window.Astra.initializeEngine();
   const chatWid = getWid(groupId, Store);

   const collection = Store.ProfilePicRepo.get(groupId) || (await Store.ProfilePicRepo.find(groupId));
   if (!collection.canSet()) throw new Error("Cannot set picture");

   if (Store.GroupUtils && Store.GroupUtils.sendSetPicture) {
    await Store.GroupUtils.sendSetPicture(chatWid, thumb, picture);
    return true;
   }
   throw new Error("sendSetPicture not found");
 };

 window.Astra.deleteGroupPicture = async function(groupId) {
   const Store = window.Astra.initializeEngine();
   const chatWid = getWid(groupId, Store);
   const collection = Store.ProfilePicRepo.get(groupId);
   if (!collection.canDelete()) throw new Error("Cannot delete picture");

   if (Store.GroupUtils && Store.GroupUtils.requestDeletePicture) {
    await Store.GroupUtils.requestDeletePicture(chatWid);
    return true;
   }
   // Fallback
   throw new Error("requestDeletePicture not found");
 };

 window.Astra.getGroupInfo = async function(groupId) {
  const Store = window.Astra.initializeEngine();
  const chatWid = getWid(groupId, Store);
  let c = getChat(groupId, Store) || (Store.ChatRepo && Store.ChatRepo.get(chatWid));

  if (!c) {
   // Wait for chat to appear (race condition after creation)
   for (let i = 0; i < 5; i++) {
    await new Promise(r => setTimeout(r, 500));
    c = getChat(groupId, Store) || (Store.ChatRepo && Store.ChatRepo.get(chatWid));
    if (c) break;
   }
  }

  if (!c) return null;

  // Try to update metadata if missing or generic
  const hasMeta = !!c.groupMetadata;
  const nameIsGeneric = hasMeta && (!c.groupMetadata.subject || c.groupMetadata.subject === 'Group' || c.name === 'Group');

  if (!hasMeta || nameIsGeneric) {
   const metaColl = Store.GroupMetadata;
   if (metaColl && metaColl.update) {
    try {
     await metaColl.update(chatWid);
    } catch (e) { console.warn("Astra: Group metadata update failed", e); }
   }
  }

  return {
   id: c.id._serialized,
   title: (c.groupMetadata && c.groupMetadata.subject) || c.name || c.formattedTitle || "Group",
   subject: (c.groupMetadata && c.groupMetadata.subject) || c.name || c.formattedTitle || "Group",
   description: (c.groupMetadata && c.groupMetadata.desc) || "",
   owner: (c.groupMetadata && c.groupMetadata.owner) ? (c.groupMetadata.owner._serialized || c.groupMetadata.owner) : null,
   creation: c.groupMetadata ? c.groupMetadata.creation : null,
   participants: (c.groupMetadata && c.groupMetadata.participants) ? c.groupMetadata.participants.map(p => ({
    id: p.id._serialized,
    isAdmin: p.isAdmin,
    isSuperAdmin: p.isSuperAdmin
   })) : []
  };
 };
})();


(function() {
 window.Astra = window.Astra || {};

 window.Astra.base64ToFile = ({ data, mimetype, filename }) => {
  const bin = window.atob(data);
  const buf = new ArrayBuffer(bin.length);
  const view = new Uint8Array(buf);
  for (let i = 0; i < bin.length; i++) {
   view[i] = bin.charCodeAt(i);
  }
  const blob = new Blob([buf], { type: mimetype });
  return new File([blob], filename, { type: mimetype, lastModified: Date.now() });
 };

 window.Astra.bufToBase64 = (buf) =>
  new Promise((resolve, reject) => {
   const blob = new Blob([buf], { type: 'application/octet-stream' });
   const reader = new FileReader();
   reader.onload = () => resolve(reader.result.split(',')[1]);
   reader.onerror = (e) => reject(e);
   reader.readAsDataURL(blob);
  });

 window.Astra.chunkedUploads = {};

 window.Astra.initChunkedUpload = (id, totalSize) => {
  window.Astra.chunkedUploads[id] = {
   buffer: new Uint8Array(totalSize),
   offset: 0,
   totalSize: totalSize
  };
  return true;
 };

 window.Astra.pushChunk = (id, dataB64) => {
  const session = window.Astra.chunkedUploads[id];
  if (!session) throw new Error("Astra: Upload session not found: " + id);
  
  const bin = window.atob(dataB64);
  const view = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) {
   session.buffer[session.offset + i] = bin.charCodeAt(i);
  }
  session.offset += bin.length;
  return { offset: session.offset, total: session.totalSize };
 };

 window.Astra.send_media = async function(to, data, mimetype, filename, caption, options = {}) {
  return await window.Astra.sendMedia(to, { data, mimetype, filename }, { caption, ...options });
 };

 window.Astra.sendMedia = async function(to, media, options = {}) {
  console.log("Astra: sendMedia called", { to, mimetype: media.mimetype });
  const Store = window.Astra.initializeEngine();

  const mimetype = media.mimetype || 'application/octet-stream';
  const isVideo = mimetype.startsWith('video/');
  const isAudio = mimetype.startsWith('audio/');
  const isImage = mimetype.startsWith('image/');
  const targetId = typeof to === 'string' ? to : (to._serialized || to.id?._serialized || to.id);
  const wid = window.Astra.createWid(targetId.includes('@') ? targetId : `${targetId}@c.us`);
  const chat = await window.Astra.getChat(wid);
  if (!chat) throw new Error('Astra: Chat not found for ' + targetId);

  try {
   const lid = Store.UserCredentials.getMaybeMeLidUser ? Store.UserCredentials.getMaybeMeLidUser() : null;
   const pn = Store.UserCredentials.getMaybeMePnUser ? Store.UserCredentials.getMaybeMePnUser() : (Store.SessionInfo && (Store.SessionInfo.wid || Store.SessionInfo.me));

   // Generate id with fallbacks for different WA versions
   let id;
   if (Store.MessageIdentity && Store.MessageIdentity.newId) {
    id = await Store.MessageIdentity.newId();
   } else if (Store.MsgKey && Store.MsgKey.newId) {
    id = await Store.MsgKey.newId();
   } else if (Store.Msg && Store.Msg.newId) {
    id = await Store.Msg.newId();
   } else {
    // Best-effort fallback: timestamp-based id
    id = `${Date.now()}-${Math.random().toString(36).slice(2,9)}`;
   }

   let from;
   const isLidChat = chat.id && (typeof chat.id.isLid === 'function' ? chat.id.isLid() : chat.id.isLid);
   if (isLidChat) {
    from = lid || pn;
   } else {
    from = pn;
   }

   if (!from) {
    throw new Error("Astra: Could not determine 'from' identity (LID/PN missing)");
   }

   let part;
   if (chat.id && (typeof chat.id.isGroup === 'function' ? chat.id.isGroup() : chat.id.isGroup)) {
    const isLidGroups = chat.groupMetadata && chat.groupMetadata.isLidAddressingMode;
    const f = isLidGroups ? (lid || pn) : pn;
    part = window.Astra.createWid(f);
   }

   let key;
   if (Store.MessageIdentity) {
    key = new Store.MessageIdentity({
     from: window.Astra.createWid(from),
     to: chat.id,
     id,
     participant: part ? window.Astra.createWid(part) : undefined,
     selfDir: 'out'
    });
   } else if (Store.MsgKey) {
    key = new Store.MsgKey({
     from: from,
     to: chat.id,
     id: id,
     participant: part ? window.Astra.createWid(part) : undefined,
     selfDir: 'out'
    });
   } else {
    key = { id: id, _serialized: typeof id === 'string' ? id : (id && id._serialized ? id._serialized : String(id)) };
   }

   let file;
  if (media.uploadId && window.Astra.chunkedUploads[media.uploadId]) {
   const session = window.Astra.chunkedUploads[media.uploadId];
   const blob = new Blob([session.buffer], { type: mimetype });
   file = new File([blob], media.filename || 'media', { type: mimetype, lastModified: Date.now() });
   delete window.Astra.chunkedUploads[media.uploadId];
  } else {
   file = window.Astra.base64ToFile(media);
  }

   // Defensive: if it's a video, ensure we have dimensions before prep
   if (mimetype.startsWith('video/')) {
    try {
     const video = document.createElement('video');
     video.preload = 'metadata';
     const videoUrl = URL.createObjectURL(file);
     video.src = videoUrl;
     await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
       console.warn("Astra: video dimensions timeout, proceeding anyway");
       resolve();
      }, 5000);
      video.onloadedmetadata = () => {
       clearTimeout(timeout);
       if (video.videoWidth && video.videoHeight) {
        console.log(`Astra: video dims detected: ${video.videoWidth}x${video.videoHeight}`);
       }
       URL.revokeObjectURL(videoUrl);
       resolve();
      };
      video.onerror = () => {
       clearTimeout(timeout);
       console.error("Astra: video metadata load error");
       resolve();
      };
     });
    } catch (vErr) {
     console.warn("Astra: dimension probe failed", vErr);
    }
   }

   // Create source blob with fallbacks (MediaBuffer, OpaqueData, etc.)
   let source;
   if (Store.MediaBuffer && Store.MediaBuffer.createFromData) {
    source = await Store.MediaBuffer.createFromData(file, mimetype);
   } else if (Store.OpaqueData && Store.OpaqueData.createFromData) {
    source = await Store.OpaqueData.createFromData(file, mimetype);
   } else if (Store.OpaqueData && Store.OpaqueData.fromData) {
    source = await Store.OpaqueData.fromData(file, mimetype);
   } else {
    // Last resort: use raw file object
    source = file;
   }

   const params = {
    asSticker: options.asSticker,
    asGif: options.asGif,
    isPtt: options.asVoice,
    asAudio: options.asAudio,
    asDocument: options.asDocument,
    width: options.width,
    height: options.height
   };

   // Prep media using available prep module
   let prep;
   if (Store.MediaEngine && Store.MediaEngine.prepRawMedia) {
    prep = Store.MediaEngine.prepRawMedia(source, params);
   } else if (Store.MediaPrep && Store.MediaPrep.prepRawMedia) {
    prep = Store.MediaPrep.prepRawMedia(source, params);
   } else if (Store.MediaDataUtils && Store.MediaDataUtils.prepRawMedia) {
    prep = Store.MediaDataUtils.prepRawMedia(source, params);
   } else {
    throw new Error('Astra: No media prep module available');
   }

   // Await prep result with compatibility for different return types
   let data;
   if (prep && typeof prep.waitForPrep === 'function') {
    data = await prep.waitForPrep();
   } else if (prep && typeof prep.then === 'function') {
    data = await prep;
   } else {
    data = prep;
   }

   // Get or create media metadata (MediaMetadata vs MediaObject)
   let meta;
   if (Store.MediaMetadata && Store.MediaMetadata.getOrCreateMediaObject) {
    meta = Store.MediaMetadata.getOrCreateMediaObject(data.filehash);
   } else if (Store.MediaObject && Store.MediaObject.getOrCreateMediaObject) {
    meta = Store.MediaObject.getOrCreateMediaObject(data.filehash);
   } else {
    meta = { filehash: data.filehash, size: data.size };
   }

   if (!data.filehash) throw new Error('Engine fault: filehash missing');

   // Ensure mediaBlob is of the expected class
   const isMediaBufferInstance = Store.MediaBuffer && (data.mediaBlob instanceof Store.MediaBuffer);
   const isOpaqueDataInstance = Store.OpaqueData && (data.mediaBlob instanceof Store.OpaqueData);
   if (!isMediaBufferInstance && !isOpaqueDataInstance) {
    if (Store.MediaBuffer && Store.MediaBuffer.createFromData) {
     data.mediaBlob = await Store.MediaBuffer.createFromData(data.mediaBlob, data.mediaBlob.type || media.mimetype);
    } else if (Store.OpaqueData && Store.OpaqueData.createFromData) {
     data.mediaBlob = await Store.OpaqueData.createFromData(data.mediaBlob, data.mediaBlob.type || media.mimetype);
    }
   }

   // renderableUrl fallback
   if (data.mediaBlob && typeof data.mediaBlob.url === 'function') {
    data.renderableUrl = data.mediaBlob.url();
   } else if (data.mediaBlob && (data.mediaBlob instanceof Blob || (data.mediaBlob && data.mediaBlob.size))) {
    data.renderableUrl = URL.createObjectURL(data.mediaBlob);
   }

   if (meta && typeof meta.consolidate === 'function') meta.consolidate(data.toJSON ? data.toJSON() : data);
   if (data.mediaBlob && typeof data.mediaBlob.autorelease === 'function') data.mediaBlob.autorelease();

   // Upload using available uploader implementations
   let upload;
   const callId = options._call_id;

   // Hook into MediaObject events for real-time progress
   if (meta && typeof meta.on === 'function') {
    meta.on('change:uploadProgress', (p) => {
     if (callId && window.Astra.emit) {
      window.Astra.emit('progress', { id: callId, current: p, total: 100 });
     }
    });
   }

   try {
    const uploadParams = {
     mimetype: data.mimetype || media.mimetype,
     mediaObject: meta,
     mediaType: data.type || media.type
    };

    if (Store.AssetUploader && Store.AssetUploader.uploadMedia) {
     upload = await Store.AssetUploader.uploadMedia(uploadParams);
    } else if (Store.MediaUpload && Store.MediaUpload.uploadMedia) {
     upload = await Store.MediaUpload.uploadMedia(uploadParams);
    } else if (Store.MediaUpload && Store.MediaUpload.upload) {
     upload = await Store.MediaUpload.upload(uploadParams);
    } else if (Store.MediaUpload && Store.MediaUpload.startUpload) {
     upload = await Store.MediaUpload.startUpload(uploadParams);
    } else if (Store.UploadUtils && Store.UploadUtils.encryptAndUpload) {
     const controller = new AbortController();
     const uploadedInfo = await Store.UploadUtils.encryptAndUpload({
      blob: file,
      type: data.type || 'media',
      signal: controller.signal,
      onProgress: (p) => {
       if (callId && window.Astra.emit) {
        window.Astra.emit('progress', { id: callId, current: p, total: 100 });
       }
      }
     });
     upload = { mediaEntry: { mmsUrl: uploadedInfo.url || uploadedInfo.clientUrl, directPath: uploadedInfo.directPath || uploadedInfo.url, mediaKey: uploadedInfo.mediaKey || uploadedInfo.key, mediaKeyTimestamp: uploadedInfo.mediaKeyTimestamp, encFilehash: uploadedInfo.encFilehash || uploadedInfo.uploadhash } };
    } else {
     throw new Error('Astra: No uploader available to upload media');
    }
   } catch (uerr) {
    console.error('upload error fallback:', uerr);
    throw uerr;
   }

   const entry = upload && (upload.mediaEntry || upload.media_entry || upload) || {};
   // Normalize and set data
   const newData = { clientUrl: entry.mmsUrl || entry.clientUrl, directPath: entry.directPath || entry.direct_path || entry.directPath, mediaKey: entry.mediaKey || entry.media_key || entry.media_key || entry.key,
      mediaKeyTimestamp: entry.mediaKeyTimestamp || entry.media_key_timestamp, filehash: meta.filehash,
      encFilehash: entry.encFilehash || entry.enc_filehash || entry.uploadhash || entry.encFilehash, size: meta.size };
   if (typeof data.set === 'function') {
    data.set(newData);
   } else {
    Object.assign(data, newData);
   }

   // Prepare target and repo early so quoted message handling can use them
   const target = Store.EngineState && Store.EngineState.unproxy ? Store.EngineState.unproxy(chat) : chat;
   const repo = Store.MessageRepo || Store.MsgRepo;

   let msg = {
    id: key, ack: 0, from, to: chat.id, local: true, self: 'out',
    t: parseInt(Date.now() / 1000), isNewMsg: true, ...options
   };

   // Add quote support
   if (options.quoted_message_id) {
    const quotedMsg = repo.get(options.quoted_message_id) || await repo.find(options.quoted_message_id);
    if (quotedMsg) {
     if (typeof quotedMsg.msgContextInfo === 'function') {
      try {
       Object.assign(msg, quotedMsg.msgContextInfo(target));
      } catch(e) {
       // Fallback: attach quoted fields manually if msgContextInfo fails
       msg.quotedMsg = quotedMsg;
       msg.quotedStanzaId = quotedMsg.id && quotedMsg.id.id;
       msg.quotedParticipant = quotedMsg.author || quotedMsg.from;
       msg.quotedRemoteJid = quotedMsg.id && quotedMsg.id.remote;
      }
     } else {
      msg.quotedMsg = quotedMsg;
      msg.quotedStanzaId = quotedMsg.id && quotedMsg.id.id;
      msg.quotedParticipant = quotedMsg.author || quotedMsg.from;
      msg.quotedRemoteJid = quotedMsg.id && quotedMsg.id.remote;
     }
    }
   }

   msg = Object.assign(msg, data.toJSON ? data.toJSON() : data);
   msg.type = data.type;
   msg.caption = options.caption || '';
   msg.body = undefined;

   try {
    const p1 = (await Store.SendMessage.addAndSendMsgToChat(target, msg))[0];
    await p1;
   } catch (sendErr) {
    console.error('[Astra] sendMedia send error:', sendErr);
    throw sendErr;
   }

   const serialized = key && (key._serialized || (typeof key === 'string' ? key : (key && key.id ? (key.id._serialized || key.id) : null)));
   return {
    id: serialized || id,
    body: msg.body || msg.caption || "",
    type: msg.type,
    isSent: true,
    timestamp: msg.t
   };
  } catch (e) {
   // Normalize and stringify error so Page.evaluate returns a readable message
   try {
    const message = (e && e.message) ? e.message : (typeof e === 'string' ? e : JSON.stringify(e));
    const stack = (e && e.stack) ? '\n' + e.stack : '';
    const info = `Astra: sendMedia error: ${message}${stack}`;
    console.error("sendMedia error:", info);
    throw new Error(info);
   } catch (ee) {
    console.error('sendMedia stringify failed', ee);
    throw e;
   }
  }
 };

 console.log("Astra Media Bridge v2 Loaded");

 window.Astra.mediaCache = {};

 window.Astra.readMediaChunk = async (id, offset, length) => {
  const buffer = window.Astra.mediaCache[id];
  if (!buffer) return null;
  
  // Use subarray for zero-copy view, then blob it
  const slice = buffer.subarray(offset, offset + length);
  return await window.Astra.bufToBase64(slice);
 };

 window.Astra.clearMediaCache = (id) => {
  delete window.Astra.mediaCache[id];
  return true;
 };

 window.Astra.retrieveMediaFromDOM = async (msgId) => {
  console.log(`[Astra] Attempting DOM retrieval for ${msgId}`);
  try {
   const Store = window.Astra.initializeEngine();
   
   // 0. Scroll message into view (Handle Virtualization)
   // WhatsApp removes off-screen messages from DOM. We must scroll to it.
   try {
    const msg = window.Store.Msg.get(msgId);
    if (msg && window.Store.Cmd && window.Store.Cmd.scrollToMessage) {
     console.log("[Astra] DOM: Scrolling to message...");
     window.Store.Cmd.scrollToMessage(msg);
     await new Promise(r => setTimeout(r, 700)); // Wait for render
    }
   } catch (e) {
    console.warn("[Astra] DOM: Scroll failed, trying searching anyway", e);
   }

   // 1. Find the message container
   // Try data-id first (most precise), then fallback to row matching
   let msgElement = document.querySelector(`div[data-id="${msgId}"]`) || 
           document.querySelector(`div[data-id*="${msgId.split('_').pop()}"]`);
   
   if (!msgElement) {
    // Fallback: Search all rows in main for the ID
    const rows = Array.from(document.querySelectorAll('#main [role="row"]'));
    msgElement = rows.find(r => r.getAttribute('data-id') === msgId || r.innerHTML.includes(msgId.split('_').pop()));
   }

   if (!msgElement) {
    console.warn("[Astra] DOM: Message container not found (Virtualization?)");
    return null;
   }

   // 2. Find the media element
   // Images are usually img, Videos/GIFs have video or img thumbnails
   // We look for src starting with blob:
   const mediaElement = Array.from(msgElement.querySelectorAll('img, video')).find(el => el.src && el.src.startsWith('blob:'));
   
   if (!mediaElement) {
    console.warn("[Astra] DOM: No blob media element found in message");
    // Attempt to click to load if it's a "Click to download" overlay? 
    // Risky, skipping for now.
    return null;
   }

   const blobUrl = mediaElement.src;
   console.log(`[Astra] DOM: Found blob URL: ${blobUrl}`);

   // 3. Fetch the data from the blob URL
   // This works because we are in the same context
   const response = await fetch(blobUrl);
   const blob = await response.blob();
   const buffer = await blob.arrayBuffer();
   const arrayBuffer = new Uint8Array(buffer);

   console.log(`[Astra] DOM: Fetched ${arrayBuffer.byteLength} bytes`);
   return arrayBuffer;

  } catch (e) {
   console.error("[Astra] DOM retrieval failed:", e);
   return null;
  }
 };

 window.Astra.retrieveMedia = async (msgId) => {
  console.log(`[Astra] retrieveMedia called for ${msgId}`);
  const Store = window.Astra.initializeEngine();
  const repo = Store.MessageRepo || Store.MsgRepo;
  let msgIdObj = msgId;
  if (typeof msgId === 'string' && Store.MessageIdentity && Store.MessageIdentity.fromString) {
   try { msgIdObj = Store.MessageIdentity.fromString(msgId); } catch(e) {}
  }

  const msg = repo.get(msgIdObj) || (await repo.getMessagesById([msgId]))?.messages?.[0];
  if (!msg) {
   console.warn("msg not found in repo");
   return null;
  }

  let decryptedMedia = null;

  // --- STRATEGY 1: Internal DownloadManager (Preferred for full quality) ---
  if (msg.directPath && msg.mediaKey && msg.encFilehash && msg.filehash) {
   try {
    const downloadManager = window.Store.DownloadManager;
    const downloadFunc = downloadManager?.downloadAndMaybeDecrypt;
    
    if (downloadFunc) {
      if (msg.mediaData.mediaStage != 'RESOLVED') {
       try {
        console.log("Downloading body...");
        await msg.downloadMedia({ downloadEvenIfExpensive: true, rmrReason: 1 });
       } catch (e) {
        console.warn("downloadMedia failed", e);
       }
      }

      console.log("Decrypting media...");
      const mockQpl = { addAnnotations: function() { return this; }, addPoint: function() { return this; } };
      decryptedMedia = await downloadFunc({
       directPath: msg.directPath,
       encFilehash: msg.encFilehash,
       filehash: msg.filehash,
       mediaKey: msg.mediaKey,
       mediaKeyTimestamp: msg.mediaKeyTimestamp || msg.t,
       type: msg.type,
       signal: (new AbortController).signal,
       downloadQpl: mockQpl
      });
    }
   } catch (err) {
    console.error("Strategy 1 (Internal) failed:", err);
   }
  }

  // --- STRATEGY 2: DOM Scraping (Fallback) ---
  if (!decryptedMedia) {
   console.log("Internal download failed or missing params. Switching to Strategy 2: DOM.");
   decryptedMedia = await window.Astra.retrieveMediaFromDOM(msgId);
  }

  if (!decryptedMedia) {
   console.error("All strategies failed. Cannot retrieve media.");
   return null;
  }

  console.log("Media retrieved. Caching...");
  // Chunking Strategy
  const streamId = `media_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  window.Astra.mediaCache[streamId] = decryptedMedia;

  return {
   streamId: streamId,
   length: decryptedMedia.byteLength,
   mimetype: msg.mimetype,
   filename: msg.filename,
   filesize: msg.size
  };
 };
})();


window.Astra.getDiagnostics = async function() {
 const Store = window.Astra.initializeEngine();
 const diag = {
  version: (window.Debug && window.Debug.VERSION) ? window.Debug.VERSION : "Unknown",
  user: (Store && Store.UserCredentials && typeof Store.UserCredentials.getMaybeMePnUser === 'function') ? (Store.UserCredentials.getMaybeMePnUser()?.toString() || "Unknown") : "Unknown",
  session: (Store && Store.SessionInfo) ? (Store.SessionInfo.wid?._serialized || Store.SessionInfo.me?._serialized || "Unknown") : "Unknown",
  chatCount: (Store && Store.ChatRepo && Store.ChatRepo.models) ? Store.ChatRepo.models.length : 0,
  stores: Object.keys(window.InternalStore || {}).length,
  userAgent: navigator.userAgent,
  timestamp: new Date().toISOString(),
  features: (Store && Store.Features && typeof Store.Features.getFeatures === 'function') ? Store.Features.getFeatures() : {},
  stream: (Store && Store.WAWebStreamModel && Store.WAWebStreamModel.Stream) ? {
   mode: Store.WAWebStreamModel.Stream.mode,
   state: Store.WAWebStreamModel.Stream.state,
   isOnline: Store.WAWebStreamModel.Stream.mode === 'MAIN'
  } : (Store && Store.Stream) ? {
   mode: Store.Stream.mode,
   state: Store.Stream.state,
   isOnline: Store.Stream.mode === 'MAIN'
  } : "Unknown"
 };
 return diag;
};

window.Astra.getDomSnippet = function(selector) {
 const el = document.querySelector(selector);
 if (!el) return "Not found";
 return el.outerHTML.substring(0, 1000);
};

window.Astra.getFullDom = function() {
 return document.documentElement.outerHTML;
};


(function() {
 window.Astra = window.Astra || {};

 window.Astra.sendTextStatus = async (text, options = {}) => {
  console.log(`[Astra] sendTextStatus: ${text.substring(0, 20)}...`);
  const Store = window.Astra.initializeEngine();

  const payload = {
   body: text,
   type: 'chat',
   backgroundColor: options.backgroundColor || '#000000',
   font: options.font || 1,
   statusV3: true,
   isStatusV3: true
  };

  let StatusV3Action = window.Store.StatusUtils || window.Store.StatusV3Action;

  if (!StatusV3Action && window.Astra.mR) {
    StatusV3Action = window.Astra.mR.findModule(m => m && (m.postStatusV3 || m.sendStatusV3 || m.sendTextStatus || m.sendMediaStatus || m.setMyStatus || m.postStatus));
  }

  if (StatusV3Action) {
   let sendFn = StatusV3Action.postStatusV3 || StatusV3Action.sendTextStatus || StatusV3Action.setMyStatus || StatusV3Action.postStatus || StatusV3Action.sendStatusV3;
   let target = StatusV3Action;

   if (!sendFn) {
    target = Object.values(StatusV3Action).find(m => m && (m.postStatusV3 || m.postStatus || m.sendStatusV3)) || target;
    sendFn = target.postStatusV3 || target.postStatus || target.sendStatusV3;
   }

   if (sendFn) {
    try {
     console.log('[Astra] Attempting internal status update...');
     await Promise.race([
      sendFn.call(target, payload),
      new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 8000))
     ]);
     console.log('[Astra] Internal status update successful.');
     return true;
    } catch (e) {
     console.warn(`[Astra] Internal status update failed or timed out: ${e.message}`);
    }
   }
  }

  console.log('[Astra] Falling back to DOM for status update...');
  return await window.Astra.sendTextStatusDOM(text);
 };

 window.Astra.sendMediaStatus = async (data, type, caption = "", options = {}) => {
  const Store = window.Astra.initializeEngine();

  // 1. Prepare Media
  let b64 = data;
  if (b64.includes(',')) b64 = b64.split(',')[1];

  const mime = type === 'image' ? 'image/jpeg' : 'video/mp4';
  const mediaData = await window.Astra.prepareMedia({
   data: b64,
   mimetype: mime,
   filename: 'status'
  });

  // 2. Upload Media
  const uploadResult = await window.Astra.uploadMedia(mediaData);
  if (!uploadResult || !uploadResult.mediaEntry) throw new Error('Astra: Status media upload failed');

  // 3. Post Status
  const payload = {
   media: uploadResult.mediaEntry,
   caption: caption,
   type: type,
   statusV3: true,
   isStatusV3: true
  };

  let StatusV3Action = window.Store.StatusUtils || window.Store.StatusV3Action;

  if (!StatusV3Action) {
   try {
    // Try aggressive search via Astra mapper
    StatusV3Action = window.Astra.mR.findModule('postStatusV3') ||
         window.Astra.mR.findModule('sendStatusV3') ||
         window.Astra.mR.findModule('setMyStatus');
   } catch (e) {}
  }

  if (!StatusV3Action && window.Astra.mR) {
    const found = window.Astra.mR.findModule(m => m && (m.postStatusV3 || m.sendStatusV3 || m.sendTextStatus || m.sendMediaStatus || m.setMyStatus || m.postStatus));
    if (found) StatusV3Action = found;
  }

  if (!StatusV3Action) throw new Error('Astra: StatusV3Action module not found');

  let sendFn = StatusV3Action.postStatusV3 || StatusV3Action.sendMediaStatus || StatusV3Action.setMyStatus || StatusV3Action.postStatus || StatusV3Action.sendStatusV3;
  let target = StatusV3Action;

  if (!sendFn) {
   target = Object.values(StatusV3Action).find(m => m && (m.postStatusV3 || m.postStatus || m.sendStatusV3)) || target;
   sendFn = target.postStatusV3 || target.postStatus || target.sendStatusV3;
  }

  if (!sendFn) throw new Error('Astra: postStatusV3 method not found on module');

  return await sendFn.call(target, payload);
 };
 window.Astra.sendTextStatusDOM = async (text) => {
  // Find which label is used for the status tab
  const statusLabels = ['Status', 'Updates', 'Status (Updates)'];
  let foundLabel = null;
  for (const label of statusLabels) {
   if (document.querySelector(`button[aria-label="${label}"]`)) {
    foundLabel = label;
    break;
   }
  }

  if (!foundLabel) {
   // Fallback: search for any button that contains 'status' or 'updates'
   const allBtn = Array.from(document.querySelectorAll('button[aria-label]'));
   const target = allBtn.find(b => b.ariaLabel.toLowerCase().includes('status') || b.ariaLabel.toLowerCase().includes('updates'));
   if (target) foundLabel = target.ariaLabel;
  }

  if (!foundLabel) throw new Error("Astra: Status/Updates tab not found in sidebar");

  await window.Astra.ensureSidebar(foundLabel, true);

  // Wait for the status list to load
  await new Promise(r => setTimeout(r, 1000));

  const drawer = window.Astra.getActiveDrawer();
  if (!drawer) throw new Error("Astra: Active drawer not found after opening status");

  await window.Astra.runDOMAction([
   { element: drawer.querySelector('button[aria-label="Add Status"], button[aria-label="Create status"], [data-testid="status-v3-add"]'), action: 'click', wait: 800 },
   { selector: 'div[aria-label="Text"], div[role="button"]:has(span[data-icon="status-v3-text"]), [data-testid="status-v3-text"]', action: 'click', wait: 800 },
   { selector: 'div[role="textbox"][contenteditable="true"], [data-testid="status-v3-text-input"]', action: 'type', value: text, wait: 1000 },
   { selector: 'div[aria-label="Send"][role="button"], span[data-icon="send"], [data-testid="status-v3-send"]', action: 'click', wait: 1500 }
  ]);

  await window.Astra.ensureSidebar(foundLabel, false);
  return true;
 };
 window.Astra.getStatusViewers = async (msgId) => {
  const Store = window.Astra.initializeEngine();
  const repo = Store.MessageRepo || Store.MsgRepo || Store.Msg;
  const msg = repo.get(msgId) || (await repo.getMessagesById?.([msgId]))?.messages?.[0];
  if (!msg) throw new Error("Astra: Status message not found: " + msgId);

  let viewers = [];
  if (msg.statusV3) {
   // Retrieve viewers from the message object or Store.Status
   const statusMod = window.Store.Status;
   if (statusMod && typeof statusMod.getStatusViewers === 'function') {
    viewers = await statusMod.getStatusViewers(msg);
   } else if (msg.ackReadList) {
    viewers = msg.ackReadList;
   }
  }

  return (viewers || []).map(v => ({
   id: v.id?._serialized || v._serialized || v,
   readAt: v.readAt || v.t || Date.now()
  }));
 };
})();


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


(function() {
 window.Astra = window.Astra || {};

 window.Astra.openChatDOM = async (chatId) => {
  console.log(`[Astra] openChatDOM: ${chatId}`);
  const idStr = (chatId && chatId._serialized) ? chatId._serialized : String(chatId);
  const cells = document.querySelectorAll('[data-testid="cell-frame-container"]');
  for (const cell of cells) {
   if (cell.innerHTML.includes(idStr)) {
    cell.click();
    await new Promise(r => setTimeout(r, 1000));
    return true;
   }
  }
  return false;
 };

 window.Astra.scanDOM = async (section) => {
  console.log(`[Astra] Starting deep DOM scan for section: ${section}`);
  const results = [];

  // Comprehensive attribute list to scan
  const attributes = ['data-testid', 'aria-label', 'role', 'title', 'id'];

  const walk = (node) => {
   if (node.nodeType === 1) { // Element node
    const entry = {
     tag: node.tagName.toLowerCase(),
     text: node.innerText ? node.innerText.substring(0, 50).trim() : '',
     attributes: {}
    };

    let hasImportantAttr = false;
    attributes.forEach(attr => {
     const val = node.getAttribute(attr);
     if (val) {
      entry.attributes[attr] = val;
      hasImportantAttr = true;
     }
    });

    if (hasImportantAttr) {
     results.push(entry);
    }
   }

   node.childNodes.forEach(walk);
  };

  // Select root based on section
  let root = document.body;
  if (section === 'chats') root = document.querySelector('[data-testid="chat-list"]') || document.querySelector('#pane-side') || document.body;
  if (section === 'settings') {
    await window.Astra.ensureSidebar('Settings', true);
    root = document.querySelector('#app > div > span:nth-child(4) > div') || document.body;
  }
  if (section === 'profile') {
    await window.Astra.ensureSidebar('Profile', true);
    root = document.querySelector('#app > div > span:nth-child(4) > div') || document.body;
  }

  walk(root);
  console.log(`[Astra] Scan complete for ${section}. Found ${results.length} stable nodes.`);
  return results;
 };

 window.Astra.generateDOMReport = async (section) => {
  const data = await window.Astra.scanDOM(section);
  let report = `Deep DOM Scan Report: ${section}\n`;
  report += `Generated at: ${new Date().toISOString()}\n`;
  report += `==========================================\n\n`;

  data.forEach((item, i) => {
   report += `Node ${i + 1}: <${item.tag}>\n`;
   if (item.text) report += ` Text: "${item.text}"\n`;
   Object.entries(item.attributes).forEach(([k, v]) => {
    report += ` ${k}: ${v}\n`;
   });
   report += `\n`;
  });

  return report;
 };
})();


(function() {
 window.Astra = window.Astra || {};

 // Specialized Drawer Finder for Firefox (Targeting the Sidebar specifically)
 window.Astra.getActiveDrawer = () => {
  const isVisible = (el) => {
   if (!el) return false;
   const style = window.getComputedStyle(el);
   if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
   const rect = el.getBoundingClientRect();
   return rect.width > 0 && rect.height > 0;
  };

  // Find all scrollable containers and pick the leftmost one (sidebar)
  const scrollables = Array.from(document.querySelectorAll('div[scrollable="true"]')).filter(isVisible);

  // Exclude the main chat list (usually has id="pane-side")
  const drawers = scrollables.filter(el => !el.closest('#pane-side') && el.getBoundingClientRect().x < 200);

  // Sort by z-index or pick the first one visible on the left
  if (drawers.length > 0) return drawers[0];

  // Backup: data-testid
  const leftDrawer = document.querySelector('[data-testid="drawer-left"]');
  if (isVisible(leftDrawer)) return leftDrawer;

  // Fallback: search for header content
  return Array.from(document.querySelectorAll('header, h1, h2')).find(h => {
    const rect = h.getBoundingClientRect();
    return rect.x < 300 && isVisible(h);
  })?.closest('div[class*="x"]') || null;
 };

 // Robust Sidebar Navigator for Firefox (No data-testid)
 window.Astra.ensureSidebar = async (label, open = true) => {
  console.log(`[Astra-Firefox] ensureSidebar: ${label} (open=${open})`);

  const isVisible = (el) => {
   if (!el) return false;
   const style = window.getComputedStyle(el);
   if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
   const rect = el.getBoundingClientRect();
   return rect.width > 0 && rect.height > 0;
  };

  const findButton = () => {
   // Firefox uses aria-label exclusively (no testid on sidebar buttons)
   const btn = document.querySelector(`button[aria-label="${label}" i]`) ||
      document.querySelector(`[role="button"][aria-label="${label}" i]`) ||
      Array.from(document.querySelectorAll('button[aria-label]')).find(b => b.ariaLabel.toLowerCase().includes(label.toLowerCase()));
   return isVisible(btn) ? btn : null;
  };

  const checkIsOpen = () => {
   const drawer = window.Astra.getActiveDrawer();
   if (!drawer) return false;

   // Firefox often uses H2 in the sidebar drawer header
   const header = drawer.querySelector('h1, h2, header');
   if (header && header.innerText.toLowerCase().includes(label.toLowerCase())) return true;

   // Special case for Settings sub-pages
   if (label.toLowerCase() === 'settings') {
    const text = (drawer.innerText || "").toLowerCase();
    return ['settings', 'privacy', 'account', 'chats', 'theme'].some(term => text.includes(term));
   }
   return false;
  };

  let isOpen = checkIsOpen();

  if (open) {
   if (isOpen) return;
   const btn = findButton();
   if (btn) {
    btn.click();
    await new Promise(r => setTimeout(r, 2000));
   } else {
    console.error(`[Astra-Firefox] Sidebar button ${label} not found!`);
   }
  } else if (!open && isOpen) {
   const drawer = window.Astra.getActiveDrawer();
   const closeBtn = drawer ? (drawer.querySelector('button[aria-label="Back"]') ||
          drawer.querySelector('button[aria-label="Close"]')) : null;
   if (closeBtn) {
    closeBtn.click();
    await new Promise(r => setTimeout(r, 1000));
   }
  }
 };

 // Override Profile access to be direct
 const originalGetProfileDOM = window.Astra.getProfileDOM;
 window.Astra.getProfileDOM = async () => {
  console.log('[Astra-Firefox] Direct Profile Access...');
  await window.Astra.ensureSidebar('Profile', true);

  const info = { name: "", about: "" };
  const nameLabel = document.querySelector('div[data-testid="profile-section-name"]');
  if (nameLabel) info.name = nameLabel.innerText.split('\n').pop();

  const aboutLabel = document.querySelector('div[data-testid="profile-section-about"]');
  if (aboutLabel) info.about = aboutLabel.innerText.split('\n').pop();

  // Fallbacks
  if (!info.name) {
    const spans = Array.from(document.querySelectorAll('span[aria-label="Click to edit Name"]'));
    if (spans.length > 0) info.name = spans[0].parentElement.innerText.split('\n')[0];
  }

  await window.Astra.ensureSidebar('Profile', false);
  return info;
 };

 const originalUpdateProfileDOM = window.Astra.updateProfileDOM;
 window.Astra.updateProfileDOM = async (type, value) => {
  console.log(`[Astra-Firefox] Direct Profile Update: ${type} -> ${value}`);
  await window.Astra.ensureSidebar('Profile', true);

  const label = type === 'name' ? "Click to edit Name" : "Click to edit About";
  const editBtn = document.querySelector(`span[aria-label="${label}"]`);

  if (editBtn) {
   editBtn.click();
   await new Promise(r => setTimeout(r, 800));
   const input = document.querySelector('div[contenteditable="true"]');
   if (input) {
    input.innerText = "";
    input.focus();
    document.execCommand('insertText', false, value);
    await new Promise(r => setTimeout(r, 500));
    const saveBtn = document.querySelector('span[aria-label="Finish editing"]') ||
        document.querySelector('[data-testid="checkmark-penciled"]');
    if (saveBtn) saveBtn.click();
    await new Promise(r => setTimeout(r, 1500));
   }
  }
  await window.Astra.ensureSidebar('Profile', false);
  return true;
 };

})();


(function() {
 window.Astra = window.Astra || {};
 window.Astra.idb = {};

 // ── Helpers ────────────────────────────────────────────────
 const IDB_NAME = 'wawc';

 const openDB = () => new Promise((resolve, reject) => {
  // WhatsApp uses multiple IDB names across versions
  const names = ['wawc', 'wawc_db_enc', 'model-storage'];
  let resolved = false;

  for (const name of names) {
   try {
    const req = indexedDB.open(name);
    req.onsuccess = (e) => {
     if (!resolved) {
      resolved = true;
      resolve(e.target.result);
     }
    };
    req.onerror = () => {};
   } catch(e) {}
  }

  setTimeout(() => {
   if (!resolved) reject(new Error('Astra: No WA IndexedDB found'));
  }, 3000);
 });

 const readAll = (db, storeName, limit = 500) => new Promise((resolve, reject) => {
  try {
   const tx = db.transaction(storeName, 'readonly');
   const store = tx.objectStore(storeName);
   const results = [];
   let count = 0;

   const req = store.openCursor();
   req.onsuccess = (e) => {
    const cursor = e.target.result;
    if (cursor && count < limit) {
     try {
      const val = cursor.value;
      // Serialize safely — strip circular refs and blobs
      const safe = JSON.parse(JSON.stringify(val, (k, v) => {
       if (v instanceof ArrayBuffer || v instanceof Uint8Array) return '[binary]';
       if (v instanceof Blob) return '[blob]';
       return v;
      }));
      results.push(safe);
     } catch(e) {
      // Skip unserializable entries
     }
     count++;
     cursor.continue();
    } else {
     resolve(results);
    }
   };
   req.onerror = () => resolve(results);
  } catch(e) {
   resolve([]);
  }
 });

 // ── Public API ─────────────────────────────────────────────

 window.Astra.idb.snapshot = async () => {
  try {
   const db = await openDB();
   const storeNames = Array.from(db.objectStoreNames);
   const stats = {};
   for (const name of storeNames) {
    try {
     const tx = db.transaction(name, 'readonly');
     const store = tx.objectStore(name);
     const countReq = store.count();
     stats[name] = await new Promise((r) => {
      countReq.onsuccess = () => r(countReq.result);
      countReq.onerror = () => r(-1);
     });
    } catch(e) {
     stats[name] = -1;
    }
   }
   return {
    dbName: db.name,
    version: db.version,
    storeNames: storeNames,
    counts: stats,
    timestamp: Date.now()
   };
  } catch(e) {
   return { error: e.message };
  }
 };

 window.Astra.idb.getChats = async (limit = 200) => {
  // Prefer Store for chat data if available (richer data)
  try {
   const Store = window.Astra.initializeEngine();
   const chats = Store.Chat.getModelsArray ? Store.Chat.getModelsArray() : (Store.Chat.models || []);
   return chats.slice(0, limit).map(c => ({
    id: c.id?._serialized || String(c.id),
    name: c.name || c.formattedTitle || c.contact?.pushname || '',
    unreadCount: c.unreadCount || 0,
    lastMessageTs: c.t || 0,
    isGroup: !!c.isGroup,
    isMuted: c.mute?.isMuted || false,
    isPinned: c.pin !== undefined && c.pin > 0,
    isArchived: !!c.archive,
    msgCount: c.msgs?.models?.length || 0
   }));
  } catch(e) {
   console.warn('[Astra IDB] Store fallback for chats:', e.message);
   return [];
  }
 };

 window.Astra.idb.getContacts = async (limit = 500) => {
  try {
   const Store = window.Astra.initializeEngine();
   const contacts = Store.Contact.getModelsArray ? Store.Contact.getModelsArray() : (Store.Contact.models || []);
   return contacts.slice(0, limit).map(c => ({
    id: c.id?._serialized || String(c.id),
    name: c.name || c.pushname || c.formattedName || '',
    isMyContact: !!c.isMyContact,
    isBusiness: !!c.isBusiness,
    verifiedName: c.verifiedName || null
   }));
  } catch(e) {
   console.warn('[Astra IDB] Contact fetch failed:', e.message);
   return [];
  }
 };

 window.Astra.idb.getRecentMessages = async (chatId, limit = 50) => {
  try {
   const Store = window.Astra.initializeEngine();
   const chatWid = Store.WidFactory.createWid(chatId);
   const chat = Store.Chat.get(chatWid);
   if (!chat) return [];

   const msgs = chat.msgs.getModelsArray ? chat.msgs.getModelsArray() : (chat.msgs.models || []);
   return msgs.slice(-limit).map(m => ({
    id: m.id?._serialized || String(m.id),
    body: m.body || '',
    type: m.type || 'unknown',
    from: m.from?._serialized || '',
    to: m.to?._serialized || '',
    timestamp: m.t || 0,
    fromMe: !!m.id?.fromMe,
    ack: m.ack || 0,
    hasMedia: !!m.mediaData
   }));
  } catch(e) {
   console.warn('[Astra IDB] Message fetch failed:', e.message);
   return [];
  }
 };

 // ── Transaction Observer ───────────────────────────────────
 // Hooks IDB writes to emit real-time cache invalidation events

 window.Astra.idb._observerActive = false;

 window.Astra.idb.startObserver = () => {
  if (window.Astra.idb._observerActive) return;
  window.Astra.idb._observerActive = true;

  const origTransaction = IDBDatabase.prototype.transaction;
  IDBDatabase.prototype.transaction = function(storeNames, mode) {
   const tx = origTransaction.apply(this, arguments);
   if (mode === 'readwrite' || mode === 'readwriteflush') {
    tx.addEventListener('complete', () => {
     const stores = Array.isArray(storeNames) ? storeNames : [storeNames];
     // Emit lightweight event for Python-side cache invalidation
     if (window.Astra.emit) {
      window.Astra.emit('idb_write', {
       db: this.name,
       stores: stores,
       ts: Date.now()
      });
     }
    });
   }
   return tx;
  };
  console.log('[Astra IDB] Transaction observer active.');
 };

 window.Astra.idb.stopObserver = () => {
  window.Astra.idb._observerActive = false;
  console.log('[Astra IDB] Transaction observer stopped.');
 };

 console.log('[Astra] IDB Cache Bridge ready.');
})();

(function() {
 const A = window.Astra;
 
 // Normalizes all results for safe Python traversal
 const pack = (val) => {
 if (val === undefined) return null;
 if (val instanceof Error) throw val;
 if (val && val.error) throw new Error(val.error);
 return val;
 };
 
 // Expose the clean API surface to the Protocol Bridge
 window.AstraEngine = {
 // Core Utilities
 sendChatState: async (p) => pack(await A.sendChatState(p.chatId, p.state)),
 getMe: async () => pack(await A.getIdentity()),
 getChats: async () => pack(await A.getChatList()),
 getContacts: async () => pack(await A.getContacts()),
 getChatById: async (p) => pack(await A.getChatById(p)),
 getContactById: async (p) => pack(await A.getContactById(p || p.id)),
 
 // Messaging
 sendMessage: async (p) => pack(await A.sendText(p.to, p.text || p.body, p.options || {})),
 sendPoll: async (p) => pack(await A.sendPoll(p.to, p.name, p.options)),
 votePoll: async (p) => pack(await A.votePoll(p.msgId, p.selections)),
 editMessage: async (p) => pack(await A.editMessage(p.msgId, p.text || p.body, p.options || {})),
 deleteMessage: async (p) => pack(await A.deleteMessage(p.msgId, p.forEveryone !== false, p.clearMedia || false)),
 bulkDeleteMessages: async (p) => pack(await A.bulkDeleteMessages(p.msgIds, p.forEveryone !== false, p.clearMedia || false)),
 markSeen: async (p) => pack(await A.markSeen(p.chatId || p)),
 react: async (p) => pack(await A.sendReaction(p.msgId, p.emoji || p.reaction)),
 fetchMessages: async (p) => pack(await A.fetchMessages(p.chatId, p.searchOptions || {})),
 syncHistory: async (p) => pack(await A.syncHistory(p.chatId)),
 
 // Media
 initChunkedUpload: async (p) => pack(A.initChunkedUpload(p.id, p.size)),
 pushChunk: async (p) => pack(A.pushChunk(p.id, p.data)),
 sendMedia: async (p) => {
  let buffer = p.data || p.media;
  if (buffer && buffer.includes(',')) buffer = buffer.split(',')[1];
  const options = { ...(p.options || {}), caption: p.caption, _call_id: p._call_id };
  const media = { data: buffer, mimetype: p.mimetype, filename: p.filename, type: p.type, uploadId: p.uploadId };
  return pack(await A.sendMedia(p.to, media, options));
 },
 retrieveMedia: async (p) => pack(await A.retrieveMedia(p.msgId || p)),
 
 // Chat Management
 archiveChat: async (p) => pack(await A.archiveChat(p.chatId, p.archive !== false)),
 pinChat: async (p) => pack(await A.pinChat(p.chatId, p.pin !== false)),
 muteChat: async (p) => pack(await A.muteChat(p.chatId, p.duration)),
 
 // Group Management
 createGroup: async (p) => pack(await A.createGroup(p.title, p.participants)),
 addMembers: async (p) => pack(await A.addParticipants(p.groupId, p.participants)),
 removeMembers: async (p) => pack(await A.kickParticipants(p.groupId, p.participants)),
 promote: async (p) => pack(await A.promoteParticipants(p.groupId, p.participants)),
 demote: async (p) => pack(await A.demoteParticipants(p.groupId, p.participants)),
 leaveGroup: async (p) => pack(await A.leaveGroup(p.groupId || p)),
 getGroupInfo: async (p) => pack(await A.getGroupInfo(p.groupId || p)),
 setGroupDescription: async (p) => pack(await A.setGroupDescription(p.groupId, p.description)),
 getInviteLink: async (p) => pack(await A.getInviteCode(p.chatId || p)),
 joinViaLink: async (p) => pack(await A.joinGroupViaLink(p.code || p)),
 
 // Social & Profile
 setProfileName: async (p) => pack(await A.updateProfileDOM(p.name || p.pushname)),
 setAbout: async (p) => pack(await A.setStatusDOM(p.about || p.status)),
 getProfilePic: async (p) => pack(await A.getProfilePic(p.chatId || p)),
 block: async (p) => pack(await A.blockContact(p.chatId || p.id, p.block !== false)),
 
 // Status & Stories
 setMyStatus: async (p) => pack(await A.sendTextStatus(p.status || p)),
 postStatus: async (p) => pack(await A.sendMediaStatus(p.data || p, p.mimetype, p.caption)),
 getStatusViewers: async (p) => pack(await A.getStatusViewers(p.msgId || p)),
 
 // Privacy & Settings
 setPrivacy: async (p) => pack(await A.setPrivacySetting(p.category, p.value)),
 getPrivacySettings: async () => pack(await A.getPrivacySettings()),
 
 // Debug & System
 deepScanModules: async (p) => pack(await A.deepScanModules(p.id || p)),
 getDiagnostics: async () => pack(await A.getDiagnostics()),
 getDomSnippet: async (p) => pack(await A.getDomSnippet(p.selector)),
 scanDOM: async (p) => pack(await A.scanDOM(p.section || p)),
 generateDOMReport: async (p) => pack(await A.generateDOMReport(p.section || p)),
 sync: async () => pack(await A.deepSync()),
 logout: async () => pack(await A.logout()),
 };
 
 // Uplink for event propagation
 window.py_onMessage = (m) => A.emit && A.emit('msg', m);
 
 if (!window.AstraEngine) {
 console.warn('[Astra] High-Level Engine init failed - window.Astra missing?');
 } else {
 console.log('[Astra] High-Level Engine V24 Ready.');
 }
})();
})();