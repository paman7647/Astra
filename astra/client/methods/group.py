# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module provides the GroupMethods mixin for the Astra Client.
"""

import logging
from typing import List, Optional, TYPE_CHECKING, Dict, Any
from ...errors import (
 GroupCreateError, GroupMemberError, GroupJoinError,
 GroupInfoError, GroupSettingsError, ErrorCode,
)
from ...models.chat import GroupInfo

if TYPE_CHECKING:
 from ..client import Client

logger = logging.getLogger("Group")

class GroupMethods:
 """
 API for Group administration.
 """

 def __init__(self, client: 'Client'):
  self._client = client

 async def create(self, title: str, participants: List[str]) -> str:
  """
  Creates a new group and returns the resulting JID.

  Raises:
   GroupCreateError: [E4001] If group creation failed.
  """
  try:
   return await self._client.api.create_group(title, participants)
  except Exception as e:
   logger.info(f"Failed to create group '{title}': {e}")
   raise GroupCreateError(f"Failed to create group '{title}': {e}", cause=e) from e

 async def add_members(self, group_id: str, members: List[str]) -> bool:
  """
  Adds participants to a group.

  Raises:
   GroupMemberError: [E4002] If adding members failed.
  """
  try:
   return await self._client.api.add_members(group_id, members)
  except Exception as e:
   logger.info(f"Failed to add members to {group_id}: {e}")
   raise GroupMemberError(f"Failed to add members to {group_id}: {e}", code=ErrorCode.GRP_ADD_FAILED) from e

 async def add_participants(self, group_id: str, members: List[str]) -> bool:
  """Alias for add_members"""
  return await self.add_members(group_id, members)

 async def remove_members(self, group_id: str, members: List[str]) -> bool:
  """
  Kicks participants from a group.

  Raises:
   GroupMemberError: [E4003] If removing members failed.
  """
  try:
   return await self._client.api.remove_members(group_id, members)
  except Exception as e:
   logger.info(f"Failed to remove members from {group_id}: {e}")
   raise GroupMemberError(f"Failed to remove members from {group_id}: {e}", code=ErrorCode.GRP_REMOVE_FAILED) from e

 async def remove_participants(self, group_id: str, members: List[str]) -> bool:
  """Alias for remove_members"""
  return await self.remove_members(group_id, members)

 async def leave(self, group_id: str) -> bool:
  """
  Leaves a group.

  Raises:
   GroupInfoError: [E4007] If leaving failed.
  """
  try:
   if hasattr(group_id, "serialized"):
    group_id_str = group_id.serialized
   else:
    group_id_str = str(group_id)
   return await self._client.bridge.call("leaveGroup", group_id_str)
  except Exception as e:
   raise GroupInfoError(f"Failed to leave group {group_id}: {e}") from e

 async def get_invite_link(self, group_id: str) -> str:
  """
  Generates a public invite link for the group.

  Raises:
   GroupInfoError: [E4007] If link generation failed.
  """
  try:
   if hasattr(group_id, "serialized"):
    group_id_str = group_id.serialized
   else:
    group_id_str = str(group_id)
   return await self._client.api.get_invite_link(group_id_str)
  except Exception as e:
   raise GroupInfoError(f"Failed to get invite link for {group_id}: {e}") from e

 async def revoke_invite_link(self, group_id: str) -> str:
  """
  Revokes the group invite link and returns the new one.
  """
  try:
   if hasattr(group_id, "serialized"):
    group_id_str = group_id.serialized
   else:
    group_id_str = str(group_id)
   return await self._client.bridge.call("revokeInviteLink", group_id_str)
  except Exception as e:
   raise GroupInfoError(f"Failed to revoke invite link for {group_id}: {e}") from e

 async def set_subject(self, group_id: str, subject: str) -> bool:
  """
  Updates the group subject/title.

  Raises:
   GroupSettingsError: [E4010] If update failed.
  """
  try:
   return await self._client.bridge.call("setGroupSubject", {"groupId": group_id, "subject": subject})
  except Exception as e:
   raise GroupSettingsError(f"Failed to set subject for {group_id}: {e}") from e

 async def set_description(self, group_id: str, description: str) -> bool:
  """
  Updates the group description.

  Raises:
   GroupSettingsError: [E4010] If update failed.
  """
  try:
   return await self._client.bridge.call("setGroupDescription", {"groupId": group_id, "description": description})
  except Exception as e:
   raise GroupSettingsError(f"Failed to set description for {group_id}: {e}") from e

 async def update_profile_pic(self, group_id: str, media: str) -> bool:
  """
  Updates the group profile picture.
 
  Args:
   group_id: The JID of the group.
   media: Base64 encoded image data.
 
  Raises:
   GroupSettingsError: [E4010] If the update failed.
  """
  try:
   return await self._client.api.update_group_pic(group_id, media)
  except Exception as e:
   raise GroupSettingsError(f"Failed to update group profile picture: {e}") from e

 async def promote_participants(self, group_id: str, members: List[str]) -> bool:
  """Promotes participants to admin status."""
  try:
   return await self._client.api.promote(group_id, members)
  except Exception as e:
   raise GroupMemberError(f"Failed to promote members in {group_id}: {e}") from e

 async def demote_participants(self, group_id: str, members: List[str]) -> bool:
  """Demotes participants from admin status."""
  try:
   return await self._client.api.demote(group_id, members)
  except Exception as e:
   raise GroupMemberError(f"Failed to demote members in {group_id}: {e}") from e

 async def get_info(self, group_id: str) -> GroupInfo:
  """Retrieves detailed info about a group."""
  try:
   from ...network.serializers import DataTransformer
   raw = await self._client.api.get_group_info(group_id)
   return DataTransformer.to_group_info(raw)
  except Exception as e:
   raise GroupInfoError(f"Failed to get info for {group_id}: {e}") from e
