import os
import subprocess
import json
import time
from datetime import datetime

class ImageGenService:
    def __init__(self, server_script_path):
        self.server_script_path = server_script_path
        
    def generate_image(self, prompt, output_dir):
        """
        调用 MCP Server 生成图片
        """
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎨 正在调用即梦生成图片，Prompt: {prompt[:50]}...")
        
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # 构造输出文件名
        timestamp = int(time.time())
        filename = f"jimeng_{timestamp}.jpg"
        output_path = os.path.abspath(os.path.join(output_dir, filename))
        
        # 构造调用命令
        # 使用 json.dumps 安全处理 prompt 中的特殊字符
        safe_prompt = json.dumps(prompt)
        
        tool_call_script = f"""
import sys
import os
import asyncio
import json

# 尝试导入 server 模块
try:
    # 动态添加路径以导入 server
    sys.path.append(os.path.dirname(r'{self.server_script_path}'))
    
    # 注意：我们这里不尝试自动安装 requests，因为 uv 环境管理严格
    # 我们假设用户环境（或 uv 临时环境）已经有了必要的依赖
    # 如果是 uv run 运行的，它应该使用 server.py 所在项目的依赖，或者我们在调用时指定 --with requests
    
    from server import generate_image
    # 如果 generate_image 是被 fastmcp 装饰的，它可能需要特殊调用方式
    # fastmcp 的 tool 装饰器通常保留了原始函数作为 __wrapped__ 属性，或者直接可调用
    # 检查是否是 FunctionTool 对象
    if hasattr(generate_image, 'fn'):
         func = generate_image.fn
    elif hasattr(generate_image, '__wrapped__'):
        func = generate_image.__wrapped__
    else:
        func = generate_image
        
    # 执行生成
    # 注意：generate_image 可能是 async 的
    # 根据错误提示，generate_image 需要 file_name 和 save_folder 参数
    # 我们构造一个临时输出路径
    import tempfile
    
    # 获取输出目录，这里我们简单地将图片保存到当前目录或临时目录
    # 因为我们最后会 print 图片路径，所以路径是什么不重要，只要能找到
    
    # 假设调用方式是 generate_image(prompt, file_name, save_folder)
    # 我们使用一个简单的文件名
    output_filename = "temp_generated.jpg"
    output_folder = os.getcwd()
    
    if asyncio.iscoroutinefunction(func):
        result = asyncio.run(func(prompt={safe_prompt}, file_name=output_filename, save_folder=output_folder))
    else:
        result = func(prompt={safe_prompt}, file_name=output_filename, save_folder=output_folder)
        
    # 如果函数返回了路径，直接使用
    # 如果没返回（即梦 server 可能只打印路径或返回 None），我们构造预期的路径
    if result:
        print(f"IMAGE_PATH:{{result}}")
    else:
        expected_path = os.path.join(output_folder, output_filename)
        if os.path.exists(expected_path):
             print(f"IMAGE_PATH:{{expected_path}}")
        else:
             print(f"IMAGE_PATH:{{expected_path}}") # 尝试返回预期路径

    
except Exception as e:
    print(f"ERROR:{{e}}")
"""
        # 将临时脚本写入文件
        client_script_path = os.path.join(os.path.dirname(__file__), "temp_jimeng_client.py")
        with open(client_script_path, "w", encoding="utf-8") as f:
            f.write("import os\n" + tool_call_script)
            
        try:
            # 使用 uv run 执行脚本，确保环境一致，并显式添加 requests, fastmcp, brotli 依赖
            cmd = ["uv", "run", "--with", "requests", "--with", "fastmcp", "--with", "brotli", client_script_path]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(self.server_script_path))
            
            if result.returncode != 0:
                print(f"Error running Jimeng client: {result.stderr}")
                return None
                
            # 解析输出
            for line in result.stdout.splitlines():
                if "IMAGE_PATH:" in line:
                    raw_result = line.split("IMAGE_PATH:")[1].strip()
                    # 尝试解析可能返回的 TextContent 对象字符串或 JSON
                    import re
                    # 提取 JSON 部分
                    json_match = re.search(r'\{.*\}', raw_result)
                    if json_match:
                        try:
                            data = json.loads(json_match.group(0))
                            if data.get("success") and data.get("images"):
                                src_path = data["images"][0] # 取第一张图
                                import shutil
                                if os.path.exists(src_path):
                                    shutil.copy2(src_path, output_path)
                                    print(f"✅ 图片已生成并保存至: {output_path}")
                                    return output_path
                        except json.JSONDecodeError:
                            pass
                    
                    # 如果不是 JSON，尝试直接作为路径处理
                    if os.path.exists(raw_result):
                        src_path = raw_result
                        import shutil
                        shutil.copy2(src_path, output_path)
                        print(f"✅ 图片已生成并保存至: {output_path}")
                        return output_path
            
            print(f"Warning: No image path found in output: {result.stdout}")
            return None
            
        except Exception as e:
            print(f"Error calling image gen service: {e}")
            return None
        finally:
            # 清理临时文件
            if os.path.exists(client_script_path):
                os.remove(client_script_path)

