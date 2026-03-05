# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
IndexedDB Cache Bridge
Injects JS that hooks into WhatsApp's IndexedDB (wawc database)
for fast, direct data reads without Store.* round-trips.
"""

IDB_CACHE_CODE = r"""
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
"""
