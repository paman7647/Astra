# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module assembles the JavaScript source for the Astra Engine.
The engine acts as the local representative of Astra inside the browser.
"""

from ..functions.base import CORE_SCRIPT
from ..functions.chat import CHAT_CODE
from ..functions.contact import CONTACT_CODE
from ..functions.group import GROUP_CODE
from ..functions.media import MEDIA_CODE
from ..functions.account import ACCOUNT_CODE
from ..functions.diagnostic import DIAGNOSTIC_CODE
from ..functions.status import STATUS_CODE
from ..functions.privacy import PRIVACY_CODE
from ..functions.dom import DOM_SCANNER_CODE
from ..functions.firefox_dom import FIREFOX_DOM_CODE
from ..functions.idb_cache import IDB_CACHE_CODE
from ..functions.download import DOWNLOAD_CODE

# The Definitive Engine Source (V24 Edition)
# We assemble individual modules into a single optimized script
JS_ENGINE_SOURCE = "\n".join([
 "(function() {",
 " console.log('[Astra] Injection start...');",
 " window.AstraInjected = (window.AstraInjected || 0) + 1;",

 "// Initialize internal module scope",
 "window.Astra = window.Astra || {};",

 # Core internal logic
 CORE_SCRIPT,

 # Feature Modules
 ACCOUNT_CODE,
 CHAT_CODE,
 CONTACT_CODE,
 GROUP_CODE,
 MEDIA_CODE,
 DIAGNOSTIC_CODE,
 STATUS_CODE,
 PRIVACY_CODE,
 DOM_SCANNER_CODE,
 FIREFOX_DOM_CODE,
 IDB_CACHE_CODE,
 DOWNLOAD_CODE,

 # --- Normalization Layer ---
 "(function() {",
 " const A = window.Astra;",
 " ",
 " // Normalizes all results for safe Python traversal",
 " const pack = (val) => {",
 " if (val === undefined) return null;",
 " if (val instanceof Error) throw val;",
 " if (val && val.error) throw new Error(val.error);",
 " return val;",
 " };",
 " ",
 " // Expose the clean API surface to the Protocol Bridge",
 " window.AstraEngine = {",
 " // Core Utilities",
 " sendChatState: async (p) => pack(await A.sendChatState(p.chatId, p.state)),",
 " getMe: async () => pack(await A.getIdentity()),",
 " getChats: async () => pack(await A.getChatList()),",
 " getContacts: async () => pack(await A.getContacts()),",
 " getChatById: async (p) => pack(await A.getChatById(p.chatId || p.id || p.value || p)),",
 " getContactById: async (p) => pack(await A.getContactById(p.contactId || p.id || p.value || p)),",
 " ",
 " // Messaging",
 " sendMessage: async (p) => pack(await A.sendText(p.to, p.text || p.body, p.options || {})),",
 " sendPoll: async (p) => pack(await A.sendPoll(p.to, p.name, p.options)),",
 " votePoll: async (p) => pack(await A.votePoll(p.msgId, p.selections)),",
 " editMessage: async (p) => pack(await A.editMessage(p.msgId, p.text || p.body, p.options || {})),",
 " deleteMessage: async (p) => pack(await A.deleteMessage(p.msgId, p.forEveryone !== false, p.clearMedia || false)),",
 " bulkDeleteMessages: async (p) => pack(await A.bulkDeleteMessages(p.msgIds, p.forEveryone !== false, p.clearMedia || false)),",
 " markSeen: async (p) => pack(await A.markSeen(p.chatId || p.value || p)),",
 " react: async (p) => pack(await A.sendReaction(p.msgId, p.emoji || p.reaction)),",
 " fetchMessages: async (p) => pack(await A.fetchMessages(p.chatId, p.searchOptions || {})),",
 " syncHistory: async (p) => pack(await A.syncHistory(p.chatId)),",
 " ",
 " // Media",
 " initChunkedUpload: async (p) => pack(A.initChunkedUpload(p.id, p.size)),",
 " pushChunk: async (p) => pack(A.pushChunk(p.id, p.data)),",
 " sendMedia: async (p) => {",
 "  let buffer = p.data || p.media;",
 "  if (buffer && buffer.includes(',')) buffer = buffer.split(',')[1];",
 "  const options = { ...(p.options || {}), caption: p.caption, _call_id: p._call_id };",
 "  const media = { data: buffer, mimetype: p.mimetype, filename: p.filename, type: p.type, uploadId: p.uploadId };",
 "  return pack(await A.sendMedia(p.to, media, options));",
 " },",
  " retrieveMedia: async (p) => pack(await A.retrieveMedia(p.msgId || p.value || p)),",
  " readMediaChunk: async (p) => pack(await A.readMediaChunk(p.id, p.offset, p.length)),",
  " clearMediaCache: async (p) => pack(await A.clearMediaCache(p.id)),",
 " ",
 " // Chat Management",
 " archiveChat: async (p) => pack(await A.archiveChat(p.chatId, p.archive !== false)),",
 " pinChat: async (p) => pack(await A.pinChat(p.chatId, p.pin !== false)),",
 " muteChat: async (p) => pack(await A.muteChat(p.chatId, p.duration)),",
 " ",
 " // Group Management",
 " createGroup: async (p) => pack(await A.createGroup(p.title, p.participants)),",
 " addMembers: async (p) => pack(await A.addParticipants(p.groupId, p.participants)),",
 " removeMembers: async (p) => pack(await A.kickParticipants(p.groupId, p.participants)),",
 " promote: async (p) => pack(await A.promoteParticipants(p.groupId, p.participants)),",
 " demote: async (p) => pack(await A.demoteParticipants(p.groupId, p.participants)),",
 " leaveGroup: async (p) => pack(await A.leaveGroup(p.groupId || p.value || p)),",
 " getGroupInfo: async (p) => pack(await A.getGroupInfo(p.groupId || p.value || p)),",
 " setGroupSubject: async (p) => pack(await A.setGroupSubject(p.groupId, p.subject)),",
 " setGroupDescription: async (p) => pack(await A.setGroupDescription(p.groupId || p.value || p, p.description)),",
 " getInviteLink: async (p) => pack(await A.getInviteCode(p.chatId || p.groupId || p.value || p)),",
 " revokeInviteLink: async (p) => pack(await A.revokeInviteCode(p.chatId || p.groupId || p.value || p)),",
 " joinViaLink: async (p) => pack(await A.joinGroupViaLink(p.code || p.value || p)),",
 " setGroupProperty: async (p) => pack(await A.setGroupProperty(p.groupId, p.property, p.value)),",
 " setAddMembersAdminsOnly: async (p) => pack(await A.setAddMembersAdminsOnly(p.groupId, p.adminsOnly !== false)),",
 " setMessagesAdminsOnly: async (p) => pack(await A.setMessagesAdminsOnly(p.groupId, p.adminsOnly !== false)),",
 " setInfoAdminsOnly: async (p) => pack(await A.setInfoAdminsOnly(p.groupId, p.adminsOnly !== false)),",
 " getGroupMembershipRequests: async (p) => pack(await A.getGroupMembershipRequests(p.groupId || p.value || p)),",
 " membershipRequestAction: async (p) => pack(await A.membershipRequestAction(p.groupId, p.action, p.requesterIds || [])),",
 " ",
 " // Social & Profile",
 " setProfileName: async (p) => pack(await A.updateProfileDOM(p.name || p.pushname)),",
 " setAbout: async (p) => pack(await A.setStatusDOM(p.about || p.status)),",
 " getProfilePic: async (p) => pack(await A.getProfilePic(p.chatId || p.value || p)),",
 " updateProfilePic: async (p) => pack(await A.setProfilePic(p.data)),",
 " updateGroupPic: async (p) => {",
 "  const media = { data: p.data, mimetype: 'image/jpeg' };",
 "  const thumb = await A.cropAndResizeImage(media, { size: 96, asDataUrl: true });",
 "  const pic = await A.cropAndResizeImage(media, { size: 640, asDataUrl: true });",
 "  return pack(await A.setGroupPicture(p.groupId, thumb, pic));",
 " },",
 " block: async (p) => pack(await A.blockContact(p.chatId || p.id || p.value || p, p.block !== false)),",
 " ",
 " // Status & Stories",
 " setMyStatus: async (p) => pack(await A.sendTextStatus(p.status || p.value || p)),",
 " postStatus: async (p) => pack(await A.sendMediaStatus(p.data || p.value || p, p.mimetype, p.caption)),",
 " getStatusViewers: async (p) => pack(await A.getStatusViewers(p.msgId || p.value || p)),",
 " ",
 " // Privacy & Settings",
 " setPrivacy: async (p) => pack(await A.setPrivacySetting(p.category, p.value)),",
 " getPrivacySettings: async () => pack(await A.getPrivacySettings()),",
 " ",
 " // Debug & System",
 " deepScanModules: async (p) => pack(await A.deepScanModules(p.id || p.value || p)),",
 " getDiagnostics: async () => pack(await A.getDiagnostics()),",
 " getDomSnippet: async (p) => pack(await A.getDomSnippet(p.selector || p.value || p)),",
 " scanDOM: async (p) => pack(await A.scanDOM(p.section || p.value || p)),",
 " generateDOMReport: async (p) => pack(await A.generateDOMReport(p.section || p.value || p)),",
 " sync: async () => pack(await A.deepSync()),",
 " logout: async () => pack(await A.logout()),",
 " ",
 " // Extended Utilities",
 " clearChat: async (p) => pack(await A.clearChat(p.chatId || p.value || p)),",
 " deleteChat: async (p) => pack(await A.deleteChat(p.chatId || p.value || p)),",
 " forwardMessage: async (p) => pack(await A.forwardMessage(p.chatId, p.msgId)),",
 " pinMessage: async (p) => pack(await A.pinMessage(p.msgId, p.pin !== false, p.duration)),",
 " rejectCall: async (p) => pack(await A.rejectCall(p.peerJid, p.callId)),",
 " };",
 " ",
 " // Uplink for event propagation",
 " window.py_onMessage = (m) => A.emit && A.emit('msg', m);",
 " ",
 " if (!window.AstraEngine) {",
 " console.warn('[Astra] High-Level Engine init failed - window.Astra missing?');",
 " } else {",
 " console.log('[Astra] High-Level Engine V24 Ready.');",
 " }",
 "})();",
 "})();"
])
