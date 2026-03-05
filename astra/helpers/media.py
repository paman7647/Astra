# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

import os
import subprocess
import base64
import tempfile
import shutil
import logging

logger = logging.getLogger("Media")

def get_ffmpeg_path():
 """Locates the FFmpeg executable."""
 ffmpeg_path = os.environ.get('FFMPEG_PATH', 'ffmpeg')
 try:
  subprocess.run([ffmpeg_path, '-version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
  return ffmpeg_path
 except Exception:
  # Fallback to common paths
  search_paths = [
   '/usr/local/bin/ffmpeg',
   '/usr/bin/ffmpeg',
   '/opt/homebrew/bin/ffmpeg'
  ]
  for path in search_paths:
   if os.access(path, os.X_OK):
    return path
 return None

def convert_to_mp4(input_bytes: bytes, is_gif: bool = False) -> bytes:
 """Converts media to WhatsApp-compatible MP4 (or GIF-mode MP4)."""
 ffmpeg_path = get_ffmpeg_path()
 if not ffmpeg_path:
  logger.warning("FFmpeg not found. Skipping conversion.")
  return input_bytes

 with tempfile.TemporaryDirectory() as tmp_dir:
  input_path = os.path.join(tmp_dir, "input")
  output_path = os.path.join(tmp_dir, "output.mp4")

  with open(input_path, "wb") as f:
   f.write(input_bytes)

  command = [
   ffmpeg_path, '-y',
   '-i', input_path,
   '-movflags', 'faststart',
   '-pix_fmt', 'yuv420p',
   '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
   '-f', 'mp4'
  ]

  if is_gif:
   command.extend(['-an']) # Remove audio for GIFs

  command.append(output_path)

  try:
   subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
   with open(output_path, "rb") as f:
    return f.read()
  except Exception as e:
   logger.error(f"FFmpeg conversion failed: {e}")
   return input_bytes
