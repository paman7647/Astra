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

 window.Astra.processStickerMetadata = async (dataB64, options = {}) => {
   const { stickerName, stickerAuthor } = options;
   if (!stickerName && !stickerAuthor) return dataB64;

   console.log('[Astra] Injecting sticker metadata:', { stickerName, stickerAuthor });
   
   // Convert base64 to Uint8Array
   const bin = window.atob(dataB64);
   const buf = new Uint8Array(bin.length);
   for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);

   // Metadata structure (based on whatsapp-web.js EXIF format)
   const json = JSON.stringify({
     'sticker-pack-name': stickerName || 'Astra',
     'sticker-pack-publisher': stickerAuthor || 'Astra Userbot',
     'emojis': options.emojis || ['✨']
   });

   const exifData = new TextEncoder().encode(json);
   const len = exifData.length;
   
   // Crafting a minimal WebP EXIF chunk (Simplified implementation)
   // In a real scenario, this would involve full WebP chunk parsing.
   // For now, we rely on the bridge's sendMedia to handle the raw buffer.
   // However, WA Web's internal prepRawMedia often overrides this.
   // If the user Bot handles the conversion to WebP, we should inject here.
   
   return dataB64; // Fallback: let internal WA handle it if possible, or refine this.
 };

 window.Astra.chunkedUploads = {};

 window.Astra.initChunkedUpload = (id, totalSize) => {
  window.Astra.chunkedUploads[id] = {
   buffer: new Uint8Array(totalSize),
   offset: 0,
   totalSize: totalSize
  };
  return true;
 };

 window.Astra.pushChunk = (id, dataB64) => {
  const session = window.Astra.chunkedUploads[id];
  if (!session) throw new Error("Astra: Upload session not found: " + id);
  
  const bin = window.atob(dataB64);
  const view = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) {
   session.buffer[session.offset + i] = bin.charCodeAt(i);
  }
  session.offset += bin.length;
  return { offset: session.offset, total: session.totalSize };
 };

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

   let file;
  if (media.uploadId && window.Astra.chunkedUploads[media.uploadId]) {
   const session = window.Astra.chunkedUploads[media.uploadId];
   const blob = new Blob([session.buffer], { type: mimetype });
   file = new File([blob], media.filename || 'media', { type: mimetype, lastModified: Date.now() });
   delete window.Astra.chunkedUploads[media.uploadId];
  } else {
   // Inject sticker metadata if needed
   let rawData = media.data;
   if (options.asSticker && (options.stickerName || options.stickerAuthor)) {
     rawData = await window.Astra.processStickerMetadata(rawData, options);
   }
   file = window.Astra.base64ToFile({ ...media, data: rawData });
  }

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

   try {
    const p1 = (await Store.SendMessage.addAndSendMsgToChat(target, msg))[0];
    await p1;
   } catch (sendErr) {
    console.error('[Astra] sendMedia send error:', sendErr);
    throw sendErr;
   }

   const serialized = key && (key._serialized || (typeof key === 'string' ? key : (key && key.id ? (key.id._serialized || key.id) : null)));
   return {
    id: serialized || id,
    body: msg.body || msg.caption || "",
    type: msg.type,
    isSent: true,
    timestamp: msg.t
   };
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

 window.Astra.addFavoriteSticker = async function(stickerId) {
  console.log("Astra: addFavoriteSticker called", stickerId);
  const Store = window.Astra.initializeEngine();
  const repo = Store.MsgRepo || Store.MessageRepo;
  const msg = repo.get(stickerId) || await repo.find(stickerId);
  if (!msg) throw new Error("Astra: Sticker message not found: " + stickerId);
  
  if (Store.FavoriteSticker && Store.FavoriteSticker.addFavoriteSticker) {
   return await Store.FavoriteSticker.addFavoriteSticker(msg);
  } else if (Store.Sticker && Store.Sticker.addFavoriteSticker) {
   return await Store.Sticker.addFavoriteSticker(msg);
  }
  throw new Error("Astra: FavoriteSticker module not found");
 };

 console.log("Astra Media Bridge v2 Loaded");

})();
"""

