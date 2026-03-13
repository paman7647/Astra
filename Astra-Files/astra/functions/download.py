# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
JavaScript implementation for Media Downloading and Retrieval.
"""

DOWNLOAD_CODE = r"""
(function() {
  window.Astra = window.Astra || {};
  window.Astra.mediaCache = window.Astra.mediaCache || {};

  window.Astra.readMediaChunk = async (id, offset, length) => {
    const buffer = window.Astra.mediaCache[id];
    if (!buffer) return null;
    
    // Use subarray for zero-copy view
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
      
      // 0. Scroll message into view
      try {
        const msg = window.Store.Msg.get(msgId);
        if (msg && window.Store.Cmd && window.Store.Cmd.scrollToMessage) {
          window.Store.Cmd.scrollToMessage(msg);
          await new Promise(r => setTimeout(r, 700));
        }
      } catch (e) {}

      // 1. Find the message container
      let msgElement = document.querySelector(`div[data-id="${msgId}"]`) || 
                      document.querySelector(`div[data-id*="${msgId.split('_').pop()}"]`);
      
      if (!msgElement) {
        const rows = Array.from(document.querySelectorAll('#main [role="row"]'));
        msgElement = rows.find(r => r.getAttribute('data-id') === msgId || r.innerHTML.includes(msgId.split('_').pop()));
      }

      if (!msgElement) return null;

      // 2. Find the media element
      const mediaElement = Array.from(msgElement.querySelectorAll('img, video')).find(el => el.src && el.src.startsWith('blob:'));
      if (!mediaElement) return null;

      const blobUrl = mediaElement.src;
      const response = await fetch(blobUrl);
      const blob = await response.blob();
      const buffer = await blob.arrayBuffer();
      return new Uint8Array(buffer);

    } catch (e) {
      console.error("[Astra] DOM retrieval failed:", e);
      return null;
    }
  };

  window.Astra.retrieveMedia = async (msgId) => {
    if (typeof msgId !== 'string') return null;
    console.log(`[Astra] retrieveMedia: ${msgId}`);
    const Store = window.Astra.initializeEngine();
    const repo = Store.MessageRepo || Store.MsgRepo;
    
    // --- Phase 1: Resolve Message Object ---
    let msg = null;
    
    // Try 1: Direct lookup (works for full serialized IDs)
    if (typeof msgId === 'string' && Store.MessageIdentity && Store.MessageIdentity.fromString) {
      try {
        const key = Store.MessageIdentity.fromString(msgId);
        msg = repo.get(key);
      } catch(e) {}
    }
    
    // Try 2: Direct string lookup
    if (!msg) msg = repo.get(msgId);
    
    // Try 3: getMessagesById API
    if (!msg) {
      try {
        const result = await repo.getMessagesById([msgId]);
        msg = result?.messages?.[0];
      } catch(e) {}
    }
    
    // Try 4: Short stanza ID scan (critical for quoted messages)
    if (!msg && typeof msgId === 'string') {
      const shortId = msgId.includes('_') ? msgId.split('_').pop() : msgId;
      console.log(`[Astra] retrieveMedia: Scanning store for short ID: ${shortId}`);
      const models = repo.getModelsArray ? repo.getModelsArray() : (repo.models || []);
      msg = models.find(m => 
        m.id && (m.id.id === shortId || m.id._serialized === msgId || m.id.id === msgId)
      );
      if (msg) console.log(`[Astra] retrieveMedia: Found via store scan: ${msg.id._serialized}`);
    }
    
    // Try 5: Search through all loaded chats
    if (!msg && Store.Chat) {
      const shortId = msgId.includes('_') ? msgId.split('_').pop() : msgId;
      const chats = Store.Chat.getModelsArray ? Store.Chat.getModelsArray() : (Store.Chat.models || []);
      for (const chat of chats) {
        if (msg) break;
        if (!chat.msgs) continue;
        const msgs = chat.msgs.getModelsArray ? chat.msgs.getModelsArray() : (chat.msgs.models || []);
        msg = msgs.find(m => m.id && (m.id.id === shortId || m.id._serialized === msgId));
      }
      if (msg) console.log(`[Astra] retrieveMedia: Found via chat scan: ${msg.id._serialized}`);
    }

    if (!msg) {
      console.error(`[Astra] retrieveMedia: Message not found for ${msgId}`);
      return null;
    }

    let decryptedMedia = null;

    // Strategy 1: Internal DownloadManager
    if (msg.directPath && msg.mediaKey && msg.encFilehash && msg.filehash) {
      try {
        const downloadManager = window.Store.DownloadManager;
        const downloadFunc = downloadManager?.downloadAndMaybeDecrypt;
        
        if (downloadFunc) {
          if (msg.mediaData && msg.mediaData.mediaStage != 'RESOLVED') {
            await msg.downloadMedia({ downloadEvenIfExpensive: true, rmrReason: 1 });
          }

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
        console.error("[Astra] DownloadManager retrieval failed:", err);
      }
    }
    
    // Strategy 2: msg.downloadMedia() direct
    if (!decryptedMedia && msg.downloadMedia) {
      try {
        const result = await msg.downloadMedia({ downloadEvenIfExpensive: true, rmrReason: 1 });
        if (result) {
          // Check if mediaData now has the blob
          if (msg.mediaData && msg.mediaData.mediaBlob) {
            const blob = msg.mediaData.mediaBlob.forResume ? msg.mediaData.mediaBlob.forResume() : msg.mediaData.mediaBlob;
            if (blob instanceof Blob || (blob && blob.slice)) {
              const ab = await blob.arrayBuffer();
              decryptedMedia = new Uint8Array(ab);
            }
          }
        }
      } catch (err) {
        console.error("[Astra] msg.downloadMedia fallback failed:", err);
      }
    }

    // Strategy 3: DOM Scraping Fallback
    if (!decryptedMedia) {
      const domId = msg.id?._serialized || msgId;
      decryptedMedia = await window.Astra.retrieveMediaFromDOM(domId);
    }

    if (!decryptedMedia) return null;

    // Chunking Cache
    const streamId = `media_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    
    let finalBuffer = decryptedMedia;
    if (decryptedMedia instanceof ArrayBuffer) {
      finalBuffer = new Uint8Array(decryptedMedia);
    }
    
    window.Astra.mediaCache[streamId] = finalBuffer;

    return {
      streamId: streamId,
      length: finalBuffer.byteLength,
      mimetype: msg.mimetype,
      filename: msg.filename,
      filesize: msg.size
    };
  };
})();
"""
