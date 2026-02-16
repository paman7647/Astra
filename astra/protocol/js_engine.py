# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module assembles the JavaScript source for the Astra Engine.
The engine acts as the local representative of Astra inside the browser.
"""

from ..core.bridge.base import CORE_SCRIPT
from ..core.bridge.chat import CHAT_CODE
from ..core.bridge.contact import CONTACT_CODE
from ..core.bridge.group import GROUP_CODE
from ..core.bridge.media import MEDIA_CODE
from ..core.bridge.account import ACCOUNT_CODE
from ..core.bridge.diagnostic import DIAGNOSTIC_CODE
from ..core.bridge.status import STATUS_CODE
from ..core.bridge.privacy import PRIVACY_CODE
from ..core.bridge.dom import DOM_SCANNER_CODE
from ..core.bridge.firefox_dom import FIREFOX_DOM_CODE
from ..core.bridge.idb_cache import IDB_CACHE_CODE

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

 # --- Expert Proxy Layer ---
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
 " getMe: async () => pack(await A.getIdentity()),",
 " getChats: async () => pack(await A.getChatList()),",
 " getContacts: async () => pack(await A.getContacts()),",
 " getChatById: async (p) => pack(await A.getChatById(p)),",
 " getContactById: async (p) => pack(await A.getContactById(p || p.id)),",
 " ",
 " // Messaging",
 " sendMessage: async (p) => pack(await A.sendText(p.to, p.text || p.body, p.options || {})),",
 " sendPoll: async (p) => pack(await A.sendPoll(p.to, p.name, p.options)),",
 " votePoll: async (p) => pack(await A.votePoll(p.msgId, p.selections)),",
 " editMessage: async (p) => pack(await A.editMessage(p.msgId, p.text || p.body, p.options || {})),",
 " deleteMessage: async (p) => pack(await A.deleteMessage(p.msgId, p.forEveryone !== false, p.clearMedia || false)),",
 " markSeen: async (p) => pack(await A.markSeen(p.chatId || p)),",
 " react: async (p) => pack(await A.sendReaction(p.msgId, p.emoji || p.reaction)),",
 " fetchMessages: async (p) => pack(await A.fetchMessages(p.chatId, p.searchOptions || {})),",
 " syncHistory: async (p) => pack(await A.syncHistory(p.chatId)),",
 " ",
 " // Media",
 " sendMedia: async (p) => {",
 "  let buffer = p.data || p.media;",
 "  if (buffer && buffer.includes(',')) buffer = buffer.split(',')[1];",
 "  const options = { ...(p.options || {}), caption: p.caption, _call_id: p._call_id };",
 "  return pack(await A.sendMedia(p.to, { data: buffer, mimetype: p.mimetype, filename: p.filename, type: p.type }, options));",
 " },",
 " retrieveMedia: async (p) => pack(await A.retrieveMedia(p.msgId || p)),",
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
 " leaveGroup: async (p) => pack(await A.leaveGroup(p.groupId || p)),",
 " getGroupInfo: async (p) => pack(await A.getGroupInfo(p.groupId || p)),",
 " setGroupDescription: async (p) => pack(await A.setGroupDescription(p.groupId, p.description)),",
 " getInviteLink: async (p) => pack(await A.getInviteCode(p.chatId || p)),",
 " joinViaLink: async (p) => pack(await A.joinGroupViaLink(p.code || p)),",
 " ",
 " // Social & Profile",
 " setProfileName: async (p) => pack(await A.updateProfileDOM(p.name || p.pushname)),",
 " setAbout: async (p) => pack(await A.setStatusDOM(p.about || p.status)),",
 " getProfilePic: async (p) => pack(await A.getProfilePic(p.chatId || p)),",
 " block: async (p) => pack(await A.blockContact(p.chatId || p.id, p.block !== false)),",
 " ",
 " // Status & Stories",
 " setMyStatus: async (p) => pack(await A.sendTextStatus(p.status || p)),",
 " postStatus: async (p) => pack(await A.sendMediaStatus(p.data || p, p.mimetype, p.caption)),",
 " getStatusViewers: async (p) => pack(await A.getStatusViewers(p.msgId || p)),",
 " ",
 " // Privacy & Settings",
 " setPrivacy: async (p) => pack(await A.setPrivacySetting(p.category, p.value)),",
 " getPrivacySettings: async () => pack(await A.getPrivacySettings()),",
 " ",
 " // Debug & System",
 " deepScanModules: async (p) => pack(await A.deepScanModules(p.id || p)),",
 " getDiagnostics: async () => pack(await A.getDiagnostics()),",
 " getDomSnippet: async (p) => pack(await A.getDomSnippet(p.selector)),",
 " scanDOM: async (p) => pack(await A.scanDOM(p.section || p)),",
 " generateDOMReport: async (p) => pack(await A.generateDOMReport(p.section || p)),",
 " sync: async () => pack(await A.deepSync()),",
 " logout: async () => pack(await A.logout()),",
 " };",
 " ",
 " // Uplink for event propagation",
 " window.py_onMessage = (m) => A.emit && A.emit('msg', m);",
 " ",
 " console.log('[Astra] High-Level Engine V24 Ready.');",
 "})();",
 "})();"
])
