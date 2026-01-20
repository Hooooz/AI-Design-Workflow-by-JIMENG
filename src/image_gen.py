import os
import sys
import subprocess
import json
import time
import tempfile
import shutil
from datetime import datetime

try:
    import asyncio
except ImportError:
    asyncio = None  # 对于同步函数，这个不应该影响


class ImageGenService:
    def __init__(self, server_script_path):
        self.server_script_path = server_script_path
        # 临时文件目录
        self.temp_dir = tempfile.mkdtemp(prefix="img_gen_")

    def __del__(self):
        """清理临时目录"""
        try:
            if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def generate_image(self, prompt, output_dir, session_id=None):
        """
        调用 MCP Server 生成图片（改进版：使用内存执行）
        """
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] 🎨 正在调用即梦生成图片，Prompt: {prompt[:50]}..."
        )

        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 构造输出文件名
        timestamp = int(time.time())
        filename = f"jimeng_{timestamp}.jpg"
        output_path = os.path.abspath(os.path.join(output_dir, filename))

        # 使用安全的 JSON 编码处理 prompt
        safe_prompt = json.dumps(prompt)

        # 注入 Session ID (如果提供)
        session_id_code = ""
        if session_id:
            session_id_code = f"os.environ['JIMENG_SESSION_ID'] = '{session_id}'"

        # 构建内联脚本（不写入临时文件）
        inline_script = f"""
import os
import sys
import json

# 设置 Session ID
{session_id_code}

# 设置工作目录
work_dir = "{os.path.dirname(self.server_script_path)}"
if work_dir not in sys.path:
    sys.path.insert(0, work_dir)

try:
    from server import generate_image
    
    # 获取正确的函数引用
    if hasattr(generate_image, 'fn'):
        func = generate_image.fn
    elif hasattr(generate_image, '__wrapped__'):
        func = generate_image.__wrapped__
    else:
        func = generate_image
    
    # 执行生成
    output_filename = "temp_generated_{timestamp}.jpg"
    output_folder = "{self.temp_dir}"
    
    if asyncio and asyncio.iscoroutinefunction(func):
        result = asyncio.run(func(prompt={safe_prompt}, file_name=output_filename, save_folder=output_folder))
    else:
        result = func(prompt={safe_prompt}, file_name=output_filename, save_folder=output_folder)
    
    # 返回结果
    if result:
        print(f"IMAGE_PATH:{{result}}")
    else:
        expected_path = os.path.join(output_folder, output_filename)
        if os.path.exists(expected_path):
            print(f"IMAGE_PATH:{{expected_path}}")
        else:
            print(f"IMAGE_PATH:{{expected_path}}")
            
except Exception as e:
    print(f"ERROR:{{e}}", file=sys.stderr)
    sys.exit(1)
"""

        try:
            # 直接执行内联脚本，不写入临时文件
            result = subprocess.run(
                [sys.executable, "-c", inline_script],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(self.server_script_path),
                timeout=120,  # 2分钟超时
            )

            if result.returncode != 0:
                print(f"Error running Jimeng client: {result.stderr}")
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
