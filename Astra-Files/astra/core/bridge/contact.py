# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

CONTACT_CODE = r"""
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


  window.Astra.getNumberId = async function(id) {
    const Store = window.Astra.initializeEngine();
    const wid = window.Astra.createWid(id);
    if (!wid) return null;
    if (Store.QueryExist) {
        try {
            const result = await Store.QueryExist(wid);
            if (result && result.wid && result.wid._serialized) return { _serialized: result.wid._serialized };
        } catch(e) { }
    }
    try {
        const engineRaid = window.Astra.mR;
        if (engineRaid && engineRaid.findModule) {
            const checkMod = engineRaid.findModule(m => m && m.queryExists);
            if (checkMod) {
                const res = await checkMod.queryExists(wid);
                if (res && res.wid) return { _serialized: res.wid._serialized };
            }
        }
    } catch(e) {}
    return null;
  };

    window.Astra.getProfilePicUrl = async function(rawId) {
    console.log(`[Astra] getProfilePicUrl start for: ${typeof rawId === 'object' ? JSON.stringify(rawId) : rawId}`);
    const Store = window.Astra.initializeEngine();
    const chatWid = window.Astra.createWid(rawId);
    if (!chatWid) {
      console.warn('[Astra] getProfilePicUrl: createWid returned null');
      return null;
    }
    console.log(`[Astra] getProfilePicUrl resolved Wid: ${chatWid._serialized}`);

    const extractUrl = (obj, source = 'unknown') => {
      if (!obj) return null;
      if (typeof obj === 'string') return obj.includes('http') ? obj : null;
      
      const url = obj.eurl || obj.img || obj.url || (obj.profilePicThumb ? (obj.profilePicThumb.eurl || obj.profilePicThumb.img) : null);
      if (typeof url === 'string') {
        console.log(`[Astra] getProfilePicUrl: Found asset via ${source} (Prop match)`);
        return url;
      }

      try {
        if (typeof obj === 'object') {
          for (const key in obj) {
            if (typeof obj[key] === 'string' && obj[key].startsWith('http')) {
               console.log(`[Astra] getProfilePicUrl: Found asset via ${source} (Scan: ${key})`);
               return obj[key];
            }
            if (obj[key] && typeof obj[key] === 'object' && key !== 'id' && key !== 'contact') {
              const nested = extractUrl(obj[key], `${source}.${key}`);
              if (nested) return nested;
            }
          }
        }
      } catch (e) {}
      return null;
    };

    try {
      const ppModules = [Store.ProfilePic, Store.ProfilePicRepo].filter(Boolean);
      console.log(`[Astra] PFP Modules available: ${ppModules.length}`);
      
      for (let i = 0; i < ppModules.length; i++) {
        const pp = ppModules[i];
        const modName = i === 0 ? 'ProfilePic' : 'ProfilePicRepo';
        
        if (typeof pp.profilePicRes === 'function') {
          try {
            const res = await pp.profilePicRes(chatWid);
            const url = extractUrl(res, `${modName}.profilePicRes`);
            if (url) return url;
          } catch (e) { console.debug(`[Astra] ${modName}.profilePicRes error:`, e.message); }
        }
        if (typeof pp.profilePicFind === 'function') {
          try {
            const res = await pp.profilePicFind(chatWid);
            const url = extractUrl(res, `${modName}.profilePicFind`);
            if (url) return url;
          } catch (e) { console.debug(`[Astra] ${modName}.profilePicFind error:`, e.message); }
        }
        if (typeof pp.requestProfilePicFromServer === 'function') {
          try {
            const res = await pp.requestProfilePicFromServer(chatWid);
            const url = extractUrl(res, `${modName}.requestProfilePicFromServer`);
            if (url) return url;
          } catch (e) { console.debug(`[Astra] ${modName}.requestProfilePicFromServer error:`, e.message); }
        }
      }

      // Method D: Repository fallbacks
      console.log('[Astra] Falling back to Contact/Chat Repo scans...');
      const contact = Store.ContactRepo ? Store.ContactRepo.get(chatWid) : null;
      const contactUrl = extractUrl(contact, 'ContactRepo');
      if (contactUrl) return contactUrl;

      const chat = Store.Chat ? Store.Chat.get(chatWid) : null;
      if (chat && chat.contact) {
        const chatUrl = extractUrl(chat.contact, 'Chat.contact');
        if (chatUrl) return chatUrl;
      }

      console.warn('[Astra] getProfilePicUrl: All methods exhausted, asset inaccessible.');
      return null;
    } catch (e) {
      console.error("Astra: getProfilePicUrl failed", e);
      return null;
    }
  };

  window.Astra.getCommonGroups = async function(id) {
    const Store = window.Astra.initializeEngine();
    const wid = window.Astra.createWid(id);
    if (!wid) return [];
    try {
        if (Store.GroupUtils && typeof Store.GroupUtils.getCommonGroups === 'function') {
            const groups = await Store.GroupUtils.getCommonGroups(wid);
            return groups.map(g => typeof g === 'string' ? g : (g._serialized || g.id));
        }
        const CommonMod = window.require && (window.require('WAWebFindCommonGroupsApi') || window.require('WAWebCommonGroups'));
        if (CommonMod && typeof CommonMod.findCommonGroups === 'function') {
            const groups = await CommonMod.findCommonGroups(wid);
            return groups.map(g => typeof g === 'string' ? g : (g._serialized || g.id));
        }
        const engineRaid = window.Astra.mR;
        if (engineRaid && engineRaid.findModule) {
            const raidMod = engineRaid.findModule(m => m && typeof m.getCommonGroups === 'function');
            if (raidMod) {
                const groups = await raidMod.getCommonGroups(wid);
                return groups.map(g => typeof g === 'string' ? g : (g._serialized || g.id));
            }
            const raidMod2 = engineRaid.findModule(m => m && typeof m.findCommonGroups === 'function');
            if (raidMod2) {
                const groups = await raidMod2.findCommonGroups(wid);
                return groups.map(g => typeof g === 'string' ? g : (g._serialized || g.id));
            }
        }
    } catch(e) { }
    return [];
  };

})();
"""
