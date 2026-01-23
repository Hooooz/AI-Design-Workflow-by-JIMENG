import time
import json
import urllib.request
import urllib.error
import sys

BASE_URL = "https://web-production-d9bfe.up.railway.app"
PROJECT_NAME = f"AutoTest_Fix_{int(time.time())}"
BRIEF = "设计一款赛博朋克风格的机械键盘，带有全息投影功能，霓虹灯配色，铝合金机身"

def api_request(method, endpoint, data=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}

    if data:
        json_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=json_data, headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error {e.code}: {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        print(f"❌ Request Error: {e}")
        return None

def verify_url(url, context):
    if not url:
        print(f"  ❌ {context}: URL 为空")
        return False
    if "yojpsrakcqkyeaoxqlxg.supabase.co" in url and url.startswith("https://"):
        print(f"  ✅ {context}: URL 格式正确")
        return True
    else:
        print(f"  ❌ {context}: URL 格式错误 -> {url}")
        return False

def main():
    print(f"🚀 开始全流程测试 | 项目名: {PROJECT_NAME}")
    print(f"🎯 目标 API: {BASE_URL}")
    print("-" * 60)

    # 1. 触发任务
    print("Step 1: 触发 run_all 异步任务...")
    start_req_time = time.time()
    res = api_request("POST", "/api/workflow/run_all", {
        "project_name": PROJECT_NAME,
        "brief": BRIEF,
        "model_name": "gemini-2.5-flash",
        "image_count": 2  # 为了测试快一点，生成2张
    })

    if not res:
        print("❌ 任务触发失败")
        return

    req_duration = time.time() - start_req_time
    print(f"✅ 接口响应耗时: {req_duration:.2f}s (预期应 < 2s)")
    print(f"   状态: {res.get('status')} | 消息: {res.get('message')}")

    if req_duration > 5:
        print("⚠️ 警告: 接口响应时间过长，异步优化可能未生效！")

    # 2. 轮询进度
    print("\nStep 2: 开始轮询进度 (Timeout: 180s)...")
    start_poll_time = time.time()

    last_step = ""
    while True:
        if time.time() - start_poll_time > 180:
            print("❌ 测试超时 (180s)")
            break

        project = api_request("GET", f"/api/project/{PROJECT_NAME}")
        if not project:
            time.sleep(5)
            continue

        metadata = project.get("metadata", {})
        status = metadata.get("status")
        current_step = metadata.get("current_step")

        if current_step != last_step:
            print(f"   🔄 当前步骤: {current_step} (Status: {status})")
            last_step = current_step

        if status == "completed":
            print(f"\n✅ 任务完成！总耗时: {time.time() - start_poll_time:.1f}s")
            verify_results(project)
            break
        elif status == "failed":
            print("\n❌ 任务执行失败！")
            break

        time.sleep(3)

def verify_results(project):
    print("\nStep 3: 验证数据完整性与链接修复情况")
    print("-" * 60)

    # 验证 1: 顶层 images 数组
    images = project.get("images", [])
    print(f"📸 顶层图片数量: {len(images)}")
    for i, img in enumerate(images):
        verify_url(img, f"Images[{i}]")

    # 验证 2: Design Proposals (JSON)
    dp_raw = project.get("design_proposals", "")
    print(f"\n📄 Design Proposals 检查:")
    try:
        if isinstance(dp_raw, str):
            dp = json.loads(dp_raw)
        else:
            dp = dp_raw

        prompts = dp.get("prompts", [])
        print(f"   找到 {len(prompts)} 个方案")
        for i, p in enumerate(prompts):
            path = p.get("image_path", "")
            verify_url(path, f"Proposal[{i}] Image")

    except Exception as e:
        print(f"   ❌ JSON 解析失败: {e}")
        print(f"   Raw Content: {dp_raw[:100]}...")

    # 验证 3: Markdown 文本中的链接
    print(f"\n📝 Markdown 链接检查 (Regex Fix验证):")

    md_fields = {
        "market_analysis": project.get("market_analysis", ""),
        "visual_research": project.get("visual_research", ""),
        "full_report": project.get("full_report", "")
    }

    import re
    link_pattern = r'\!\[.*?\]\((.*?)\)'

    for field, content in md_fields.items():
        links = re.findall(link_pattern, content)
        if links:
            print(f"   Field '{field}': 找到 {len(links)} 个图片链接")
            for i, link in enumerate(links):
                verify_url(link, f"{field} Link[{i}]")
        else:
            print(f"   Field '{field}': 无图片链接 (正常)")

if __name__ == "__main__":
    main()
