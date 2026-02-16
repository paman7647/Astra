# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module provides the GroupMethods mixin for the Astra Client.
"""

import logging
from typing import List, Optional, TYPE_CHECKING
from ...errors import (
 GroupCreateError, GroupMemberError, GroupJoinError,
 GroupInfoError, GroupSettingsError, ErrorCode,
)

if TYPE_CHECKING:
 from ..client import Client

logger = logging.getLogger("Astra.Group")

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
   raise GroupMemberError(f"Failed to add members to {group_id}: {e}", code=ErrorCode.GRP_ADD_FAILED) from e

 async def remove_members(self, group_id: str, members: List[str]) -> bool:
  """
  Kicks participants from a group.

  Raises:
   GroupMemberError: [E4003] If removing members failed.
  """
  try:
   return await self._client.api.remove_members(group_id, members)
  except Exception as e:
   raise GroupMemberError(f"Failed to remove members from {group_id}: {e}", code=ErrorCode.GRP_REMOVE_FAILED) from e

 async def leave(self, group_id: str) -> bool:
  """
  Leaves a group.

  Raises:
   GroupInfoError: [E4007] If leaving failed.
  """
  try:
   return await self._client.bridge.call("leaveGroup", group_id)
  except Exception as e:
   raise GroupInfoError(f"Failed to leave group {group_id}: {e}") from e

 async def get_invite_link(self, group_id: str) -> str:
  """
  Generates a public invite link for the group.

  Raises:
   GroupInfoError: [E4007] If link generation failed.
  """
  try:
   return await self._client.api.get_invite_link(group_id)
  except Exception as e:
   raise GroupInfoError(f"Failed to get invite link for {group_id}: {e}") from e

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
