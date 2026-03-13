# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

DOM_SCANNER_CODE = r"""
(function() {
 window.Astra = window.Astra || {};

 window.Astra.openChatDOM = async (chatId) => {
  console.log(`[Astra] openChatDOM: ${chatId}`);
  const idStr = (chatId && chatId._serialized) ? chatId._serialized : String(chatId);
  const cells = document.querySelectorAll('[data-testid="cell-frame-container"]');
  for (const cell of cells) {
   if (cell.innerHTML.includes(idStr)) {
    cell.click();
    await new Promise(r => setTimeout(r, 1000));
    return true;
   }
  }
  return false;
 };

 window.Astra.scanDOM = async (section) => {
  console.log(`[Astra] Starting deep DOM scan for section: ${section}`);
  const results = [];

  // Comprehensive attribute list to scan
  const attributes = ['data-testid', 'aria-label', 'role', 'title', 'id'];

  const walk = (node) => {
   if (node.nodeType === 1) { // Element node
    const entry = {
     tag: node.tagName.toLowerCase(),
     text: node.innerText ? node.innerText.substring(0, 50).trim() : '',
     attributes: {}
    };

    let hasImportantAttr = false;
    attributes.forEach(attr => {
     const val = node.getAttribute(attr);
     if (val) {
      entry.attributes[attr] = val;
      hasImportantAttr = true;
     }
    });

    if (hasImportantAttr) {
     results.push(entry);
    }
   }

   node.childNodes.forEach(walk);
  };

  // Select root based on section
  let root = document.body;
  if (section === 'chats') root = document.querySelector('[data-testid="chat-list"]') || document.querySelector('#pane-side') || document.body;
  if (section === 'settings') {
    await window.Astra.ensureSidebar('Settings', true);
    root = document.querySelector('#app > div > span:nth-child(4) > div') || document.body;
  }
  if (section === 'profile') {
    await window.Astra.ensureSidebar('Profile', true);
    root = document.querySelector('#app > div > span:nth-child(4) > div') || document.body;
  }

  walk(root);
  console.log(`[Astra] Scan complete for ${section}. Found ${results.length} stable nodes.`);
  return results;
 };

 window.Astra.generateDOMReport = async (section) => {
  const data = await window.Astra.scanDOM(section);
  let report = `Deep DOM Scan Report: ${section}\n`;
  report += `Generated at: ${new Date().toISOString()}\n`;
  report += `==========================================\n\n`;

  data.forEach((item, i) => {
   report += `Node ${i + 1}: <${item.tag}>\n`;
   if (item.text) report += ` Text: "${item.text}"\n`;
   Object.entries(item.attributes).forEach(([k, v]) => {
    report += ` ${k}: ${v}\n`;
   });
   report += `\n`;
  });

  return report;
 };
})();
"""
