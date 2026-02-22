# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module provides the AccountMethods mixin for the Astra Client.
"""

import logging
from typing import Optional, Dict, Any, TYPE_CHECKING
from ...errors import (
 ProfileUpdateError, StatusPostError, PrivacyError,
 BlockError, ProfileReadError,
)

if TYPE_CHECKING:
 from ..client import Client

logger = logging.getLogger("Astra.Account")

class AccountMethods:
 """
 API for Privacy and Account settings.
 """

 def __init__(self, client: 'Client'):
  self._client = client

 async def set_name(self, name: str) -> bool:
  """
  Sets the profile name.

  Raises:
   ProfileUpdateError: [E5002] If the profile name update failed.
  """
  try:
   return await self._client.api.set_profile_name(name)
  except Exception as e:
   raise ProfileUpdateError(f"Failed to set profile name: {e}") from e

 async def set_about_text(self, text: str) -> bool:
  """
  Sets the profile 'About' text content.

  Raises:
   ProfileUpdateError: [E5002] If the about text update failed.
  """
  try:
   return await self._client.api.set_about_text(text)
  except Exception as e:
   raise ProfileUpdateError(f"Failed to set about text: {e}") from e

 async def update_profile_pic(self, media: str) -> bool:
  """
  Updates the profile picture.

  Args:
   media: Base64 encoded image data.

  Raises:
   ProfileUpdateError: [E5002] If the profile picture update failed.
  """
  try:
   return await self._client.api.update_profile_pic(media)
  except Exception as e:
   raise ProfileUpdateError(f"Failed to update profile picture: {e}") from e

 async def post_status(self, text: str) -> bool:
  """
  Posts a text status update to your stories.

  Raises:
   StatusPostError: [E5010] If status posting failed.
  """
  try:
   return await self._client.api.send_status(text)
  except Exception as e:
   raise StatusPostError(f"Failed to post status: {e}", cause=e) from e

 async def set_last_seen(self, value: str) -> bool:
  """
  Sets 'Last Seen' privacy.
  Values: 'all', 'contacts', 'contact_blacklist', 'none'

  Raises:
   PrivacyError: [E5020] If the privacy update failed.
  """
  try:
   return await self._client.api.set_privacy('last_seen', value)
  except Exception as e:
   raise PrivacyError(f"Failed to set last_seen privacy: {e}") from e

 async def set_profile_pic(self, value: str) -> bool:
  """
  Sets 'Profile Photo' privacy.
  Values: 'all', 'contacts', 'contact_blacklist', 'none'

  Raises:
   PrivacyError: [E5020] If the privacy update failed.
  """
  try:
   return await self._client.api.set_privacy('profile_pic', value)
  except Exception as e:
   raise PrivacyError(f"Failed to set profile_pic privacy: {e}") from e

 async def set_about(self, value: str) -> bool:
  """
  Sets 'About' privacy.
  Values: 'all', 'contacts', 'contact_blacklist', 'none'

  Raises:
   PrivacyError: [E5020] If the privacy update failed.
  """
  try:
   return await self._client.api.set_privacy('about', value)
  except Exception as e:
   raise PrivacyError(f"Failed to set about privacy: {e}") from e

 async def set_status(self, value: str) -> bool:
  """
  Sets 'Status' privacy.
  Values: 'all', 'contacts', 'contact_blacklist'

  Raises:
   PrivacyError: [E5020] If the privacy update failed.
  """
  try:
   return await self._client.api.set_privacy('status', value)
  except Exception as e:
   raise PrivacyError(f"Failed to set status privacy: {e}") from e

 async def set_read_receipts(self, enabled: bool) -> bool:
  """
  Toggles 'Read Receipts'.

  Raises:
   PrivacyError: [E5020] If the privacy update failed.
  """
  try:
   return await self._client.api.set_privacy('read_receipts', enabled)
  except Exception as e:
   raise PrivacyError(f"Failed to set read_receipts: {e}") from e

 async def get_settings(self) -> Dict[str, Any]:
  """
  Retrieves current privacy settings.

  Raises:
   PrivacyError: [E5020] If reading privacy settings failed.
  """
  try:
   return await self._client.api.get_privacy_settings()
  except Exception as e:
   raise PrivacyError(f"Failed to get privacy settings: {e}") from e
