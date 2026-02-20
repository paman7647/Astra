# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
JS logic and interaction scripts for Phone Pairing.
"""

JS_SCRIPTS = {
    "TRIGGER_PAIRING": """
        async () => {
            const sleep = (ms) => new Promise(r => setTimeout(r, ms));
            
            // 1. Find the Link Text
            // We look for "Link with phone number instead." (partial match)
            const findLink = () => {
                const xpath = "//div[contains(text(), 'Link with phone number instead')] | //span[contains(text(), 'Link with phone number instead')] | //div[contains(text(), 'Link with phone number')] | //span[contains(text(), 'Link with phone number')]";
                const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                return result.singleNodeValue;
            };

            let linkParams = null;
            for (let i = 0; i < 10; i++) {
                const el = findLink();
                if (el && el.offsetParent) { // Check visibility
                   linkParams = el;
                   break; 
                }
                await sleep(500);
            }

            if (!linkParams) return false;

            // 2. Click Strategy
            // We try to find the clickable ancestor or just click the element itself
            console.log("[Astra] Found Pairing Link:", linkParams);
            
            // Scroll into view gently
            linkParams.scrollIntoView({behavior: "smooth", block: "center"});
            await sleep(500);

            // Coordinate Click (Most Robust for React)
            const rect = linkParams.getBoundingClientRect();
            const x = rect.left + (rect.width / 2);
            const y = rect.top + (rect.height / 2);
            
            const clickEvent = new MouseEvent('click', {
                view: window,
                bubbles: true,
                cancelable: true,
                clientX: x,
                clientY: y
            });
            
            // Dispatch specifically to the element
            linkParams.dispatchEvent(clickEvent);
            
            // Also try standard click() on it and parent
            linkParams.click();
            if (linkParams.parentElement) linkParams.parentElement.click();

            return true;
        }
    """,

    "INJECT_PHONE": """
        async (phoneNumber) => {
            const sleep = (ms) => new Promise(r => setTimeout(r, ms));
            
            // User-defined formatting logic
            let formatted = phoneNumber.toString();
            // 1. If no +, check if it has 91
            if (!formatted.startsWith('+')) {
                if (formatted.startsWith('91')) {
                    // Has 91, missing +
                    formatted = '+' + formatted;
                } else {
                    // Missing 91 and +, append both (Default to India)
                    formatted = '+91' + formatted;
                }
            }
            
            console.log(`[Astra] Formatting: ${phoneNumber} -> ${formatted}`);

            // 1. Find Input
            // We search for the main phone input
            const selector = 'input[aria-label*="phone number"], input[type="text"]';
            let inputEl = null;
            
            for (let i = 0; i < 20; i++) {
                const inputs = document.querySelectorAll(selector);
                for (const inp of inputs) {
                    if (inp.offsetParent) { // Must be visible
                        inputEl = inp;
                        break;
                    }
                }
                if (inputEl) break;
                await sleep(500);
            }

            if (!inputEl) throw new Error("Phone input not found");
            
            inputEl.focus();
            await sleep(200);

            // 2. Injection Strategy: Full Type
            // Typing the full number with + often triggers auto-formatting in WA Web
            
            // Clear first just in case
            document.execCommand('selectAll', false, null);
            document.execCommand('delete', false, null);
            
            // Use execCommand for robustness
            document.execCommand('insertText', false, formatted);
            
            // Fallback validation
            await sleep(100);
            if (inputEl.value.replace(/\\D/g, '') !== formatted.replace(/\\D/g, '')) {
                // If value doesn't match (maybe input didn't accept +), try alternate
                 console.log("[Astra] execCommand mismatch, trying native setter...");
                 const setNativeValue = (element, value) => {
                    const valueSetter = Object.getOwnPropertyDescriptor(element, 'value').set;
                    const prototype = Object.getPrototypeOf(element);
                    const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
                    
                    if (valueSetter && valueSetter !== prototypeValueSetter) {
                        prototypeValueSetter.call(element, value);
                    } else {
                        valueSetter.call(element, value);
                    }
                };
                setNativeValue(inputEl, formatted);
                inputEl.dispatchEvent(new Event('input', { bubbles: true }));
            }
            
            inputEl.dispatchEvent(new Event('change', { bubbles: true }));
            await sleep(500);
            
            // 3. Click Next
            const clickNext = () => {
                const buttons = Array.from(document.querySelectorAll('button'));
                let nextBtn = buttons.find(b => b.innerText === 'Next' || b.innerText === 'Maju' || b.innerText === 'Suivant');
                
                if (!nextBtn) {
                     const divs = Array.from(document.querySelectorAll('div[role="button"]'));
                     nextBtn = divs.find(b => b.innerText === 'Next' || b.innerText === 'Maju');
                }

                if (nextBtn) {
                    console.log("[Astra] Clicking Next button:", nextBtn);
                    nextBtn.click();
                    nextBtn.dispatchEvent(new MouseEvent('click', { view: window, bubbles: true, cancelable: true }));
                    return true;
                }
                return false;
            };

            if (!clickNext()) {
                setTimeout(clickNext, 1000);
            }
            
            // Enter key fallback
            inputEl.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', which: 13, bubbles: true }));
            
            return true;
        }
    """,

    "EXTRACT_CODE": """
        async () => {
            // Wait for code container
            const start = Date.now();
            while (Date.now() - start < 10000) {
                 // Strategy 1: data-link-code attribute
                 const dataEl = document.querySelector('[data-link-code]');
                 if (dataEl) {
                     const code = dataEl.getAttribute('data-link-code').replace(/,/g, '');
                     return code;
                 }

                 // Strategy 2: 8-character visually distinct text
                 // Often in spans with specific class or layout
                 // We look for 8 alphanums usually grouped
                 const spans = document.querySelectorAll('div[role="button"] span');
                 for (const span of spans) {
                     const text = span.innerText;
                     // Regex for format XXXX-XXXX or XXXXXXXX
                     if (/^[A-Z0-9]{4}-?[A-Z0-9]{4}$/.test(text)) {
                         return text.replace('-', ''); // Return purely alphanumeric
                     }
                 }
                 
                 await new Promise(r => setTimeout(r, 500));
            }
            return null;
        }
    """,

    "DETECT_STATE": """
        () => {
            const check = (s) => document.querySelector(s);
            const findByText = (text) => {
                return Array.from(document.querySelectorAll('span, div, button, h1, a'))
                            .find(el => el.innerText && el.innerText.includes(text));
            };

            // 1. High-fidelity engine check
            if (window.Store && window.Store.Stream) {
                const s = window.Store.Stream.state || (window.Store.Stream.Stream && window.Store.Stream.Stream.state);
                const m = window.Store.Stream.mode || (window.Store.Stream.Stream && window.Store.Stream.Stream.mode);
                if (s === 'CONNECTED' || m === 'MAIN') return "CONNECTED";
            }
            if (window.Store && window.Store.Conn && window.Store.Conn.isMain) return "CONNECTED";

            // 2. DOM Connectivity
            if (check('[data-testid="side"]') || check('#pane-side')) return "CONNECTED";
            if (check('[data-testid="startup-loading-screen"]')) return "LOADING";

            // 3. Auth Priority: ERRORS > CODE > PHONE > QR
            
            // Rate Limits / Errors (Prioritized!)
            // The dialog checks for specific text that appears when blocked
            if (findByText("You've guessed too many times") || findByText('Too many attempts')) return "RATE_LIMITED";

            if (check('[data-link-code]') || findByText('Enter code on phone')) return "LOGIN_CODE";
            
            const isPhoneInput = check('input[aria-label*="phone number"]') || 
                                 check('input[aria-label*="Type your phone number"]') ||
                                 check('input[type="tel"]') || 
                                 check('input[type="text"]') && findByText('Enter phone number');

            if (isPhoneInput) return "LOGIN_PHONE";

            if (check('canvas') || check('[data-testid="qrcode"]') || check('[data-ref]')) return "LOGIN_QR";
            if (findByText('Scan the QR code') || findByText('Link with phone number') || findByText('Log in with phone number') || findByText('Link with phone number instead')) return "LOGIN_QR";

            return "UNKNOWN";
        }
    """
}

def format_pairing_code(code: str) -> str:
    """Formats 8-char code into XXXX-XXXX for terminal display."""
    if not code or len(code) != 8:
        return code
    return f"{code[:4]}-{code[4:]}"
