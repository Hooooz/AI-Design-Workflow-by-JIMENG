import requests
import json
import time

# 优化后端响应时间的测试
BASE_URL = "http://localhost:8000"

def test_optimized_calls():
    """测试优化后的API调用"""
    
    print("=== 测试优化后的API调用 ===")
    
    brief = "设计一款简约风格的智能台灯"
    
    # 测试1: 使用gemma-3-12b-it模型（用户指定的补全任务模型）
    print(f"\n--- 测试AI创意补全 (models/gemma-3-12b-it) ---")
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/ai/autocomplete",
            json={"brief": brief, "model_name": "models/gemma-3-12b-it"},
            timeout=60
        )
        duration = time.time() - start_time
        
        print(f"状态码: {response.status_code}")
        print(f"耗时: {duration:.2f}秒")
        
        if response.status_code == 200:
            data = response.json()
            if "expanded_brief" in data:
                print(f"✅ 成功获取扩展内容 ({len(data['expanded_brief'])} 字符)")
            else:
                print(f"❌ 响应格式错误")
        else:
            print(f"❌ API错误: {response.text}")
            
    except Exception as e:
        print(f"❌ 异常: {e}")
    
    # 测试2: 使用gemini-2.5-flash-lite模型（用户指定的总结任务模型）
    print(f"\n--- 测试推荐标签 (models/gemini-2.5-flash-lite) ---")
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/ai/tags",
            json={"brief": brief, "model_name": "models/gemini-2.5-flash-lite"},
            timeout=30
        )
        duration = time.time() - start_time
        
        print(f"状态码: {response.status_code}")
        print(f"耗时: {duration:.2f}秒")
        
        if response.status_code == 200:
            data = response.json()
            if "tags" in data:
                print(f"✅ 成功获取标签: {data['tags']}")
            else:
                print(f"❌ 响应格式错误")
        else:
            print(f"❌ API错误: {response.text}")
            
    except Exception as e:
        print(f"❌ 异常: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_optimized_calls()