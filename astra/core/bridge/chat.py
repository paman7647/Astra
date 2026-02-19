# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

CHAT_CODE = r"""
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
"""
