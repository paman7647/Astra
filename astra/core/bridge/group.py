# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

GROUP_CODE = r"""
(function() {
 window.Astra = window.Astra || {};

 const getWid = (id, Store) => Store.AddressFactory.createWid(id);
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
   const w = getWid(p, Store);
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
"""
