# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

CORE_SCRIPT = r"""

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
    s.subtype = msg.subtype;
    s.recipients = (msg.recipients || msg.participants || []).map(r => serializeWid(r));

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
  window.Astra.serializeWid = (wid) => {
    if (!wid) return null;
    if (typeof wid === 'string') return wid;
    const get = (o) => (o && typeof o === 'object') ? (o._serialized || o.serialized || (o.id ? (typeof o.id === 'string' ? o.id : o.id._serialized) : null)) : o;
    let id = get(wid);
    if (typeof id === 'string') return id;
    if (wid.user && wid.server) return `${wid.user}@${wid.server}`;
    return (wid.toString && wid.toString() !== '[object Object]') ? wid.toString() : String(wid);
  };

  window.Astra.createWid = (input) => {
    try {
      if (!input) return null;
      if (typeof input === 'object' && input._serialized && typeof input._serialized === 'string') return input;

      let serialized = typeof input === 'string' ? input : (input._serialized || input.serialized || (input.id && (input.id._serialized || input.id)));
      if (!serialized || typeof serialized !== 'string' || serialized === '[object Object]') {
          if (input.user && input.server) serialized = `${input.user}@${input.server}`;
          else if (input.toString && input.toString() !== '[object Object]') serialized = input.toString();
          else return null;
      }

      const Store = window.Astra.initializeEngine();
      const wf = Store.WidFactory || Store.AddressFactory;

      if (wf && typeof wf.createWid === 'function') {
        try {
          return wf.createWid(serialized);
        } catch (e) {
          console.warn('[Astra] WidFactory.createWid failed for:', serialized);
        }
      }

      // Hard fallback for basic Wid structure
      const parts = serialized.split('@');
      return { 
        user: parts[0], 
        server: parts[1] || (serialized.includes('lid') ? 'lid' : 'c.us'), 
        _serialized: serialized,
        isLid: () => serialized.includes('@lid'),
        isGroup: () => serialized.includes('@g.us'),
        isUser: () => serialized.includes('@c.us') || serialized.includes('@lid') || serialized.includes('@s.whatsapp.net')
      };
    } catch (e) {
      console.error('[Astra] createWid failed:', e.message);
      return null;
    }
  };

  window.Astra.getChat = async (wid, force = false) => {
    try {
      const Store = window.Astra.initializeEngine();
      // Ensure we always have a string ID before trying to create a Wid
      let chatId = '';
      if (typeof wid === 'string') chatId = wid;
      else if (wid && typeof wid === 'object') {
          chatId = wid._serialized || wid.serialized || (wid.id && wid.id._serialized) || String(wid);
      } else {
          chatId = String(wid);
      }
      
      let chatWid = window.Astra.createWid(chatId);
      
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
          if (!anchorMsg) {
            const shortId = String(anchorId).split('_').pop();
            anchorMsg = getLocalArray().find(m => m.id && (m.id._serialized === anchorId || m.id.id === anchorId || m.id.id === shortId));
          }

          if (anchorMsg) {
            const all = getLocalArray().filter(isValidMsg);
            all.sort((a, b) => a.t - b.t);
            const shortId = String(anchorId).split('_').pop();
            const idx = all.findIndex(m => m.id && (m.id._serialized === anchorId || m.id.id === anchorId || m.id.id === shortId));
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
          
          window.Astra.log(`Strategy 2 found ${found.length} results before filtering.`);

          let filtered = found.filter(isValidMsg);
          if (anchorId && !includeAnchor) {
            const shortId = String(anchorId).split('_').pop();
            filtered = filtered.filter(m => !(m.id && (m.id._serialized === anchorId || m.id.id === anchorId || m.id.id === shortId)));
          }
          window.Astra.log(`Strategy 2 final count: ${filtered.length}`);
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
      ProfilePicThumb: 'WAWebContactProfilePicThumbBridge',
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
      window.Store.AccountUtils = window.Store.PushnameAction || window.Store.AccountUtils;

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
        'UploadUtils': 'WAWebUploadManager',
        'PushnameAction': 'WAWebSetPushnameConnAction',
        'StatusV3Action': 'WAWebStatusV3Action'
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
        ProfilePicThumb: (m) => m.requestProfilePicFromServer || (m.default && m.default.requestProfilePicFromServer),
        StatusV3Action: (m) => m && (m.postStatusV3 || m.sendStatusV3 || m.postStatus || m.sendTextStatus || (typeof m === 'object' && Object.values(m).some(v => v && (v.postStatusV3 || v.postStatus || v.sendTextStatus)))),
        StatusUtils: (m) => m && (m.postStatusV3 || m.sendStatusV3 || m.setMyStatus || m.postStatus || m.sendTextStatus || (typeof m === 'object' && Object.values(m).some(v => v && (v.postStatusV3 || v.postStatus || v.sendTextStatus)))),
        Settings: (m) => m && (m.setPushname || (m.Conn && m.Conn.pushname) || (typeof m === 'object' && Object.values(m).some(v => v && v.setPushname))),
        PrivacySettings: (m) => m && (m.setPrivacyLastSeen || m.getPrivacyLastSeen || m.getPrivacyAbout || (typeof m === 'object' && Object.values(m).some(v => v && (v.setPrivacyLastSeen || v.setPrivacyAbout)))),
        Polls: (m) => m && (m.sendCreatePollMsgs || m.createPollMsg || m.postPoll || m.sendPoll || (typeof m === 'object' && Object.values(m).some(v => v && (v.sendCreatePollMsgs || v.sendPoll)))),
        BlockAction: (m) => m && (m.blockContact || m.blockUser) && (m.unblockContact || m.unblockUser),
        AccountUtils: (m) => m && (m.setPushname || m.setAbout || m.setMyStatus),
        GroupInvite: (m) => m && (m.sendGetGroupInviteCode || m.queryGroupInviteCode || m.fetchGroupInviteCode || m.queryGroupInvite || m.getGroupInviteCode),
        GroupInviteV4: (m) => m && (m.queryGroupInviteV4 || m.sendGroupInviteMessage),
        WAGroupInviteQuery: (m) => m && (m.fetchMexGroupInviteCode || m.queryGroupInviteCode),
        GroupParticipants: (m) => m && m.addParticipants && m.promoteParticipants && m.removeParticipants,
        GroupUtils: (m) => m && (m.sendSetPicture || (m.setGroupSubject && m.setGroupDescription) || (m.sendSetPicture && m.requestDeletePicture) || (m.sendExitGroup && m.setGroupSubject))
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

"""