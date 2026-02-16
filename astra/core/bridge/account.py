# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

ACCOUNT_CODE = r"""
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
       'User';

   return { id: serializedId, pushname: pushname, isMyContact: true };
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
"""
