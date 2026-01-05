# Packet Counter Fix V2 - Stale Response Handling

**Date:** 2024-12-08 (Updated)  
**Version:** scl_protocol v0.1.1

## Problem Analysis

The original fix had a critical flaw in the resync logic. When receiving a response with a packet number that doesn't match what we sent, there are TWO different scenarios:

### Scenario 1: Controller is AHEAD (Controller > Us)
**Example:** We send packet 18, controller responds with packet 20

**Cause:** We're behind the controller (we missed packets or got out of sync)

**Solution:** Sync UP to controller's value
```python
self.packet_num = last_resp_packet_num - 1  # Set to 19, next increment → 20
```

### Scenario 2: Received STALE Response (Controller < Us)  
**Example:** We send packet 45, controller responds with packet 44

**Cause:** This is a STALE packet from the socket buffer, not the actual response to our packet

**Problem with old logic:**
- We were treating this as "controller is behind"
- We resynced DOWN to packet 43
- Next loop sent packet 44 again
- But controller already processed 44 and moved to 45!
- Result: Controller ignores duplicate packet 44 → TIMEOUT

**Correct solution:** DON'T resync! Just retry the SAME packet number
```python
self.packet_num -= 1  # Undo increment, next loop will send same number again
```

## The Fix

### Code Changes (controller.py lines 292-319)

```python
if not found_correct_packet:
    # Analyze the mismatch to determine appropriate action
    if last_resp_packet_num is not None:
        if last_resp_packet_num > self.packet_num:
            # Controller is AHEAD - we're behind, need to catch up
            logger.warning("Packet counter out of sync. Sent %d, controller at %d. Resyncing...", ...)
            self._flush_socket_buffer()
            self.packet_num = last_resp_packet_num - 1  # Sync up
            continue
            
        elif last_resp_packet_num < self.packet_num:
            # Received STALE response - controller hasn't responded yet
            logger.warning("Received stale response %d (expected %d). Retrying...", ...)
            self._flush_socket_buffer()
            self.packet_num -= 1  # Retry same packet
            continue
```

### Key Improvements

1. **Distinguishes between sync scenarios**
   - Ahead: controller moved forward without us
   - Stale: we received old buffered response

2. **Different handling for each**
   - Ahead → Sync up to controller
   - Stale → Retry same packet number

3. **Clear logging messages**
   - "Packet counter out of sync" = Controller ahead
   - "Received stale response" = Buffered response

## Example Flow: Stale Response (Fixed)

### Before Fix (BROKEN):
```
1. Send packet 45
2. Receive response 44 (stale from buffer)
3. Resync to 43 (44-1)
4. Loop: increment to 44
5. Send packet 44
6. Controller ignores (already processed 44)
7. TIMEOUT ✗
```

### After Fix (WORKING):
```
1. Send packet 45
2. Receive response 44 (stale from buffer)
3. Detect: 44 < 45 (stale!)
4. Flush buffer
5. Decrement to 44
6. Loop: increment to 45
7. Send packet 45 again
8. Controller responds with 45 ✓
```

## Testing

### Test Case: Upload with Stale Responses

**Observed in sf-led-manager logs:**
```
Packet counter out of sync. Sent 45, received 44. Resyncing...
[then timeout]
```

**Root cause:** Old logic treated this as "controller behind" and resynced DOWN, causing duplicate packet sends.

**After fix:** Should detect stale response and retry same packet number.

### Verification Commands

```bash
# Test basic connection
cd /Users/matthias.peplow/Development/sf-led_anzeige
python3 scripts/test_connection.py
# Result: ✓ PASSED

# Test with real upload (from sf-led-manager)
# Upload file via web interface
# Watch logs for "Received stale response" messages
```

## Important Notes

### When Stale Responses Occur

Stale responses typically happen when:
1. Multiple commands sent rapidly
2. Socket buffer contains old responses
3. Controller is slower to respond than we are to send
4. Network delays cause packet reordering

### The Socket Buffer Flush

Both scenarios call `_flush_socket_buffer()` to clear any remaining stale packets before continuing. This is critical to prevent cascading failures.

### Filename Length Limitation

Remember: Controller has 16-character limit for **full path** including subdirectory!
```python
# TOO LONG (20 chars)
"P99/test_upload.png"  # ✗

# CORRECT (12 chars)
"P99/TEST.PNG"  # ✓
```

## Related Issues

### Buffer Write Errors

If you see:
```
Buffer write verification failed: expected offset=0, length=1024, got offset=0, length=1
```

This is NOT a packet counter issue. This indicates:
- Controller received command correctly
- But response indicates only 1 byte written instead of 1024
- Possible causes:
  - Controller buffer full
  - Controller in wrong state
  - File system error

### Solution
- Ensure controller has space
- Check controller isn't locked by another process
- Verify file system isn't corrupted

## Migration from V1

If you're upgrading from the first fix:

**V1 behavior:** Resynced on ANY mismatch (broken for stale responses)  
**V2 behavior:** Distinguishes ahead vs. stale (correct)

**Action required:** None - just use latest code

## Version History

- **v0.1.1-rc1:** Initial packet counter fix (incomplete)
- **v0.1.1-rc2:** Fixed stale response handling (current)

## Files Modified

- `scl_protocol/controller.py` (lines 292-319)
- This document

## Next Steps

1. Test with sf-led-manager uploads
2. Monitor for "Received stale response" messages
3. Verify no more timeouts after stale responses
4. Update to final v0.1.1 release
