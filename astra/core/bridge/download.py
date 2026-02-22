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
    console.log(`[Astra] retrieveMedia: ${msgId}`);
    const Store = window.Astra.initializeEngine();
    const repo = Store.MessageRepo || Store.MsgRepo;
    
    let msgIdObj = msgId;
    if (typeof msgId === 'string' && Store.MessageIdentity && Store.MessageIdentity.fromString) {
      try { msgIdObj = Store.MessageIdentity.fromString(msgId); } catch(e) {}
    }

    let msg = repo.get(msgIdObj) || (await repo.getMessagesById([msgId]))?.messages?.[0];
    
    // Fallback: search by short ID if full ID lookup fails
    if (!msg) {
      const shortId = String(msgId).split('_').pop();
      msg = repo.getModelsArray().find(m => 
        m.id && (m.id._serialized === msgId || m.id.id === msgId || m.id.id === shortId || m.id.stanzaId === shortId)
      );
    }
    
    if (!msg) {
      console.warn(`[Astra] retrieveMedia cannot find message ${msgId}`);
      return null;
    }

    let decryptedMedia = null;

    // Strategy 1: Modern MediaBlob & LruMediaStore cache extraction
    if (msg.mediaData) {
      try {
        if (msg.downloadMedia && msg.mediaData.mediaStage !== 'RESOLVED') {
          await msg.downloadMedia({ downloadEvenIfExpensive: true, rmrReason: 1, isUserInitiated: true });
        }

        let blob = null;
        if (msg.mediaData.mediaBlob) {
           blob = msg.mediaData.mediaBlob.forceToBlob ? msg.mediaData.mediaBlob.forceToBlob() : (msg.mediaData.mediaBlob._blob || msg.mediaData.mediaBlob);
        }
        
        if (!blob && window.Store.LruMediaStore && msg.mediaData.filehash) {
           const cachedBuffer = await window.Store.LruMediaStore.get(msg.mediaData.filehash).catch(() => null);
           if (cachedBuffer) {
               blob = new Blob([cachedBuffer], { type: msg.mimetype || 'application/octet-stream' });
           }
        }
        
        if (blob && blob.arrayBuffer) {
          const buffer = await blob.arrayBuffer();
          decryptedMedia = new Uint8Array(buffer);
        }
      } catch (err) {
        console.error("Modern media retrieval failed:", err);
      }
    }

    // Strategy 1b: Legacy DownloadManager Fallback
    if (!decryptedMedia && msg.directPath && msg.mediaKey && msg.encFilehash && msg.filehash) {
      try {
        const downloadManager = window.Store.DownloadManager;
        const downloadFunc = downloadManager?.downloadAndMaybeDecrypt;
        
        if (downloadFunc) {
          const mockQpl = { addAnnotations: function() { return this; }, addPoint: function() { return this; } };
          const result = await downloadFunc({
            directPath: msg.directPath,
            encFilehash: msg.encFilehash,
            filehash: msg.filehash,
            mediaKey: msg.mediaKey,
            mediaKeyTimestamp: msg.mediaKeyTimestamp || msg.t,
            type: msg.type,
            signal: (new AbortController).signal,
            downloadQpl: mockQpl
          });
          if (result) decryptedMedia = new Uint8Array(result);
        }
      } catch (err) {
        console.error("Legacy retrieval failed:", err);
      }
    }

    // Strategy 2: DOM Scraping Fallback
    if (!decryptedMedia) {
      decryptedMedia = await window.Astra.retrieveMediaFromDOM(msgId);
    }

    if (!decryptedMedia) return null;

    // Chunking Cache
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
