import requests
import json
import time

# 测试前端调用逻辑
BASE_URL = "http://localhost:8000"

def test_frontend_logic():
    """模拟前端调用逻辑，测试实际任务执行"""
    
    print("=== 模拟前端调用测试 ===")
    
    # 模拟当前状态
    brief = "设计一款简约风格的智能台灯"
    
    print(f"当前brief: {brief}")
    print(f"brief长度: {len(brief)}字符")
    
    # 测试1: AI创意补全
    print("\n--- 测试AI创意补全 ---")
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/ai/autocomplete",
            json={"brief": brief, "model_name": "models/gemma-3-12b-it"},
            timeout=60  # 60秒超时
        )
        duration = time.time() - start_time
        
        print(f"状态码: {response.status_code}")
        print(f"耗时: {duration:.2f}秒")
        
        if response.status_code == 200:
            data = response.json()
            if "expanded_brief" in data:
                expanded = data["expanded_brief"]
                print(f"✅ 成功扩展brief")
                print(f"扩展后长度: {len(expanded)}字符")
                print(f"扩展倍数: {len(expanded)/len(brief):.1f}x")
                # 显示前200字符
                preview = expanded[:200] + "..." if len(expanded) > 200 else expanded
                print(f"预览: {preview}")
            else:
                print(f"❌ 响应格式错误: {data}")
        else:
            print(f"❌ API错误: {response.text}")
            
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时 (>60秒)")
    except Exception as e:
        print(f"❌ 异常错误: {e}")
    
    # 测试2: 推荐标签
    print("\n--- 测试推荐标签 ---")
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/api/ai/tags",
            json={"brief": brief, "model_name": "models/gemini-2.5-flash-lite"},
            timeout=30  # 30秒超时
        )
        duration = time.time() - start_time
        
        print(f"状态码: {response.status_code}")
        print(f"耗时: {duration:.2f}秒")
        
        if response.status_code == 200:
            data = response.json()
            if "tags" in data and isinstance(data["tags"], list):
                tags = data["tags"]
                print(f"✅ 成功获取标签: {tags}")
                print(f"标签数量: {len(tags)}")
            else:
                print(f"❌ 响应格式错误: {data}")
        else:
            print(f"❌ API错误: {response.text}")
            
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时 (>30秒)")
    except Exception as e:
        print(f"❌ 异常错误: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_frontend_logic()