"""Utility tools (QR Code reading/generation, Background Removal)."""

import os
import io
try:
    import qrcode
    from PIL import Image
except ImportError:
    qrcode = None

try:
    from pyzbar.pyzbar import decode as decode_qr
except ImportError:
    decode_qr = None

try:
    from rembg import remove as remove_bg
except ImportError:
    remove_bg = None

from . import *

@astra_command(
    name="qrgen",
    description="Generate a QR code from text.",
    category="Tools",
    aliases=["makeqr", "qrcode"],
    usage="<text>",
    owner_only=True,
)
async def qrgen_handler(client: Client, message: Message):
    """Generates a QR code."""
    if not qrcode:
        return await edit_or_reply(message, "Error: `qrcode` and `Pillow` libraries are missing. Run `pip install qrcode[pil]`.")

    text = " ".join(extract_args(message))
    if not text:
        return await edit_or_reply(message, "Usage: `.qrgen <text or URL>`")

    status = await edit_or_reply(message, "Generating QR code...")
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        bio = io.BytesIO()
        img.save(bio, format="PNG")
        bio.seek(0)
        
        # Save to temp file to send
        temp_path = "/tmp/astra_qr.png"
        with open(temp_path, "wb") as f:
            f.write(bio.read())

        await client.api.send_media(message.chat_id, temp_path, "image/png", caption=f"QR Code for: `{text}`")
        await status.delete()
        
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception as e:
        await status.edit(f"Error generating QR code: {e}")

@astra_command(
    name="qrread",
    description="Read a QR code from an image.",
    category="Tools",
    aliases=["readqr", "scanqr"],
    usage="(reply to image)",
    owner_only=True,
)
async def qrread_handler(client: Client, message: Message):
    """Scans a QR code from a replied image."""
    if not decode_qr or not qrcode:
        return await edit_or_reply(message, "Error: `pyzbar` or `Pillow` missing. Run `pip install pyzbar Pillow`.")
        
    if not message.has_quoted_msg or not message.quoted:
        return await edit_or_reply(message, "Reply to an image containing a QR code.")

    status = await edit_or_reply(message, "Scanning QR code...")
    try:
        media_path = await client.download_media(message.quoted)
        if not media_path:
            return await status.edit("Failed to download image.")

        img = Image.open(media_path)
        decoded = decode_qr(img)
        
        os.remove(media_path)
        
        if not decoded:
            return await status.edit("No QR code found in the image.")
            
        result = decoded[0].data.decode("utf-8")
        await status.edit(f"**QR Code Scanned:**\n\n`{result}`")
    except Exception as e:
        await status.edit(f"Error reading QR code: {e}")

@astra_command(
    name="rmbg",
    description="Remove the background from an image.",
    category="Tools",
    aliases=["removebg", "bgrm"],
    usage="(reply to image)",
    owner_only=True,
)
async def rmbg_handler(client: Client, message: Message):
    """Removes the background from an image using local ML (rembg)."""
    if not remove_bg:
        return await edit_or_reply(message, "Error: `rembg` is not installed. Run `pip install rembg`.")

    if not message.has_quoted_msg or not message.quoted:
        return await edit_or_reply(message, "Reply to an image to remove its background.")

    status = await edit_or_reply(message, "Removing background... (This may take a moment)")
    try:
        media_path = await client.download_media(message.quoted)
        if not media_path:
            return await status.edit("Failed to download image.")

        with open(media_path, "rb") as i:
            input_data = i.read()
            
        # Run background removal
        output_data = remove_bg(input_data)
        
        temp_out = "/tmp/astra_rmbg_out.png"
        with open(temp_out, "wb") as o:
            o.write(output_data)

        await client.api.send_media(message.chat_id, temp_out, "image/png")
        await status.delete()
        
        # Cleanup
        if os.path.exists(media_path):
            os.remove(media_path)
        if os.path.exists(temp_out):
            os.remove(temp_out)
            
    except Exception as e:
        await status.edit(f"Error removing background: {e}")
