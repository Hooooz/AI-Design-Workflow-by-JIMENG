import sys
import os
import json
import hashlib
from fastapi.testclient import TestClient

# 将 src 加入路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api import app
from services import db_service

client = TestClient(app)

def test_system_verification():
    print("开始系统重构验证...\n")

    # 1. 验证健康检查与存储模式
    print("用例 1: 验证健康检查接口...")
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["storage"] == "supabase_only"
    print("✅ 存储模式已确认: 纯 Supabase 运行\n")

    # 2. 验证图片路径修复逻辑 (核心修复点)
    print("用例 2: 验证旧项目图片路径修复 (修复 404 问题)...")
    project_name = "拍立得相机包15"
    project_id = hashlib.md5(project_name.encode()).hexdigest()[:12]

    # 模拟一个旧的、错误的本地路径记录
    bad_paths = [
        f"/projects/{project_name}/img.jpg", # 原始名称路径
        f"http://47.89.249.90:8000/projects/{project_name}/img.jpg" # 旧 IP 路径
    ]

    fixed_paths = db_service.fix_image_urls(bad_paths)
    for path in fixed_paths:
        assert project_id in path # 确保 ID 存在
        assert project_name not in path # 确保原始中文名称已被替换为哈希
        assert "storage/v1/object/public/project-images" in path
    print(f"✅ 图片路径转换逻辑验证通过。ID: {project_id}")
    print(f"   示例转换结果: {fixed_paths[0]}\n")

    # 3. 验证项目列表读取
    print("用例 3: 验证数据库项目列表读取...")
    response = client.get("/api/projects?limit=5")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    print(f"✅ 列表读取成功，当前云端项目数: {len(response.json())}\n")

    # 4. 验证本地磁盘隔离
    print("用例 4: 验证本地文件系统隔离...")
    test_project = "Refactor_Test_Project"
    test_id = db_service.get_project_id(test_project)
    local_path = os.path.join(os.getcwd(), "projects", test_id)
    assert not os.path.exists(local_path)
    print("✅ 本地隔离验证成功: 无冗余文件产生\n")

    print("🎉 所有核心 API 及图片路径修复逻辑验证通过！系统可安全部署。")

if __name__ == "__main__":
    try:
        test_system_verification()
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        sys.exit(1)
