# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

DIAGNOSTIC_CODE = r"""
window.Astra.getDiagnostics = async function() {
 const Store = window.Astra.initializeEngine();
 const diag = {
  version: (window.Debug && window.Debug.VERSION) ? window.Debug.VERSION : "Unknown",
  user: (Store && Store.UserCredentials && typeof Store.UserCredentials.getMaybeMePnUser === 'function') ? (Store.UserCredentials.getMaybeMePnUser()?.toString() || "Unknown") : "Unknown",
  session: (Store && Store.SessionInfo) ? (Store.SessionInfo.wid?._serialized || Store.SessionInfo.me?._serialized || "Unknown") : "Unknown",
  chatCount: (Store && Store.ChatRepo && Store.ChatRepo.models) ? Store.ChatRepo.models.length : 0,
  stores: Object.keys(window.InternalStore || {}).length,
  userAgent: navigator.userAgent,
  timestamp: new Date().toISOString(),
  features: (Store && Store.Features && typeof Store.Features.getFeatures === 'function') ? Store.Features.getFeatures() : {},
  stream: (Store && Store.WAWebStreamModel && Store.WAWebStreamModel.Stream) ? {
   mode: Store.WAWebStreamModel.Stream.mode,
   state: Store.WAWebStreamModel.Stream.state,
   isOnline: Store.WAWebStreamModel.Stream.mode === 'MAIN'
  } : (Store && Store.Stream) ? {
   mode: Store.Stream.mode,
   state: Store.Stream.state,
   isOnline: Store.Stream.mode === 'MAIN'
  } : "Unknown"
 };
 return diag;
};

window.Astra.getDomSnippet = function(selector) {
 const el = document.querySelector(selector);
 if (!el) return "Not found";
 return el.outerHTML.substring(0, 1000);
};

window.Astra.getFullDom = function() {
 return document.documentElement.outerHTML;
};
"""
