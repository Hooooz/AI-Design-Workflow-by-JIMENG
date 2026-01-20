import os
import sys
import json
import time
import tempfile
import shutil
import requests
from datetime import datetime


logger = None


class ImageGenService:
    def __init__(self, server_script_path=None):
        global logger
        if logger is None:
            import logging

            logger = logging.getLogger(__name__)

        self.server_script_path = server_script_path
        self.temp_dir = tempfile.mkdtemp(prefix="img_gen_")

        # 检查是否配置了 HTTP 图片服务
        self.http_url = os.getenv("IMAGE_GEN_SERVER_URL", "").strip()
        if self.http_url:
            self.mode = "http"
            logger.info(f"使用 HTTP 图片服务: {self.http_url}")
        elif server_script_path and os.path.exists(server_script_path):
            self.mode = "local"
            logger.info(f"使用本地图片服务: {server_script_path}")
        else:
            self.mode = "disabled"
            logger.warning("图片服务未配置，图片生成功能已禁用")

    def __del__(self):
        try:
            if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def generate_image(self, prompt, output_dir, session_id=None):
        """
        生成图片 - 支持 HTTP 和本地两种模式
        """
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] 🎨 正在调用即梦生成图片，Prompt: {prompt[:50]}..."
        )

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

        if self.mode == "http":
            return self._generate_http(prompt, output_path, filename, session_id)
        else:
            return self._generate_local(prompt, output_path, filename, session_id)

    def _generate_http(self, prompt, output_path, filename, session_id=None):
        """HTTP 模式生成图片"""
        print(f"[DEBUG] HTTP 图片服务 URL: {self.http_url}")
        print(f"[DEBUG] 模式: {self.mode}")

        try:
            # 注入 Session ID 到环境变量
            headers = {"Content-Type": "application/json"}
            payload = {
                "prompt": prompt,
                "file_name": filename,
                "save_folder": self.temp_dir,
            }

            if session_id:
                os.environ["JIMENG_SESSION_ID"] = session_id
                print(f"[DEBUG] 使用 Session ID: {session_id[:10]}...")

            print(f"[DEBUG] 发送请求到 {self.http_url}/generate")
            response = requests.post(
                f"{self.http_url}/generate", json=payload, headers=headers, timeout=120
            )

            print(f"[DEBUG] 响应状态码: {response.status_code}")
            print(f"[DEBUG] 响应内容: {response.text[:200]}...")

            if response.status_code == 200:
                result = response.json()
                print(f"[DEBUG] 解析结果: {result}")
                if result.get("success") and result.get("image_path"):
                    src_path = result["image_path"]
                    print(f"[DEBUG] 图片路径: {src_path}")
                    if os.path.exists(src_path):
                        shutil.copy2(src_path, output_path)
                        print(f"✅ 图片已生成并保存至: {output_path}")
                        return output_path
                    else:
                        print(f"[DEBUG] 文件不存在: {src_path}")

            print(f"❌ HTTP 生成失败: {response.text}")
            return None

        except requests.exceptions.Timeout:
            print("❌ HTTP 请求超时 (120s)")
            return None
        except Exception as e:
            print(f"❌ HTTP 调用失败: {type(e).__name__}: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _generate_local(self, prompt, output_path, filename, session_id=None):
        """本地模式生成图片（原有逻辑）"""
        try:
            import subprocess

            safe_prompt = json.dumps(prompt)

            session_id_code = ""
            if session_id:
                session_id_code = f"os.environ['JIMENG_SESSION_ID'] = '{session_id}'"

            inline_script = f"""
import os
import sys
import json

{session_id_code}

work_dir = "{os.path.dirname(self.server_script_path)}"
if work_dir not in sys.path:
    sys.path.insert(0, work_dir)

try:
    from server import generate_image
    
    if hasattr(generate_image, 'fn'):
        func = generate_image.fn
    elif hasattr(generate_image, '__wrapped__'):
        func = generate_image.__wrapped__
    else:
        func = generate_image
    
    output_filename = "temp_generated_{int(time.time())}.jpg"
    output_folder = "{self.temp_dir}"
    
    result = func(prompt={safe_prompt}, file_name=output_filename, save_folder=output_folder)
    
    if result:
        print(f"IMAGE_PATH:{{result}}")
    else:
        expected_path = os.path.join(output_folder, output_filename)
        print(f"IMAGE_PATH:{{expected_path}}")
        
except Exception as e:
    print(f"ERROR:{{e}}", file=sys.stderr)
    sys.exit(1)
"""

            result = subprocess.run(
                [sys.executable, "-c", inline_script],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(self.server_script_path),
                timeout=120,
            )

            if result.returncode != 0:
                print(f"Error running Jimeng client: {result.stderr}")
                return None

            for line in result.stdout.splitlines():
                if "IMAGE_PATH:" in line:
                    raw_result = line.split("IMAGE_PATH:")[1].strip()
                    import re

                    json_match = re.search(r"\{.*\}", raw_result)
                    if json_match:
                        try:
                            data = json.loads(json_match.group(0))
                            if data.get("success") and data.get("images"):
                                src_path = data["images"][0]
                                if os.path.exists(src_path):
                                    shutil.copy2(src_path, output_path)
                                    print(f"✅ 图片已生成并保存至: {output_path}")
                                    return output_path
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass

                    if os.path.exists(raw_result):
                        shutil.copy2(raw_result, output_path)
                        print(f"✅ 图片已生成并保存至: {output_path}")
                        return output_path

            print(f"Warning: No image path found in output: {result.stdout}")
            return None

        except subprocess.TimeoutExpired:
            print("Error: Image generation timed out (120s)")
            return None
        except Exception as e:
            print(f"Error calling image gen service: {e}")
            return None

            # 解析输出
            for line in result.stdout.splitlines():
                if "IMAGE_PATH:" in line:
                    raw_result = line.split("IMAGE_PATH:")[1].strip()
                    # 尝试解析 JSON
                    import re

                    json_match = re.search(r"\{.*\}", raw_result)
                    if json_match:
                        try:
                            data = json.loads(json_match.group(0))
                            if data.get("success") and data.get("images"):
                                src_path = data["images"][0]
                                if os.path.exists(src_path):
                                    shutil.copy2(src_path, output_path)
                                    print(f"✅ 图片已生成并保存至: {output_path}")
                                    return output_path
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass

                    # 直接作为路径处理
                    if os.path.exists(raw_result):
                        shutil.copy2(raw_result, output_path)
                        print(f"✅ 图片已生成并保存至: {output_path}")
                        return output_path

            print(f"Warning: No image path found in output: {result.stdout}")
            return None

        except subprocess.TimeoutExpired:
            print("Error: Image generation timed out (120s)")
            return None
        except Exception as e:
            print(f"Error calling image gen service: {e}")
            return None
