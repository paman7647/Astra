# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

STATUS_CODE = r"""
(function() {
 window.Astra = window.Astra || {};

 window.Astra.sendTextStatus = async (text, options = {}) => {
  console.log(`[Astra] sendTextStatus: ${text.substring(0, 20)}...`);
  const Store = window.Astra.initializeEngine();

  const payload = {
   body: text,
   type: 'chat',
   backgroundColor: options.backgroundColor || '#000000',
   font: options.font || 1,
   statusV3: true,
   isStatusV3: true
  };

  let StatusV3Action = window.Store.StatusUtils || window.Store.StatusV3Action;

  if (!StatusV3Action && window.Astra.mR) {
    StatusV3Action = window.Astra.mR.findModule(m => m && (m.postStatusV3 || m.sendStatusV3 || m.sendTextStatus || m.sendMediaStatus || m.setMyStatus || m.postStatus));
  }

  if (StatusV3Action) {
   let sendFn = StatusV3Action.postStatusV3 || StatusV3Action.sendTextStatus || StatusV3Action.setMyStatus || StatusV3Action.postStatus || StatusV3Action.sendStatusV3;
   let target = StatusV3Action;

   if (!sendFn) {
    target = Object.values(StatusV3Action).find(m => m && (m.postStatusV3 || m.postStatus || m.sendStatusV3)) || target;
    sendFn = target.postStatusV3 || target.postStatus || target.sendStatusV3;
   }

   if (sendFn) {
    try {
     console.log('[Astra] Attempting internal status update...');
     await Promise.race([
      sendFn.call(target, payload),
      new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 8000))
     ]);
     console.log('[Astra] Internal status update successful.');
     return true;
    } catch (e) {
     console.warn(`[Astra] Internal status update failed or timed out: ${e.message}`);
    }
   }
  }

  console.log('[Astra] Falling back to DOM for status update...');
  return await window.Astra.sendTextStatusDOM(text);
 };

 window.Astra.sendMediaStatus = async (data, type, caption = "", options = {}) => {
  const Store = window.Astra.initializeEngine();

  // 1. Prepare Media
  let b64 = data;
  if (b64.includes(',')) b64 = b64.split(',')[1];

  const mime = type === 'image' ? 'image/jpeg' : 'video/mp4';
  const mediaData = await window.Astra.prepareMedia({
   data: b64,
   mimetype: mime,
   filename: 'status'
  });

  // 2. Upload Media
  const uploadResult = await window.Astra.uploadMedia(mediaData);
  if (!uploadResult || !uploadResult.mediaEntry) throw new Error('Astra: Status media upload failed');

  // 3. Post Status
  const payload = {
   media: uploadResult.mediaEntry,
   caption: caption,
   type: type,
   statusV3: true,
   isStatusV3: true
  };

  let StatusV3Action = window.Store.StatusUtils || window.Store.StatusV3Action;

  if (!StatusV3Action) {
   try {
    // Try aggressive search via Astra mapper
    StatusV3Action = window.Astra.mR.findModule('postStatusV3') ||
         window.Astra.mR.findModule('sendStatusV3') ||
         window.Astra.mR.findModule('setMyStatus');
   } catch (e) {}
  }

  if (!StatusV3Action && window.Astra.mR) {
    const found = window.Astra.mR.findModule(m => m && (m.postStatusV3 || m.sendStatusV3 || m.sendTextStatus || m.sendMediaStatus || m.setMyStatus || m.postStatus));
    if (found) StatusV3Action = found;
  }

  if (!StatusV3Action) throw new Error('Astra: StatusV3Action module not found');

  let sendFn = StatusV3Action.postStatusV3 || StatusV3Action.sendMediaStatus || StatusV3Action.setMyStatus || StatusV3Action.postStatus || StatusV3Action.sendStatusV3;
  let target = StatusV3Action;

  if (!sendFn) {
   target = Object.values(StatusV3Action).find(m => m && (m.postStatusV3 || m.postStatus || m.sendStatusV3)) || target;
   sendFn = target.postStatusV3 || target.postStatus || target.sendStatusV3;
  }

  if (!sendFn) throw new Error('Astra: postStatusV3 method not found on module');

  return await sendFn.call(target, payload);
 };
 window.Astra.sendTextStatusDOM = async (text) => {
  // Find which label is used for the status tab
  const statusLabels = ['Status', 'Updates', 'Status (Updates)'];
  let foundLabel = null;
  for (const label of statusLabels) {
   if (document.querySelector(`button[aria-label="${label}"]`)) {
    foundLabel = label;
    break;
   }
  }

  if (!foundLabel) {
   // Fallback: search for any button that contains 'status' or 'updates'
   const allBtn = Array.from(document.querySelectorAll('button[aria-label]'));
   const target = allBtn.find(b => b.ariaLabel.toLowerCase().includes('status') || b.ariaLabel.toLowerCase().includes('updates'));
   if (target) foundLabel = target.ariaLabel;
  }

  if (!foundLabel) throw new Error("Astra: Status/Updates tab not found in sidebar");

  await window.Astra.ensureSidebar(foundLabel, true);

  // Wait for the status list to load
  await new Promise(r => setTimeout(r, 1000));

  const drawer = window.Astra.getActiveDrawer();
  if (!drawer) throw new Error("Astra: Active drawer not found after opening status");

  await window.Astra.runDOMAction([
   { element: drawer.querySelector('button[aria-label="Add Status"], button[aria-label="Create status"], [data-testid="status-v3-add"]'), action: 'click', wait: 800 },
   { selector: 'div[aria-label="Text"], div[role="button"]:has(span[data-icon="status-v3-text"]), [data-testid="status-v3-text"]', action: 'click', wait: 800 },
   { selector: 'div[role="textbox"][contenteditable="true"], [data-testid="status-v3-text-input"]', action: 'type', value: text, wait: 1000 },
   { selector: 'div[aria-label="Send"][role="button"], span[data-icon="send"], [data-testid="status-v3-send"]', action: 'click', wait: 1500 }
  ]);

  await window.Astra.ensureSidebar(foundLabel, false);
  return true;
 };
 window.Astra.getStatusViewers = async (msgId) => {
  const Store = window.Astra.initializeEngine();
  const repo = Store.MessageRepo || Store.MsgRepo || Store.Msg;
  const msg = repo.get(msgId) || (await repo.getMessagesById?.([msgId]))?.messages?.[0];
  if (!msg) throw new Error("Astra: Status message not found: " + msgId);

  let viewers = [];
  if (msg.statusV3) {
   // Retrieve viewers from the message object or Store.Status
   const statusMod = window.Store.Status;
   if (statusMod && typeof statusMod.getStatusViewers === 'function') {
    viewers = await statusMod.getStatusViewers(msg);
   } else if (msg.ackReadList) {
    viewers = msg.ackReadList;
   }
  }

  return (viewers || []).map(v => ({
   id: v.id?._serialized || v._serialized || v,
   readAt: v.readAt || v.t || Date.now()
  }));
 };
})();
"""
