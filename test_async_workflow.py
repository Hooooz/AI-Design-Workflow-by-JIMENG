
import requests
import time
import sys
import json

BASE_URL = "http://localhost:8000"
TEST_PROJECT_NAME = f"Test_Async_Run_{int(time.time())}"

def test_async_workflow():
    print(f"🚀 Starting Async Workflow Test: {TEST_PROJECT_NAME}")
    
    # 1. 触发异步全流程
    payload = {
        "project_name": TEST_PROJECT_NAME,
        "brief": "设计一款未来感的透明智能手机",
        "model_name": "gemini-2.5-flash-lite",
        "settings": {
            "image_count": 1,
            "persona": "科技极客"
        }
    }
    
    try:
        start_time = time.time()
        print("📡 Sending POST /api/workflow/run_all request...")
        resp = requests.post(f"{BASE_URL}/api/workflow/run_all", json=payload, timeout=5)
        
        if resp.status_code == 200:
            print(f"✅ Request Accepted: {resp.json()}")
        else:
            print(f"❌ Failed to start workflow: {resp.text}")
            return
            
        # 2. 轮询状态
        print("\n🔄 Polling status...")
        max_retries = 30 # 30 * 2s = 60s timeout for test
        for i in range(max_retries):
            status_resp = requests.get(f"{BASE_URL}/api/project/{TEST_PROJECT_NAME}")
            
            if status_resp.status_code != 200:
                print(f"⚠️ Project not ready yet ({i+1}/{max_retries})...")
                time.sleep(2)
                continue
                
            data = status_resp.json()
            status = data['metadata']['status']
            step = data['metadata']['current_step']
            
            print(f"   [{int(time.time() - start_time)}s] Status: {status} | Step: {step}")
            
            if status == "completed":
                print("\n✅ Workflow Completed Successfully!")
                print(f"   - Market Analysis Length: {len(data.get('market_analysis', ''))}")
                print(f"   - Visual Research Length: {len(data.get('visual_research', ''))}")
                print(f"   - Design Proposals Length: {len(data.get('design_proposals', ''))}")
                print(f"   - Images Generated: {len(data.get('images', []))}")
                return
            
            if status == "failed":
                print("\n❌ Workflow Failed!")
                return
                
            time.sleep(2)
            
        print("\n⚠️ Test Timeout (Background task might still be running)")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_async_workflow()
