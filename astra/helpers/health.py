# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

from typing import Dict, Any, List


class HealthMonitor:
 """
 Aggregates health telemetry from various framework components.
 """

 @staticmethod
 def consolidate(
  client_state: str,
  browser_health: Dict[str, Any],
  tasks_health: Dict[str, Any],
  gateway_ready: bool
 ) -> Dict[str, Any]:
  """Creates a unified health report."""

  # Determine overall status
  status = "HEALTHY"
  if client_state == "FAILED" or not browser_health.get("engine_active"):
   status = "UNHEALTHY"
  elif client_state == "DISCONNECTED":
   status = "DEGRADED"

  return {
   "status": status,
   "client": {
    "state": client_state,
    "gateway_ready": gateway_ready
   },
   "infrastructure": {
    "browser": browser_health,
    "tasks": tasks_health
   }
  }
