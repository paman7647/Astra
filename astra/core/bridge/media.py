# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

MEDIA_CODE = r"""
(function() {
 window.Astra = window.Astra || {};

 window.Astra.base64ToFile = ({ data, mimetype, filename }) => {
  const bin = window.atob(data);
  const buf = new ArrayBuffer(bin.length);
  const view = new Uint8Array(buf);
  for (let i = 0; i < bin.length; i++) {
   view[i] = bin.charCodeAt(i);
  }
  const blob = new Blob([buf], { type: mimetype });
  return new File([blob], filename, { type: mimetype, lastModified: Date.now() });
 };

 window.Astra.bufToBase64 = (buf) =>
  new Promise((resolve, reject) => {
   const blob = new Blob([buf], { type: 'application/octet-stream' });
   const reader = new FileReader();
   reader.onload = () => resolve(reader.result.split(',')[1]);
   reader.onerror = (e) => reject(e);
   reader.readAsDataURL(blob);
  });

 window.Astra.send_media = async function(to, data, mimetype, filename, caption, options = {}) {
  return await window.Astra.sendMedia(to, { data, mimetype, filename }, { caption, ...options });
 };

 window.Astra.sendMedia = async function(to, media, options = {}) {
  console.log("Astra: sendMedia called", { to, mimetype: media.mimetype });
  const Store = window.Astra.initializeEngine();

  const mimetype = media.mimetype || 'application/octet-stream';
  const isVideo = mimetype.startsWith('video/');
  const isAudio = mimetype.startsWith('audio/');
  const isImage = mimetype.startsWith('image/');
  const targetId = typeof to === 'string' ? to : (to._serialized || to.id?._serialized || to.id);
  const wid = window.Astra.createWid(targetId.includes('@') ? targetId : `${targetId}@c.us`);
  const chat = await window.Astra.getChat(wid);
  if (!chat) throw new Error('Astra: Chat not found for ' + targetId);

  try {
   const lid = Store.UserCredentials.getMaybeMeLidUser ? Store.UserCredentials.getMaybeMeLidUser() : null;
   const pn = Store.UserCredentials.getMaybeMePnUser ? Store.UserCredentials.getMaybeMePnUser() : (Store.SessionInfo && (Store.SessionInfo.wid || Store.SessionInfo.me));

   // Generate id with fallbacks for different WA versions
   let id;
   if (Store.MessageIdentity && Store.MessageIdentity.newId) {
    id = await Store.MessageIdentity.newId();
   } else if (Store.MsgKey && Store.MsgKey.newId) {
    id = await Store.MsgKey.newId();
   } else if (Store.Msg && Store.Msg.newId) {
    id = await Store.Msg.newId();
   } else {
    // Best-effort fallback: timestamp-based id
    id = `${Date.now()}-${Math.random().toString(36).slice(2,9)}`;
   }

   let from;
   const isLidChat = chat.id && (typeof chat.id.isLid === 'function' ? chat.id.isLid() : chat.id.isLid);
   if (isLidChat) {
    from = lid || pn;
   } else {
    from = pn;
   }

   if (!from) {
    throw new Error("Astra: Could not determine 'from' identity (LID/PN missing)");
   }

   let part;
   if (chat.id && (typeof chat.id.isGroup === 'function' ? chat.id.isGroup() : chat.id.isGroup)) {
    const isLidGroups = chat.groupMetadata && chat.groupMetadata.isLidAddressingMode;
    const f = isLidGroups ? (lid || pn) : pn;
    part = window.Astra.createWid(f);
   }

   let key;
   if (Store.MessageIdentity) {
    key = new Store.MessageIdentity({
     from: window.Astra.createWid(from),
     to: chat.id,
     id,
     participant: part ? window.Astra.createWid(part) : undefined,
     selfDir: 'out'
    });
   } else if (Store.MsgKey) {
    key = new Store.MsgKey({
     from: from,
     to: chat.id,
     id: id,
     participant: part ? window.Astra.createWid(part) : undefined,
     selfDir: 'out'
    });
   } else {
    key = { id: id, _serialized: typeof id === 'string' ? id : (id && id._serialized ? id._serialized : String(id)) };
   }

   const file = window.Astra.base64ToFile(media);

   // Defensive: if it's a video, ensure we have dimensions before prep
   if (mimetype.startsWith('video/')) {
    try {
     const video = document.createElement('video');
     video.preload = 'metadata';
     const videoUrl = URL.createObjectURL(file);
     video.src = videoUrl;
     await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
       console.warn("Astra: video dimensions timeout, proceeding anyway");
       resolve();
      }, 5000);
      video.onloadedmetadata = () => {
       clearTimeout(timeout);
       if (video.videoWidth && video.videoHeight) {
        console.log(`Astra: video dims detected: ${video.videoWidth}x${video.videoHeight}`);
       }
       URL.revokeObjectURL(videoUrl);
       resolve();
      };
      video.onerror = () => {
       clearTimeout(timeout);
       console.error("Astra: video metadata load error");
       resolve();
      };
     });
    } catch (vErr) {
     console.warn("Astra: dimension probe failed", vErr);
    }
   }

   // Create source blob with fallbacks (MediaBuffer, OpaqueData, etc.)
   let source;
   if (Store.MediaBuffer && Store.MediaBuffer.createFromData) {
    source = await Store.MediaBuffer.createFromData(file, mimetype);
   } else if (Store.OpaqueData && Store.OpaqueData.createFromData) {
    source = await Store.OpaqueData.createFromData(file, mimetype);
   } else if (Store.OpaqueData && Store.OpaqueData.fromData) {
    source = await Store.OpaqueData.fromData(file, mimetype);
   } else {
    // Last resort: use raw file object
    source = file;
   }

   const params = {
    asSticker: options.asSticker,
    asGif: options.asGif,
    isPtt: options.asVoice,
    asAudio: options.asAudio,
    asDocument: options.asDocument,
    width: options.width,
    height: options.height
   };

   // Prep media using available prep module
   let prep;
   if (Store.MediaEngine && Store.MediaEngine.prepRawMedia) {
    prep = Store.MediaEngine.prepRawMedia(source, params);
   } else if (Store.MediaPrep && Store.MediaPrep.prepRawMedia) {
    prep = Store.MediaPrep.prepRawMedia(source, params);
   } else if (Store.MediaDataUtils && Store.MediaDataUtils.prepRawMedia) {
    prep = Store.MediaDataUtils.prepRawMedia(source, params);
   } else {
    throw new Error('Astra: No media prep module available');
   }

   // Await prep result with compatibility for different return types
   let data;
   if (prep && typeof prep.waitForPrep === 'function') {
    data = await prep.waitForPrep();
   } else if (prep && typeof prep.then === 'function') {
    data = await prep;
   } else {
    data = prep;
   }

   // Get or create media metadata (MediaMetadata vs MediaObject)
   let meta;
   if (Store.MediaMetadata && Store.MediaMetadata.getOrCreateMediaObject) {
    meta = Store.MediaMetadata.getOrCreateMediaObject(data.filehash);
   } else if (Store.MediaObject && Store.MediaObject.getOrCreateMediaObject) {
    meta = Store.MediaObject.getOrCreateMediaObject(data.filehash);
   } else {
    meta = { filehash: data.filehash, size: data.size };
   }

   if (!data.filehash) throw new Error('Engine fault: filehash missing');

   // Ensure mediaBlob is of the expected class
   const isMediaBufferInstance = Store.MediaBuffer && (data.mediaBlob instanceof Store.MediaBuffer);
   const isOpaqueDataInstance = Store.OpaqueData && (data.mediaBlob instanceof Store.OpaqueData);
   if (!isMediaBufferInstance && !isOpaqueDataInstance) {
    if (Store.MediaBuffer && Store.MediaBuffer.createFromData) {
     data.mediaBlob = await Store.MediaBuffer.createFromData(data.mediaBlob, data.mediaBlob.type || media.mimetype);
    } else if (Store.OpaqueData && Store.OpaqueData.createFromData) {
     data.mediaBlob = await Store.OpaqueData.createFromData(data.mediaBlob, data.mediaBlob.type || media.mimetype);
    }
   }

   // renderableUrl fallback
   if (data.mediaBlob && typeof data.mediaBlob.url === 'function') {
    data.renderableUrl = data.mediaBlob.url();
   } else if (data.mediaBlob && (data.mediaBlob instanceof Blob || (data.mediaBlob && data.mediaBlob.size))) {
    data.renderableUrl = URL.createObjectURL(data.mediaBlob);
   }

   if (meta && typeof meta.consolidate === 'function') meta.consolidate(data.toJSON ? data.toJSON() : data);
   if (data.mediaBlob && typeof data.mediaBlob.autorelease === 'function') data.mediaBlob.autorelease();

   // Upload using available uploader implementations
   let upload;
   const callId = options._call_id;

   // Hook into MediaObject events for real-time progress
   if (meta && typeof meta.on === 'function') {
    meta.on('change:uploadProgress', (p) => {
     if (callId && window.Astra.emit) {
      window.Astra.emit('progress', { id: callId, current: p, total: 100 });
     }
    });
   }

   try {
    const uploadParams = {
     mimetype: data.mimetype || media.mimetype,
     mediaObject: meta,
     mediaType: data.type || media.type
    };

    if (Store.AssetUploader && Store.AssetUploader.uploadMedia) {
     upload = await Store.AssetUploader.uploadMedia(uploadParams);
    } else if (Store.MediaUpload && Store.MediaUpload.uploadMedia) {
     upload = await Store.MediaUpload.uploadMedia(uploadParams);
    } else if (Store.MediaUpload && Store.MediaUpload.upload) {
     upload = await Store.MediaUpload.upload(uploadParams);
    } else if (Store.MediaUpload && Store.MediaUpload.startUpload) {
     upload = await Store.MediaUpload.startUpload(uploadParams);
    } else if (Store.UploadUtils && Store.UploadUtils.encryptAndUpload) {
     const controller = new AbortController();
     const uploadedInfo = await Store.UploadUtils.encryptAndUpload({
      blob: file,
      type: data.type || 'media',
      signal: controller.signal,
      onProgress: (p) => {
       if (callId && window.Astra.emit) {
        window.Astra.emit('progress', { id: callId, current: p, total: 100 });
       }
      }
     });
     upload = { mediaEntry: { mmsUrl: uploadedInfo.url || uploadedInfo.clientUrl, directPath: uploadedInfo.directPath || uploadedInfo.url, mediaKey: uploadedInfo.mediaKey || uploadedInfo.key, mediaKeyTimestamp: uploadedInfo.mediaKeyTimestamp, encFilehash: uploadedInfo.encFilehash || uploadedInfo.uploadhash } };
    } else {
     throw new Error('Astra: No uploader available to upload media');
    }
   } catch (uerr) {
    console.error('upload error fallback:', uerr);
    throw uerr;
   }

   const entry = upload && (upload.mediaEntry || upload.media_entry || upload) || {};
   // Normalize and set data
   const newData = { clientUrl: entry.mmsUrl || entry.clientUrl, directPath: entry.directPath || entry.direct_path || entry.directPath, mediaKey: entry.mediaKey || entry.media_key || entry.media_key || entry.key,
      mediaKeyTimestamp: entry.mediaKeyTimestamp || entry.media_key_timestamp, filehash: meta.filehash,
      encFilehash: entry.encFilehash || entry.enc_filehash || entry.uploadhash || entry.encFilehash, size: meta.size };
   if (typeof data.set === 'function') {
    data.set(newData);
   } else {
    Object.assign(data, newData);
   }

   // Prepare target and repo early so quoted message handling can use them
   const target = Store.EngineState && Store.EngineState.unproxy ? Store.EngineState.unproxy(chat) : chat;
   const repo = Store.MessageRepo || Store.MsgRepo;

   let msg = {
    id: key, ack: 0, from, to: chat.id, local: true, self: 'out',
    t: parseInt(Date.now() / 1000), isNewMsg: true, ...options
   };

   // Add quote support
   if (options.quoted_message_id) {
    const quotedMsg = repo.get(options.quoted_message_id) || await repo.find(options.quoted_message_id);
    if (quotedMsg) {
     if (typeof quotedMsg.msgContextInfo === 'function') {
      try {
       Object.assign(msg, quotedMsg.msgContextInfo(target));
      } catch(e) {
       // Fallback: attach quoted fields manually if msgContextInfo fails
       msg.quotedMsg = quotedMsg;
       msg.quotedStanzaId = quotedMsg.id && quotedMsg.id.id;
       msg.quotedParticipant = quotedMsg.author || quotedMsg.from;
       msg.quotedRemoteJid = quotedMsg.id && quotedMsg.id.remote;
      }
     } else {
      msg.quotedMsg = quotedMsg;
      msg.quotedStanzaId = quotedMsg.id && quotedMsg.id.id;
      msg.quotedParticipant = quotedMsg.author || quotedMsg.from;
      msg.quotedRemoteJid = quotedMsg.id && quotedMsg.id.remote;
     }
    }
   }

   msg = Object.assign(msg, data.toJSON ? data.toJSON() : data);
   msg.type = data.type;
   msg.caption = options.caption || '';
   msg.body = undefined;

   // Send message using available send APIs with fallbacks
   let p1;
   try {
    if (Store.SendMessage && typeof Store.SendMessage.addAndSendMsgToChat === 'function') {
     p1 = (await Store.SendMessage.addAndSendMsgToChat(target, msg))[0];
    } else if (Store.MessageSender && typeof Store.MessageSender.addAndSendMsgToChat === 'function') {
     console.warn('[Astra] fallback: used MessageSender.addAndSendMsgToChat in sendMedia');
     p1 = (await Store.MessageSender.addAndSendMsgToChat(target, msg))[0];
    } else if (Store.SendMessage && typeof Store.SendMessage.send === 'function') {
     console.warn('[Astra] fallback: used SendMessage.send in sendMedia');
     p1 = Promise.resolve(Store.SendMessage.send(target, msg));
    } else {
     throw new Error('Astra: No SendMessage implementation available to send media');
    }

    await p1;
   } catch (sendErr) {
    console.error('[Astra] sendMedia send error:', sendErr);
    throw sendErr;
   }

   // Resolve result from repo; be tolerant if key._serialized missing
   const serialized = key && (key._serialized || (typeof key === 'string' ? key : (key && key.id ? (key.id._serialized || key.id) : null)));
   const res = serialized ? repo.get(serialized) : (repo.get ? repo.get(key) : null);
   return window.Astra.serializeMsg(res || msg);
  } catch (e) {
   // Normalize and stringify error so Page.evaluate returns a readable message
   try {
    const message = (e && e.message) ? e.message : (typeof e === 'string' ? e : JSON.stringify(e));
    const stack = (e && e.stack) ? '\n' + e.stack : '';
    const info = `Astra: sendMedia error: ${message}${stack}`;
    console.error("sendMedia error:", info);
    throw new Error(info);
   } catch (ee) {
    console.error('sendMedia stringify failed', ee);
    throw e;
   }
  }
 };

 console.log("Astra Media Bridge v2 Loaded");

 window.Astra.mediaCache = {};

 window.Astra.readMediaChunk = async (id, offset, length) => {
  const buffer = window.Astra.mediaCache[id];
  if (!buffer) return null;
  
  // Use subarray for zero-copy view, then blob it
  const slice = buffer.subarray(offset, offset + length);
  return await window.Astra.bufToBase64(slice);
 };

 window.Astra.clearMediaCache = (id) => {
  delete window.Astra.mediaCache[id];
  return true;
 };

 window.Astra.retrieveMediaFromDOM = async (msgId) => {
  console.log(`[Astra] Attempting DOM retrieval for ${msgId}`);
  try {
   const Store = window.Astra.initializeEngine();
   
   // 0. Scroll message into view (Handle Virtualization)
   // WhatsApp removes off-screen messages from DOM. We must scroll to it.
   try {
    const msg = window.Store.Msg.get(msgId);
    if (msg && window.Store.Cmd && window.Store.Cmd.scrollToMessage) {
     console.log("[Astra] DOM: Scrolling to message...");
     window.Store.Cmd.scrollToMessage(msg);
     await new Promise(r => setTimeout(r, 700)); // Wait for render
    }
   } catch (e) {
    console.warn("[Astra] DOM: Scroll failed, trying searching anyway", e);
   }

   // 1. Find the message container
   // Try data-id first (most precise), then fallback to row matching
   let msgElement = document.querySelector(`div[data-id="${msgId}"]`) || 
           document.querySelector(`div[data-id*="${msgId.split('_').pop()}"]`);
   
   if (!msgElement) {
    // Fallback: Search all rows in main for the ID
    const rows = Array.from(document.querySelectorAll('#main [role="row"]'));
    msgElement = rows.find(r => r.getAttribute('data-id') === msgId || r.innerHTML.includes(msgId.split('_').pop()));
   }

   if (!msgElement) {
    console.warn("[Astra] DOM: Message container not found (Virtualization?)");
    return null;
   }

   // 2. Find the media element
   // Images are usually img, Videos/GIFs have video or img thumbnails
   // We look for src starting with blob:
   const mediaElement = Array.from(msgElement.querySelectorAll('img, video')).find(el => el.src && el.src.startsWith('blob:'));
   
   if (!mediaElement) {
    console.warn("[Astra] DOM: No blob media element found in message");
    // Attempt to click to load if it's a "Click to download" overlay? 
    // Risky, skipping for now.
    return null;
   }

   const blobUrl = mediaElement.src;
   console.log(`[Astra] DOM: Found blob URL: ${blobUrl}`);

   // 3. Fetch the data from the blob URL
   // This works because we are in the same context
   const response = await fetch(blobUrl);
   const blob = await response.blob();
   const buffer = await blob.arrayBuffer();
   const arrayBuffer = new Uint8Array(buffer);

   console.log(`[Astra] DOM: Fetched ${arrayBuffer.byteLength} bytes`);
   return arrayBuffer;

  } catch (e) {
   console.error("[Astra] DOM retrieval failed:", e);
   return null;
  }
 };

 window.Astra.retrieveMedia = async (msgId) => {
  console.log(`[Astra] retrieveMedia called for ${msgId}`);
  const Store = window.Astra.initializeEngine();
  const repo = Store.MessageRepo || Store.MsgRepo;
  let msgIdObj = msgId;
  if (typeof msgId === 'string' && Store.MessageIdentity && Store.MessageIdentity.fromString) {
   try { msgIdObj = Store.MessageIdentity.fromString(msgId); } catch(e) {}
  }

  const msg = repo.get(msgIdObj) || (await repo.getMessagesById([msgId]))?.messages?.[0];
  if (!msg) {
   console.warn("msg not found in repo");
   return null;
  }

  let decryptedMedia = null;

  // --- STRATEGY 1: Internal DownloadManager (Preferred for full quality) ---
  if (msg.directPath && msg.mediaKey && msg.encFilehash && msg.filehash) {
   try {
    const downloadManager = window.Store.DownloadManager;
    const downloadFunc = downloadManager?.downloadAndMaybeDecrypt;
    
    if (downloadFunc) {
      if (msg.mediaData.mediaStage != 'RESOLVED') {
       try {
        console.log("Downloading body...");
        await msg.downloadMedia({ downloadEvenIfExpensive: true, rmrReason: 1 });
       } catch (e) {
        console.warn("downloadMedia failed", e);
       }
      }

      console.log("Decrypting media...");
      const mockQpl = { addAnnotations: function() { return this; }, addPoint: function() { return this; } };
      decryptedMedia = await downloadFunc({
       directPath: msg.directPath,
       encFilehash: msg.encFilehash,
       filehash: msg.filehash,
       mediaKey: msg.mediaKey,
       mediaKeyTimestamp: msg.mediaKeyTimestamp || msg.t,
       type: msg.type,
       signal: (new AbortController).signal,
       downloadQpl: mockQpl
      });
    }
   } catch (err) {
    console.error("Strategy 1 (Internal) failed:", err);
   }
  }

  // --- STRATEGY 2: DOM Scraping (Fallback) ---
  if (!decryptedMedia) {
   console.log("Internal download failed or missing params. Switching to Strategy 2: DOM.");
   decryptedMedia = await window.Astra.retrieveMediaFromDOM(msgId);
  }

  if (!decryptedMedia) {
   console.error("All strategies failed. Cannot retrieve media.");
   return null;
  }

  console.log("Media retrieved. Caching...");
  // Chunking Strategy
  const streamId = `media_${Date.now()}_${Math.random().toString(36).slice(2)}`;
  window.Astra.mediaCache[streamId] = decryptedMedia;

  return {
   streamId: streamId,
   length: decryptedMedia.byteLength,
   mimetype: msg.mimetype,
   filename: msg.filename,
   filesize: msg.size
  };
 };
})();
"""

