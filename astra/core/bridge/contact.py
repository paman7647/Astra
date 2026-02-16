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

 window.Astra.getContactById = function(id) {
  const Store = window.Astra.initializeEngine();
  if (!Store.ContactRepo) return null;
  const contact = Store.ContactRepo.get(id);
  return contact ? window.Astra.serializeContact(contact) : null;
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
"""
