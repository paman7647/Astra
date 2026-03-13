# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

GROUP_CODE = r"""
(function() {
 window.Astra = window.Astra || {};

  const getWid = (id, Store) => window.Astra.createWid(id);
  const getChat = async (id, Store) => await window.Astra.getChat(getWid(id, Store));

  // LID/PN Resolution (ported from newwp/src/util/Injected/Utils.js)
  const enforceLidAndPnRetrieval = async (participantId) => {
    try {
      const Store = window.Astra.initializeEngine();
      const wid = window.Astra.createWid(participantId);
      if (!wid) return { lid: null, phone: null };
      const ApiContact = window.require && window.require('WAWebApiContact');
      if (ApiContact && typeof ApiContact.getPhoneNumber === 'function') {
        const phone = wid.server === 'lid' ? ApiContact.getPhoneNumber(wid) : wid;
        return { lid: wid, phone };
      }
      return { lid: wid, phone: wid };
    } catch (e) {
      console.warn('[Astra] enforceLidAndPnRetrieval failed:', e.message);
      return { lid: null, phone: null };
    }
  };
  window.Astra.enforceLidAndPnRetrieval = enforceLidAndPnRetrieval;

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

  window.Astra.createGroup = async function(groupId, participants) {
   return await window.Astra.withLock(async () => {
   const Store = window.Astra.initializeEngine();
  const pids = participants.map(p => {
    const w = window.Astra.createWid(p);
    if (!w) return null;
    return { phoneNumber: w, lid: w };
   }).filter(w => !!w);

   const meta = {
    'title': groupId,
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
   }); // end withLock
  };

 window.Astra.getInviteCode = async function(groupId) {
  const Store = window.Astra.initializeEngine();
  const chatWid = getWid(groupId, Store);

   // Prioritize Store.MexGroupInvite (mapped from WAWebMexFetchGroupInviteCodeJob in base.py)
   const MexInvite = Store.MexGroupInvite;
   if (MexInvite && typeof MexInvite.fetchMexGroupInviteCode === 'function') {
    console.log('[Astra] Using MexGroupInvite.fetchMexGroupInviteCode');
    const res = await MexInvite.fetchMexGroupInviteCode(groupId);
    return res?.code || res;
   }

   // Legacy fallback chain
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
  window.Astra.updateGroupPic = async function(groupId, data) {
    return await window.Astra.withLock(async () => {
    const Store = window.Astra.initializeEngine();
    const chatWid = getWid(groupId, Store);
    
    console.log('[Astra] updateGroupPic: Resizing and setting group PFP...');
    const media = { data, mimetype: 'image/jpeg' };
    const thumb = await window.Astra.cropAndResizeImage(media, { size: 96, asDataUrl: true });
    const full = await window.Astra.cropAndResizeImage(media, { size: 640, asDataUrl: true });

    // Strategy 1: Store.GroupUtils.sendSetPicture
    if (Store.GroupUtils && typeof Store.GroupUtils.sendSetPicture === 'function') {
     await Store.GroupUtils.sendSetPicture(chatWid, thumb, full);
     return true;
    }

   // Strategy 2: Runtime scan
   try {
     const engineRaid = window.Astra.mR;
     if (engineRaid && engineRaid.findModule) {
       const picModule = engineRaid.findModule(m => m && typeof m.sendSetPicture === 'function');
        if (picModule) {
          await picModule.sendSetPicture(chatWid, thumb, full);
          return true;
        }
     }
   } catch (e) {
     console.warn('[Astra] Runtime scan for sendSetPicture failed:', e.message);
   }

   // Strategy 3: ProfilePicRepo.setPicture
    if (Store.ProfilePicRepo && typeof Store.ProfilePicRepo.setPicture === 'function') {
      await Store.ProfilePicRepo.setPicture(chatWid, thumb, full);
      return true;
    }
 
    throw new Error("sendSetPicture not found in any module");
    }); // end withLock
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

 // ─── NEW FEATURES: Group Settings ───────────────────────────
 /**
  * Set group property (admins-only add members, messages, info edit)
  * Properties: 'member_add_mode' (0=admins, 1=all), 'announcement' (1=admins, 0=all), 'restrict' (1=admins, 0=all)
  */
 window.Astra.setGroupProperty = async function(groupId, property, value) {
  const Store = window.Astra.initializeEngine();

  // Strategy 1: Store.GroupUtils.setGroupProperty
  if (Store.GroupUtils && typeof Store.GroupUtils.setGroupProperty === 'function') {
   try {
    const chat = await getChat(groupId, Store);
    await Store.GroupUtils.setGroupProperty(chat, property, value);
    return true;
   } catch(e) { console.warn('[Astra] Store.GroupUtils.setGroupProperty failed:', e.message); }
  }

  // Strategy 2: window.require('WAWebSetPropertyGroupAction')
  try {
   const chat = await getChat(groupId, Store);
   const SetPropMod = window.require && window.require('WAWebSetPropertyGroupAction');
   if (SetPropMod && typeof SetPropMod.setGroupProperty === 'function') {
    await SetPropMod.setGroupProperty(chat, property, value);
    return true;
   }
  } catch(e) { console.warn('[Astra] WAWebSetPropertyGroupAction failed:', e.message); }

  // Strategy 3: Runtime scan
  const engineRaid = window.Astra.mR;
  if (engineRaid && engineRaid.findModule) {
   const mod = engineRaid.findModule(m => m && typeof m.setGroupProperty === 'function');
   if (mod) {
    const chat = await getChat(groupId, Store);
    await mod.setGroupProperty(chat, property, value);
    return true;
   }
  }

  throw new Error('setGroupProperty not available');
 };

 /** Convenience: Set admins-only to add members */
 window.Astra.setAddMembersAdminsOnly = async function(groupId, adminsOnly) {
  return await window.Astra.setGroupProperty(groupId, 'member_add_mode', adminsOnly ? 0 : 1);
 };

 /** Convenience: Set admins-only to send messages */
 window.Astra.setMessagesAdminsOnly = async function(groupId, adminsOnly) {
  return await window.Astra.setGroupProperty(groupId, 'announcement', adminsOnly ? 1 : 0);
 };

 /** Convenience: Set admins-only to edit group info */
 window.Astra.setInfoAdminsOnly = async function(groupId, adminsOnly) {
  return await window.Astra.setGroupProperty(groupId, 'restrict', adminsOnly ? 1 : 0);
 };

 // ─── NEW FEATURES: Membership Requests ──────────────────────
 window.Astra.getGroupMembershipRequests = async function(groupId) {
  const Store = window.Astra.initializeEngine();
  const chatWid = getWid(groupId, Store);

  // Update metadata first
  try {
   const queryJob = window.require && window.require('WAWebGroupQueryJob');
   if (queryJob) await queryJob.queryAndUpdateGroupMetadataById({ id: groupId });
  } catch(e) {}

  const chat = await getChat(groupId, Store);
  if (!chat || !chat.groupMetadata) return [];

  const requests = chat.groupMetadata.membershipApprovalRequests;
  if (!requests || !requests._models) return [];

  return requests._models.map(r => ({
   id: r.id?._serialized || r.id,
   addedBy: r.addedBy?._serialized || r.addedBy,
   requestMethod: r.requestMethod || 'unknown',
   timestamp: r.t || Date.now()
  }));
 };

 window.Astra.membershipRequestAction = async function(groupId, action, requesterIds) {
  // action: 'approve' or 'reject'
  const toApprove = action.toLowerCase() === 'approve';

  // Strategy 1: window.require RPC
  try {
   const WidFactory = window.require && window.require('WAWebWidFactory');
   const WidToJid = window.require && window.require('WAWebWidToJid');
   const ActionRPC = window.require && window.require('WASmaxGroupsMembershipRequestsActionRPC');

   if (WidFactory && WidToJid && ActionRPC) {
    const groupWid = WidFactory.createWid(groupId);
    const groupJid = WidToJid.widToGroupJid(groupWid);
    const results = [];

    if (!requesterIds || !requesterIds.length) {
     // Get all pending requests
     const reqs = await window.Astra.getGroupMembershipRequests(groupId);
     requesterIds = reqs.map(r => r.id);
    }

    for (const rid of requesterIds) {
     const rWid = WidFactory.createWid(rid);
     const participantArgs = [{ participantJid: WidToJid.widToUserJid(rWid) }];
     const args = { iqTo: groupJid };
     args[toApprove ? 'approveArgs' : 'rejectArgs'] = { participantArgs };

     const resp = await ActionRPC.sendMembershipRequestsActionRPC(args);
     results.push({ requesterId: rid, success: resp.name === 'MembershipRequestsActionResponseSuccess' });
    }
    return results;
   }
  } catch(e) { console.warn('[Astra] membershipRequestAction RPC failed:', e.message); }

  throw new Error('Membership request action not available');
 };

 // ─── NEW FEATURES: Chat Utilities ───────────────────────────
 window.Astra.clearChat = async function(chatId) {
  const Store = window.Astra.initializeEngine();
  const chat = await getChat(chatId, Store);
  if (!chat) throw new Error('Chat not found: ' + chatId);

  // Strategy 1: Store
  if (Store.ClearChat && typeof Store.ClearChat.sendClear === 'function') {
   await Store.ClearChat.sendClear(chat, false);
   return true;
  }

  // Strategy 2: window.require
  try {
   const ClearMod = window.require && window.require('WAWebChatClearBridge');
   if (ClearMod && typeof ClearMod.sendClear === 'function') {
    await ClearMod.sendClear(chat, false);
    return true;
   }
  } catch(e) {}

  // Strategy 3: Runtime scan
  const engineRaid = window.Astra.mR;
  if (engineRaid && engineRaid.findModule) {
   const mod = engineRaid.findModule(m => m && typeof m.sendClear === 'function');
   if (mod) { await mod.sendClear(chat, false); return true; }
  }

  throw new Error('clearChat not available');
 };

 window.Astra.deleteChat = async function(chatId) {
  const Store = window.Astra.initializeEngine();
  const chat = await getChat(chatId, Store);
  if (!chat) throw new Error('Chat not found: ' + chatId);

  try {
   const DelMod = window.require && window.require('WAWebDeleteChatAction');
   if (DelMod && typeof DelMod.sendDelete === 'function') {
    await DelMod.sendDelete(chat);
    return true;
   }
  } catch(e) {}

  if (Store.DeleteChat && typeof Store.DeleteChat.sendDelete === 'function') {
   await Store.DeleteChat.sendDelete(chat);
   return true;
  }

  throw new Error('deleteChat not available');
 };

 window.Astra.forwardMessage = async function(chatId, msgId) {
  const Store = window.Astra.initializeEngine();
  const chatWid = getWid(chatId, Store);
  const chat = await getChat(chatId, Store);
  if (!chat) throw new Error('Chat not found: ' + chatId);

  const msg = Store.Msg ? Store.Msg.get(msgId) : null;
  if (!msg) throw new Error('Message not found: ' + msgId);

  if (Store.ForwardMsg && typeof Store.ForwardMsg.forwardMessage === 'function') {
   await Store.ForwardMsg.forwardMessage(chat, msg);
   return true;
  }

  try {
   const FwdMod = window.require && window.require('WAWebForwardMessagesToChat');
   if (FwdMod) {
    const fn = FwdMod.forwardMessagesToChat || FwdMod.default;
    if (typeof fn === 'function') { await fn(chat, [msg], false); return true; }
   }
  } catch(e) {}

  throw new Error('forwardMessage not available');
 };

 window.Astra.pinMessage = async function(msgId, pin, duration) {
  // duration in seconds (default 7 days = 604800)
  duration = duration || 604800;
  const Store = window.Astra.initializeEngine();
  const msg = Store.Msg ? Store.Msg.get(msgId) : null;
  if (!msg) throw new Error('Message not found: ' + msgId);

  try {
   const PinMod = window.require && window.require('WAWebSendPinMessageAction');
   const PinConst = window.require && window.require('WAWebPinMsgConstants');
   if (PinMod && typeof PinMod.sendPinInChatMsg === 'function') {
    // Override duration temporarily
    let origFn = null;
    if (PinConst && PinConst.getPinExpiryDuration) {
     origFn = PinConst.getPinExpiryDuration;
     PinConst.getPinExpiryDuration = () => duration;
    }
    const res = await PinMod.sendPinInChatMsg(msg, pin, duration);
    if (origFn) PinConst.getPinExpiryDuration = origFn;
    return res.messageSendResult === 'OK';
   }
  } catch(e) { console.warn('[Astra] pinMessage failed:', e.message); }

  throw new Error('pinMessage not available');
 };

 window.Astra.rejectCall = async function(peerJid, callId) {
  try {
   const UserPrefs = window.require && window.require('WAWebUserPrefsMeUser');
   const WAWap = window.require && window.require('WAWap');
   const SendIq = window.require && window.require('WADeprecatedSendIq');

   if (UserPrefs && WAWap && SendIq) {
    const userId = UserPrefs.getMaybeMePnUser()._serialized;
    const stanza = WAWap.wap('call', {
     id: WAWap.generateId(),
     from: userId,
     to: peerJid,
    }, [
     WAWap.wap('reject', { 'call-id': callId, 'call-creator': peerJid, count: '0' })
    ]);
    await SendIq.deprecatedCastStanza(stanza);
    return true;
   }
  } catch(e) { console.warn('[Astra] rejectCall failed:', e.message); }

  throw new Error('rejectCall not available');
 };

 // ─── ENHANCED FALLBACKS: Use NEWWP module names ─────────────
 // Add window.require-based fallback to existing addParticipants
 const origAddParticipants = window.Astra.addParticipants;
 window.Astra.addParticipants = async function(groupId, participants) {
  try {
   return await origAddParticipants(groupId, participants);
  } catch (e) {
   // Fallback: WAWebModifyParticipantsGroupAction
   console.warn('[Astra] addParticipants fallback using window.require...', e.message);
   const Store = window.Astra.initializeEngine();
   const chat = await getChat(groupId, Store);
   if (!chat) throw e;
   try {
    const AddMod = window.require && window.require('WAWebModifyParticipantsGroupAction');
    if (!AddMod) throw e;
    const WidFactory = window.require('WAWebWidFactory');
    const pWids = participants.map(p => WidFactory.createWid(p));
    await AddMod.addParticipants(chat, pWids);
    return true;
   } catch (e2) { throw e; }
  }
 };

 const origKickParticipants = window.Astra.kickParticipants;
 window.Astra.kickParticipants = async function(groupId, participants) {
  try {
   return await origKickParticipants(groupId, participants);
  } catch (e) {
   console.warn('[Astra] kickParticipants fallback...', e.message);
   const Store = window.Astra.initializeEngine();
   const chat = await getChat(groupId, Store);
   if (!chat) throw e;
   try {
    const RemMod = window.require && window.require('WAWebModifyParticipantsGroupAction');
    if (!RemMod) throw e;
    const WidFactory = window.require('WAWebWidFactory');
    const pWids = participants.map(p => {
     const wid = WidFactory.createWid(p);
     return chat.groupMetadata?.participants.get(wid._serialized) || wid;
    });
    await RemMod.removeParticipants(chat, pWids.filter(Boolean));
    return true;
   } catch (e2) { throw e; }
  }
 };

})();
"""

