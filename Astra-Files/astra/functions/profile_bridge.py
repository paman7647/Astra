# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

PROFILE_CODE = r"""
(function() {
 window.Astra = window.Astra || {};

 window.Astra.getProfileDOM = async () => {
  console.log('[Astra] Fetching Profile info (DOM)...');
  await window.Astra.ensureSidebar('Settings', true);

  const drawer = (typeof window.Astra.getActiveDrawer === 'function') ?
      window.Astra.getActiveDrawer() :
      (document.querySelector('div[scrollable="true"][class*="x1n2onr6"]') || document.querySelector('[data-testid="drawer-left"]'));

  if (!drawer) throw new Error("Astra: Settings drawer not found");

  const profileRow = Array.from(drawer.querySelectorAll('div[role="button"], button, [role="link"]')).find(el => {
   const text = (el.innerText || "").toLowerCase();
   return !text.includes('account') && !text.includes('privacy') && !text.includes('chats') && text.length > 0;
  });

  if (profileRow) {
   profileRow.click();
   await new Promise(r => setTimeout(r, 1500));
  }

  const info = {
   name: "",
   about: ""
  };

  const nameLabel = document.querySelector('div[data-testid="profile-section-name"]');
  if (nameLabel) info.name = nameLabel.innerText.split('\n').pop();

  const aboutLabel = document.querySelector('div[data-testid="profile-section-about"]');
  if (aboutLabel) info.about = aboutLabel.innerText.split('\n').pop();

  // If data-testid fails, fallback to semantic search
  if (!info.name) {
    const spans = Array.from(document.querySelectorAll('span[aria-label="Click to edit Name"]'));
    if (spans.length > 0) info.name = spans[0].parentElement.innerText.split('\n')[0];
  }

  console.log(`[Astra] Profile found: ${info.name} | ${info.about}`);
  await window.Astra.ensureSidebar('Settings', false);
  return info;
 };

 window.Astra.updateProfileDOM = async (type, value) => {
  console.log(`[Astra] Updating Profile ${type} -> ${value}`);
  await window.Astra.ensureSidebar('Settings', true);

  const drawer = (typeof window.Astra.getActiveDrawer === 'function') ?
      window.Astra.getActiveDrawer() :
      (document.querySelector('div[scrollable="true"][class*="x1n2onr6"]') || document.querySelector('[data-testid="drawer-left"]'));

  if (!drawer) throw new Error("Astra: Settings drawer not found");

  const profileRow = Array.from(drawer.querySelectorAll('div[role="button"], button, [role="link"]')).find(el => {
   const text = (el.innerText || "").toLowerCase();
   return !text.includes('account') && !text.includes('privacy') && !text.includes('chats') && text.length > 0;
  });

  if (profileRow) {
   profileRow.click();
   await new Promise(r => setTimeout(r, 1500));
  }

  // Find Edit Span
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

    // Click Checkmark
    const saveBtn = document.querySelector('span[aria-label="Finish editing"]') ||
        document.querySelector('[data-testid="checkmark-penciled"]');
    if (saveBtn) saveBtn.click();
    await new Promise(r => setTimeout(r, 1500));
   }
  } else {
   throw new Error(`Astra: Profile edit button for ${type} not found`);
  }

  await window.Astra.ensureSidebar('Settings', false);
  return true;
 };

})();
"""
