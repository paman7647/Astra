# Astra Error Code Reference

## Error Code Format

All Astra error codes follow the format: `ASTRA-[CATEGORY]-[NUMBER]`

- **CATEGORY**: 3-4 letter category code
- **NUMBER**: 3-digit sequential number

## Error Categories

| Code | Category | Description |
|------|----------|-------------|
| BRW | Browser | Browser engine and automation errors |
| AUTH | Authentication | Login and authentication failures |
| SESS | Session | Session management issues |
| NET | Network | Network connectivity problems |
| PRO | Protocol | WhatsApp protocol communication |
| VAL | Validation | Input validation failures |
| CONF | Configuration | Setup and configuration errors |
| RES | Resource | System resource issues |
| MSG | Messaging | Message sending/receiving |
| MED | Media | Media upload/download |
| CNT | Contact | Contact management |
| GRP | Group | Group operations |

## Complete Error Code List

### Browser Errors (ASTRA-BRW-XXX)

| Code | Error | Severity | Description |
|------|-------|----------|-------------|
| ASTRA-BRW-001 | Browser Launch Failed | FATAL | Browser engine failed to start |
| ASTRA-BRW-002 | Browser Crashed | FATAL | Browser process terminated unexpectedly |
| ASTRA-BRW-003 | Page Navigation Failed | HIGH | Could not navigate to URL |
| ASTRA-BRW-004 | Selector Not Found | HIGH | Element not found on page |

### Authentication Errors (ASTRA-AUTH-XXX)

| Code | Error | Severity | Description |
|------|-------|----------|-------------|
| ASTRA-AUTH-001 | QR Generation Failed | HIGH | Could not generate QR code |
| ASTRA-AUTH-002 | QR Timeout | MEDIUM | QR code not scanned in time |
| ASTRA-AUTH-003 | Pairing Failed | HIGH | Phone number pairing failed |
| ASTRA-AUTH-004 | Auth Rejected | HIGH | WhatsApp rejected authentication |
| ASTRA-AUTH-005 | Already Logged In | MEDIUM | Account logged in elsewhere |

### Session Errors (ASTRA-SESS-XXX)

| Code | Error | Severity | Description |
|------|-------|----------|-------------|
| ASTRA-SESS-001 | Session Not Found | MEDIUM | Session data does not exist |
| ASTRA-SESS-002 | Session Corrupted | HIGH | Session data is corrupted |
| ASTRA-SESS-003 | Session Conflict | MEDIUM | Multiple instances using same session |
| ASTRA-SESS-004 | Session Invalidated | HIGH | WhatsApp invalidated the session |

### Network Errors (ASTRA-NET-XXX)

| Code | Error | Severity | Description |
|------|-------|----------|-------------|
| ASTRA-NET-001 | Connection Timeout | HIGH | Network connection timed out |
| ASTRA-NET-002 | Connection Refused | HIGH | Server refused connection |
| ASTRA-NET-003 | DNS Resolution Failed | HIGH | Could not resolve hostname |

### Protocol Errors (ASTRA-PRO-XXX)

| Code | Error | Severity | Description |
|------|-------|----------|-------------|
| ASTRA-PRO-001 | WhatsApp API Changed | FATAL | WhatsApp Web API incompatible |
| ASTRA-PRO-002 | Encryption Failed | FATAL | Message encryption failed |

### Validation Errors (ASTRA-VAL-XXX)

| Code | Error | Severity | Description |
|------|-------|----------|-------------|
| ASTRA-VAL-001 | Invalid Phone Number | LOW | Phone number format invalid |
| ASTRA-VAL-002 | Invalid File Path | LOW | File path does not exist |

### Configuration Errors (ASTRA-CONF-XXX)

| Code | Error | Severity | Description |
|------|-------|----------|-------------|
| ASTRA-CONF-001 | Missing Configuration | HIGH | Required config key not set |
| ASTRA-CONF-002 | Invalid Config Value | HIGH | Configuration value invalid |

### Resource Errors (ASTRA-RES-XXX)

| Code | Error | Severity | Description |
|------|-------|----------|-------------|
| ASTRA-RES-001 | Memory Exhausted | FATAL | Application memory limit exceeded |
| ASTRA-RES-002 | CPU Overload | HIGH | CPU usage too high |
| ASTRA-RES-003 | Disk Space Error | HIGH | Insufficient disk space |

### Messaging Errors (ASTRA-MSG-XXX)

| Code | Error | Severity | Description |
|------|-------|----------|-------------|
| MESSAGE_SEND_FAILED | Send Failed | MEDIUM | Message could not be sent |
| MESSAGE_TOO_LONG | Too Long | LOW | Message exceeds character limit |
| INVALID_RECIPIENT | Invalid Recipient | MEDIUM | Recipient ID invalid |

### Media Errors (ASTRA-MED-XXX)

| Code | Error | Severity | Description |
|------|-------|----------|-------------|
| MEDIA_UPLOAD_FAILED | Upload Failed | MEDIUM | Media upload failed |
| MEDIA_TOO_LARGE | File Too Large | MEDIUM | File exceeds size limit |
| MEDIA_UNSUPPORTED_FORMAT | Unsupported Format | MEDIUM | File format not supported |

### Contact Errors (ASTRA-CNT-XXX)

| Code | Error | Severity | Description |
|------|-------|----------|-------------|
| CONTACT_NOT_FOUND | Not Found | MEDIUM | Contact does not exist |
| PROFILE_UPDATE_FAILED | Update Failed | MEDIUM | Profile update rejected |

### Group Errors (ASTRA-GRP-XXX)

| Code | Error | Severity | Description |
|------|-------|----------|-------------|
| GROUP_NOT_FOUND | Not Found | MEDIUM | Group does not exist |
| INSUFFICIENT_PERMISSIONS | Permission Denied | MEDIUM | Insufficient permissions |
| GROUP_PARTICIPANT_LIMIT | Limit Reached | MEDIUM | Group member limit reached |

### Rate Limiting (ASTRA-RATE-XXX)

| Code | Error | Severity | Description |
|------|-------|----------|-------------|
| RATE_LIMIT_EXCEEDED | Rate Limited | MEDIUM | Too many requests |

## Usage Example

```python
from astra.utils.logging import error_codes

# Create error with standardized code
error = error_codes.create_browser_launch_failed_error(
 engine="chromium",
 reason="Binary not found"
)

# Error code is: ASTRA-BRW-001
print(error.context.error_code)

# Get full diagnostic report
print(error.get_diagnostic_report())
```
