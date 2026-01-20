import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_api_endpoints():
    """测试所有API端点，模拟前端调用"""
    
    print("=== 测试API端点连接 ===")
    
    # 测试健康检查
    try:
        health_res = requests.get(f"{BASE_URL}/")
        print(f"✅ 健康检查: {health_res.status_code}")
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
        return
    
    # 测试项目列表
    try:
        projects_res = requests.get(f"{BASE_URL}/api/projects")
        print(f"✅ 项目列表: {projects_res.status_code}")
    except Exception as e:
        print(f"❌ 项目列表失败: {e}")
    
    # 测试AI创意补全
    print("\n=== 测试AI创意补全 ===")
    test_brief = "设计一款简约风格的智能台灯"
    
    try:
        start_time = time.time()
        autocomplete_res = requests.post(
            f"{BASE_URL}/api/ai/autocomplete",
            json={"brief": test_brief, "model_name": "models/gemma-3-12b-it"},
            timeout=60
        )
        duration = time.time() - start_time
        
        print(f"✅ AI创意补全状态: {autocomplete_res.status_code}")
        print(f"✅ 响应时间: {duration:.2f}秒")
        
        if autocomplete_res.status_code == 200:
            data = autocomplete_res.json()
            if "expanded_brief" in data:
                print(f"✅ 成功获取扩展内容: {len(data['expanded_brief'])} 字符")
            else:
                print(f"❌ 响应格式错误: {data}")
        else:
            print(f"❌ 错误响应: {autocomplete_res.text}")
            
    except requests.exceptions.Timeout:
        print(f"❌ AI创意补全超时 (>60秒)")
    except Exception as e:
        print(f"❌ AI创意补全失败: {e}")
    
    # 测试推荐标签
    print("\n=== 测试推荐标签 ===")
    
    try:
        start_time = time.time()
        tags_res = requests.post(
            f"{BASE_URL}/api/ai/tags",
            json={"brief": test_brief, "model_name": "models/gemini-2.5-flash-lite"},
            timeout=30
        )
        duration = time.time() - start_time
        
        print(f"✅ 推荐标签状态: {tags_res.status_code}")
        print(f"✅ 响应时间: {duration:.2f}秒")
        
        if tags_res.status_code == 200:
            data = tags_res.json()
            if "tags" in data and isinstance(data["tags"], list):
                print(f"✅ 成功获取标签: {data['tags']}")
            else:
                print(f"❌ 响应格式错误: {data}")
        else:
            print(f"❌ 错误响应: {tags_res.text}")
            
    except requests.exceptions.Timeout:
        print(f"❌ 推荐标签超时 (>30秒)")
    except Exception as e:
        print(f"❌ 推荐标签失败: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_api_endpoints()