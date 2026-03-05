# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

GROUP_CODE = r"""
(function() {
 window.Astra = window.Astra || {};

 const getWid = (id, Store) => window.Astra.createWid(id);
 const getChat = async (id, Store) => await window.Astra.getChat(getWid(id, Store));

   const mutateParticipants = async function(chat, participants, funcName) {
    const Store = window.Astra.initializeEngine();
    const pids = participants.map(p => getWid(p, Store)).filter(Boolean);
    if (pids.length === 0) throw new Error("No valid participants found");

    // Live Participant objects from GroupMetadata (Critical for recent WA versions)
    const liveParticipants = pids.map(wid => {
      try {
        return chat.groupMetadata?.participants?.get(wid) || chat.groupMetadata?.participants?.get(wid._serialized) || null;
      } catch(e) { return null; }
    }).filter(Boolean);

    const strategies = [
      { name: "Chat, Participant Objects", data: [chat, liveParticipants] },
      { name: "Chat, Wid Array", data: [chat, pids] },
      { name: "Chat, Serialized Array", data: [chat, pids.map(w => w._serialized || w.id || w)] },
      { name: "Chat, Object Array {id: Wid}", data: [chat, pids.map(w => ({ id: w }))] },
      { name: "ChatWid, Wid Array", data: [chat.id || chat, pids] },
      { name: "Wid Array Only", data: [pids] }
    ];

    let lastError;
    // Try both GroupParticipants AND GroupUtils as some methods migrate
    const providers = [
      { name: 'GroupParticipants', module: Store.GroupParticipants },
      { name: 'GroupUtils', module: Store.GroupUtils }
    ].filter(p => !!p.module);

    for (const provider of providers) {
      const gFunc = provider.module[funcName];
      if (!gFunc) continue;

      for (const strategy of strategies) {
        if (strategy.data[1] && Array.isArray(strategy.data[1]) && strategy.data[1].length === 0 && strategy.name.includes("Participant")) {
          // Skip if we couldn't find any live participants for that strategy
          continue;
        }
        try {
          console.log(`[Astra] [${funcName}] Provider: ${provider.name}, Strategy: ${strategy.name}`);
          
          // CRITICAL: Must use .apply() for module methods to preserve 'this'
          const result = await gFunc.apply(provider.module, strategy.data);
          
          console.log(`[Astra] [${funcName}] Success with ${provider.name} / ${strategy.name}`);
          return result === undefined ? true : result;
        } catch (e) {
          console.warn(`[Astra] [${funcName}] ${provider.name} / ${strategy.name} failed: ${e.message}`);
          if (e.stack && !e.message.includes("not found")) console.warn(e.stack);
          lastError = e;
          // Don't retry if it's a permission/logic error
          if (e.message.includes("not an admin") || e.message.includes("Group not found")) throw e;
        }
      }
    }

    // Last ditch for add: sendAddParticipantsRPC
    if (funcName === 'addParticipants' && Store.GroupParticipants.sendAddParticipantsRPC) {
      try {
        console.log(`[Astra] Attempting addParticipants with sendAddParticipantsRPC...`);
        return await Store.GroupParticipants.sendAddParticipantsRPC(chat, pids);
      } catch (e) {
        lastError = e;
      }
    }

    throw lastError || new Error(`${funcName} failed after all strategies`);
  };

  window.Astra.kickParticipants = async function(groupId, participants) {
    const chat = await getChat(groupId, window.Astra.initializeEngine());
    if (!chat) throw new Error("Group not found");
    return await mutateParticipants(chat, participants, 'removeParticipants');
  };

  window.Astra.addParticipants = async function(groupId, participants) {
    const chat = await getChat(groupId, window.Astra.initializeEngine());
    if (!chat) throw new Error("Group not found");
    return await mutateParticipants(chat, participants, 'addParticipants');
  };

  window.Astra.promoteParticipants = async function(groupId, participants) {
    const chat = await getChat(groupId, window.Astra.initializeEngine());
    if (!chat) throw new Error("Group not found");
    return await mutateParticipants(chat, participants, 'promoteParticipants');
  };

  window.Astra.demoteParticipants = async function(groupId, participants) {
    const chat = await getChat(groupId, window.Astra.initializeEngine());
    if (!chat) throw new Error("Group not found");
    return await mutateParticipants(chat, participants, 'demoteParticipants');
  };

 window.Astra.setGroupSubject = async function(groupId, subject) {
  const Store = window.Astra.initializeEngine();
  const chatWid = getWid(groupId, Store);

  // Strategy 1: Store.GroupUtils
  if (Store.GroupUtils && typeof Store.GroupUtils.setGroupSubject === 'function') {
   await Store.GroupUtils.setGroupSubject(chatWid, subject);
   return true;
  }

  // Strategy 2: Runtime scan
  const engineRaid = window.Astra.mR;
  if (engineRaid && engineRaid.findModule) {
   const mod = engineRaid.findModule(m => m && typeof m.setGroupSubject === 'function');
   if (mod) {
    await mod.setGroupSubject(chatWid, subject);
    return true;
   }
  }

  throw new Error('setGroupSubject not found in any module');
 };

 window.Astra.setGroupDescription = async function(groupId, description) {
  const Store = window.Astra.initializeEngine();
  const chat = await getChat(groupId, Store);
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

  // Strategy 3: Runtime scan
  const engineRaid = window.Astra.mR;
  if (engineRaid && engineRaid.findModule) {
   const mod = engineRaid.findModule(m => m && typeof m.setGroupDescription === 'function');
   if (mod) {
    await mod.setGroupDescription(chatWid, description, newId, descId);
    return true;
   }
  }

  throw new Error('setGroupDescription not available');
 };

 window.Astra.leaveGroup = async function(groupId) {
  const Store = window.Astra.initializeEngine();
  const chat = await getChat(groupId, Store);
  if (!chat) throw new Error("Chat not found: " + groupId);

  // Strategy 1: Store.GroupUtils.sendExitGroup
  if (Store.GroupUtils && typeof Store.GroupUtils.sendExitGroup === 'function') {
   await Store.GroupUtils.sendExitGroup(chat);
   return true;
  }

  // Strategy 2: window.Store fallback
  if (window.Store && window.Store.GroupUtils && typeof window.Store.GroupUtils.sendExitGroup === 'function') {
   await window.Store.GroupUtils.sendExitGroup(chat);
   return true;
  }

  // Strategy 3: Runtime scan
  const engineRaid = window.Astra.mR;
  if (engineRaid && engineRaid.findModule) {
   const mod = engineRaid.findModule(m => m && typeof m.sendExitGroup === 'function');
   if (mod) {
    await mod.sendExitGroup(chat);
    return true;
   }
  }

  throw new Error("sendExitGroup not available in any module");
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
  const InviteStore = Store.WAGroupInviteQuery || Store.WAGroupInvite || (window.Store && window.Store.GroupInvite) || Store.WAGroupInviteV4 || (window.Store && window.Store.GroupInviteV4) || Store.WAGroupQuery || Store.GroupInviteService;

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
    } else if (InviteStore.getGroupInviteCode) {
     const res = await InviteStore.getGroupInviteCode(chatWid);
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

   // Strategy 1: Store.GroupUtils.sendSetPicture
   if (Store.GroupUtils && typeof Store.GroupUtils.sendSetPicture === 'function') {
    await Store.GroupUtils.sendSetPicture(chatWid, thumb, picture);
    return true;
   }

   // Strategy 2: Runtime scan
   try {
     const engineRaid = window.Astra.mR;
     if (engineRaid && engineRaid.findModule) {
       const picModule = engineRaid.findModule(m => m && typeof m.sendSetPicture === 'function');
       if (picModule) {
         await picModule.sendSetPicture(chatWid, thumb, picture);
         return true;
       }
     }
   } catch (e) {
     console.warn('[Astra] Runtime scan for sendSetPicture failed:', e.message);
   }

   // Strategy 3: ProfilePicRepo.setPicture
   if (Store.ProfilePicRepo && typeof Store.ProfilePicRepo.setPicture === 'function') {
     await Store.ProfilePicRepo.setPicture(chatWid, thumb, picture);
     return true;
   }

   throw new Error("sendSetPicture not found in any module");
 };

 window.Astra.deleteGroupPicture = async function(groupId) {
   const Store = window.Astra.initializeEngine();
   const chatWid = getWid(groupId, Store);

   // Strategy 1: Store.GroupUtils.requestDeletePicture
   if (Store.GroupUtils && typeof Store.GroupUtils.requestDeletePicture === 'function') {
    await Store.GroupUtils.requestDeletePicture(chatWid);
    return true;
   }

   // Strategy 2: Runtime scan
   try {
     const engineRaid = window.Astra.mR;
     if (engineRaid && engineRaid.findModule) {
       const picModule = engineRaid.findModule(m => m && typeof m.requestDeletePicture === 'function');
       if (picModule) {
         await picModule.requestDeletePicture(chatWid);
         return true;
       }
     }
   } catch (e) {
     console.warn('[Astra] Runtime scan for requestDeletePicture failed:', e.message);
   }

   throw new Error("requestDeletePicture not found in any module");
 };

 window.Astra.getGroupInfo = async function(groupId) {
  const Store = window.Astra.initializeEngine();
  const chatWid = getWid(groupId, Store);
  let c = await getChat(groupId, Store) || (Store.ChatRepo && Store.ChatRepo.get(chatWid));

  if (!c) {
   // Wait for chat to appear (race condition after creation)
   for (let i = 0; i < 5; i++) {
    await new Promise(r => setTimeout(r, 500));
    c = await getChat(groupId, Store) || (Store.ChatRepo && Store.ChatRepo.get(chatWid));
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
