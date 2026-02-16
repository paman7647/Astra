import asyncio
import logging
import os
from astra import Client

# Configure logging
logging.basicConfig(level=logging.DEBUG)

async def test_pairing_transition():
    # Set the environment variable to force pairing mode
    os.environ["PHONEPAIRING"] = "True"
    
    # Use a dummy but valid-format international number
    dummy_phone = "919876543210"
    
    print(f"\n🚀 Testing Phone Pairing Transition (PHONEPAIRING=True)")
    print("---------------------------------------------------------")
    
    # We use a unique session ID to avoid cache interference
    async with Client(session_id="verify_pairing_final_v7", phone=dummy_phone, headless=False) as client:
        print("\n⏳ Monitoring terminal for pairing code...")
        
        # Wait up to 60 seconds
        for _ in range(30):
            await asyncio.sleep(2)
            # Authenticator should log the "Pairing mode requested" and then "PAIRING CODE"
            
    print("\n✅ Verification script finished.")

if __name__ == "__main__":
    try:
        asyncio.run(test_pairing_transition())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"❌ Error: {e}")
