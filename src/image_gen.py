import os
import sys
import time
import shutil
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ImageGenService:
    def __init__(self, server_script_path=None):
        self.server_script_path = server_script_path
        self.temp_dir = os.path.join("/tmp", f"img_gen_{int(time.time())}")
        os.makedirs(self.temp_dir, exist_ok=True)

        # 获取 Token
        self.jimeng_token = os.getenv("JIMENG_API_TOKEN", "").strip()

        # Supabase Storage 配置
        self.supabase_url = os.getenv("SUPABASE_URL", "").strip()
        self.supabase_key = os.getenv("SUPABASE_KEY", "").strip()
        self.supabase_bucket = "project-images"
        self.use_storage = bool(self.supabase_url and self.supabase_key)

        if self.use_storage:
            print(f"ℹ️ Supabase Storage: 已配置")

        # 设置即梦模块路径 - 优先使用 src/jimeng（生产环境）
        self.jimeng_path = None
        jimeng_in_src = os.path.join(os.path.dirname(__file__), "jimeng")
        if os.path.exists(os.path.join(jimeng_in_src, "__init__.py")):
            self.jimeng_path = jimeng_in_src
        else:
            # 备选路径
            possible_paths = [
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "..",
                    "test_workspace",
                    "image-gen-server",
                    "proxy",
                ),
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "test_workspace",
                    "image-gen-server",
                    "proxy",
                ),
                os.path.join(
                    os.getcwd(), "test_workspace", "image-gen-server", "proxy"
                ),
            ]
            for path in possible_paths:
                if os.path.exists(os.path.join(path, "jimeng", "__init__.py")):
                    self.jimeng_path = path
                    break

        # 确定模式
        if self.jimeng_token and self.jimeng_path:
            self.mode = "direct"
            print(f"ℹ️ 即梦模块: 直接调用模式")
            print(f"   - Token: {self.jimeng_token[:10]}...")
            print(f"   - 路径: {self.jimeng_path}")
        elif self.jimeng_token:
            self.mode = "http"
            print(f"⚠️ 即梦模块未找到，尝试 HTTP 模式")
        else:
            self.mode = "disabled"
            print(f"⚠️ 图片服务未配置:")
            print(
                f"   - JIMENG_API_TOKEN: {'已设置' if self.jimeng_token else '未设置'}"
            )
            print(f"   - 即梦模块: {'找到' if self.jimeng_path else '未找到'}")

    def __del__(self):
        try:
            if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def upload_to_supabase(self, local_path, project_name, filename):
        """上传图片到 Supabase Storage"""
        if not self.use_storage:
            return None

        try:
            from services.db_service import get_project_id

            # 统一使用 db_service 中的 ID 生成逻辑
            storage_folder = get_project_id(project_name)
            file_path = f"{storage_folder}/{filename}"
            url = f"{self.supabase_url}/storage/v1/object/{self.supabase_bucket}/{file_path}"

            with open(local_path, "rb") as f:
                file_data = f.read()

            headers = {
                "Authorization": f"Bearer {self.supabase_key}",
                "Content-Type": "image/jpeg",
            }

            response = requests.post(url, headers=headers, data=file_data, timeout=60)

            if response.status_code in [200, 201]:
                # 获取公开访问 URL
                public_url = f"{self.supabase_url}/storage/v1/object/public/{self.supabase_bucket}/{file_path}"
                print(f"✅ 已上传到 Supabase Storage: {file_path}")
                return public_url
            else:
                print(f"❌ 上传失败: {response.status_code} - {response.text[:100]}")
                return None
        except Exception as e:
            print(f"❌ Supabase 上传异常: {e}")
            return None

    def generate_image(self, prompt, output_dir, session_id=None):
        """生成图片"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎨 即梦生成: {prompt[:50]}...")

        if self.mode == "disabled":
            print("❌ 图片生成服务未配置")
            return None

        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 构造输出文件名
        timestamp = int(time.time())
        filename = f"jimeng_{timestamp}.jpg"
        output_path = os.path.abspath(os.path.join(output_dir, filename))

        if self.mode == "direct":
            return self._generate_direct(
                prompt, output_path, filename, session_id, output_dir
            )
        elif self.mode == "http":
            return self._generate_http(
                prompt, output_path, filename, session_id, output_dir
            )
        else:
            return None

    def _generate_direct(
        self, prompt, output_path, filename, session_id=None, output_dir=None
    ):
        """直接调用即梦模块"""
        try:
            # 添加模块路径
            if self.jimeng_path and self.jimeng_path not in sys.path:
                sys.path.insert(0, self.jimeng_path)

            from jimeng.images import generate_images as jimeng_generate

            token = session_id or self.jimeng_token
            print(f"[DEBUG] 使用 Token: {token[:10]}...")

            # 调用即梦生成图片
            image_urls = jimeng_generate(
                model="jimeng-2.1",
                prompt=prompt,
                width=1024,
                height=1024,
                sample_strength=0.5,
                negative_prompt="",
                refresh_token=token,
            )

            print(f"[DEBUG] 获取 {len(image_urls)} 个 URL")

            if image_urls:
                # 下载第一张图片
                url = image_urls[0]
                print(f"[DEBUG] 下载: {url[:80]}...")

                response = requests.get(url, timeout=60)
                if response.status_code == 200:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                    print(f"✅ 已保存本地: {output_path}")

                    # 上传到 Supabase Storage
                    project_name = (
                        os.path.basename(output_dir) if output_dir else "unknown"
                    )
                    storage_url = self.upload_to_supabase(
                        output_path, project_name, filename
                    )

                    if storage_url:
                        return storage_url

                    print(f"❌ 上传 Supabase 失败，且当前模式要求必须使用云端存储")
                    return None
                else:
                    print(f"❌ 下载失败: {response.status_code}")

            return None

        except ImportError as e:
            print(f"❌ 导入失败: {e}")
            print(f"[DEBUG] 尝试 HTTP 模式...")
            self.mode = "http"
            return self._generate_http(
                prompt, output_path, filename, session_id, output_dir
            )

        except Exception as e:
            print(f"❌ 调用失败: {type(e).__name__}: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _generate_http(
        self, prompt, output_path, filename, session_id=None, output_dir=None
    ):
        """HTTP 模式调用图片生成服务"""
        http_url = os.getenv("IMAGE_GEN_SERVER_URL", "").strip()
        if not http_url:
            print("❌ IMAGE_GEN_SERVER_URL 未配置")
            return None

        try:
            token = session_id or self.jimeng_token

            payload = {
                "prompt": prompt,
                "file_name": filename,
                "save_folder": self.temp_dir,
            }

            print(f"[DEBUG] HTTP 请求: {http_url}/generate")
            response = requests.post(
                f"{http_url}/generate",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120,
            )

            print(f"[DEBUG] 响应: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                if result.get("success") and result.get("images"):
                    # HTTP 服务返回的是本地路径
                    src_path = result["images"][0]
                    if os.path.exists(src_path):
                        shutil.copy2(src_path, output_path)
                        print(f"✅ 已保存本地: {output_path}")

                        # 上传到 Supabase Storage
                        project_name = (
                            os.path.basename(output_dir) if output_dir else "unknown"
                        )
                        storage_url = self.upload_to_supabase(
                            output_path, project_name, filename
                        )

                        if storage_url:
                            return storage_url

                        print(f"❌ 上传 Supabase 失败，且当前模式要求必须使用云端存储")
                        return None

            print(f"❌ 生成失败: {response.text[:200]}")
            return None

        except requests.exceptions.Timeout:
            print("❌ HTTP 请求超时")
            return None

        except Exception as e:
            print(f"❌ HTTP 调用失败: {e}")
            return None
