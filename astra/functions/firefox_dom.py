# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

FIREFOX_DOM_CODE = r"""
(function() {
 window.Astra = window.Astra || {};

 // Specialized Drawer Finder for Firefox (Targeting the Sidebar specifically)
 window.Astra.getActiveDrawer = () => {
  const isVisible = (el) => {
   if (!el) return false;
   const style = window.getComputedStyle(el);
   if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
   const rect = el.getBoundingClientRect();
   return rect.width > 0 && rect.height > 0;
  };

  // Find all scrollable containers and pick the leftmost one (sidebar)
  const scrollables = Array.from(document.querySelectorAll('div[scrollable="true"]')).filter(isVisible);

  // Exclude the main chat list (usually has id="pane-side")
  const drawers = scrollables.filter(el => !el.closest('#pane-side') && el.getBoundingClientRect().x < 200);

  // Sort by z-index or pick the first one visible on the left
  if (drawers.length > 0) return drawers[0];

  // Backup: data-testid
  const leftDrawer = document.querySelector('[data-testid="drawer-left"]');
  if (isVisible(leftDrawer)) return leftDrawer;

  // Fallback: search for header content
  return Array.from(document.querySelectorAll('header, h1, h2')).find(h => {
    const rect = h.getBoundingClientRect();
    return rect.x < 300 && isVisible(h);
  })?.closest('div[class*="x"]') || null;
 };

 // Robust Sidebar Navigator for Firefox (No data-testid)
 window.Astra.ensureSidebar = async (label, open = true) => {
  console.log(`[Astra-Firefox] ensureSidebar: ${label} (open=${open})`);

  const isVisible = (el) => {
   if (!el) return false;
   const style = window.getComputedStyle(el);
   if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
   const rect = el.getBoundingClientRect();
   return rect.width > 0 && rect.height > 0;
  };

  const findButton = () => {
   // Firefox uses aria-label exclusively (no testid on sidebar buttons)
   const btn = document.querySelector(`button[aria-label="${label}" i]`) ||
      document.querySelector(`[role="button"][aria-label="${label}" i]`) ||
      Array.from(document.querySelectorAll('button[aria-label]')).find(b => b.ariaLabel.toLowerCase().includes(label.toLowerCase()));
   return isVisible(btn) ? btn : null;
  };

  const checkIsOpen = () => {
   const drawer = window.Astra.getActiveDrawer();
   if (!drawer) return false;

   // Firefox often uses H2 in the sidebar drawer header
   const header = drawer.querySelector('h1, h2, header');
   if (header && header.innerText.toLowerCase().includes(label.toLowerCase())) return true;

   // Special case for Settings sub-pages
   if (label.toLowerCase() === 'settings') {
    const text = (drawer.innerText || "").toLowerCase();
    return ['settings', 'privacy', 'account', 'chats', 'theme'].some(term => text.includes(term));
   }
   return false;
  };

  let isOpen = checkIsOpen();

  if (open) {
   if (isOpen) return;
   const btn = findButton();
   if (btn) {
    btn.click();
    await new Promise(r => setTimeout(r, 2000));
   } else {
    console.error(`[Astra-Firefox] Sidebar button ${label} not found!`);
   }
  } else if (!open && isOpen) {
   const drawer = window.Astra.getActiveDrawer();
   const closeBtn = drawer ? (drawer.querySelector('button[aria-label="Back"]') ||
          drawer.querySelector('button[aria-label="Close"]')) : null;
   if (closeBtn) {
    closeBtn.click();
    await new Promise(r => setTimeout(r, 1000));
   }
  }
 };

 // Override Profile access to be direct
 const originalGetProfileDOM = window.Astra.getProfileDOM;
 window.Astra.getProfileDOM = async () => {
  console.log('[Astra-Firefox] Direct Profile Access...');
  await window.Astra.ensureSidebar('Profile', true);

  const info = { name: "", about: "" };
  const nameLabel = document.querySelector('div[data-testid="profile-section-name"]');
  if (nameLabel) info.name = nameLabel.innerText.split('\n').pop();

  const aboutLabel = document.querySelector('div[data-testid="profile-section-about"]');
  if (aboutLabel) info.about = aboutLabel.innerText.split('\n').pop();

  // Fallbacks
  if (!info.name) {
    const spans = Array.from(document.querySelectorAll('span[aria-label="Click to edit Name"]'));
    if (spans.length > 0) info.name = spans[0].parentElement.innerText.split('\n')[0];
  }

  await window.Astra.ensureSidebar('Profile', false);
  return info;
 };

 const originalUpdateProfileDOM = window.Astra.updateProfileDOM;
 window.Astra.updateProfileDOM = async (type, value) => {
  console.log(`[Astra-Firefox] Direct Profile Update: ${type} -> ${value}`);
  await window.Astra.ensureSidebar('Profile', true);

  const label = type === 'name' ? "Click to edit Name" : "Click to edit About";
  const editBtn = document.querySelector(`span[aria-label="${label}"]`);

  if (editBtn) {
   editBtn.click();
   await new Promise(r => setTimeout(r, 800));
   const input = document.querySelector('div[contenteditable="true"]');
   if (input) {
    input.innerText = "";
    input.focus();
    document.execCommand('insertText', false, value);
    await new Promise(r => setTimeout(r, 500));
    const saveBtn = document.querySelector('span[aria-label="Finish editing"]') ||
        document.querySelector('[data-testid="checkmark-penciled"]');
    if (saveBtn) saveBtn.click();
    await new Promise(r => setTimeout(r, 1500));
   }
  }
  await window.Astra.ensureSidebar('Profile', false);
  return true;
 };

})();
"""
