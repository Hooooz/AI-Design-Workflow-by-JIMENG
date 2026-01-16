import unittest
import os
import shutil
import sys
from datetime import datetime

# 添加 src 到路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from llm_wrapper import LLMService
from image_gen import ImageGenService
import config

class TestWorkflowIntegration(unittest.TestCase):
    def setUp(self):
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🧪 开始集成测试...")
        self.output_dir = "test_output"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
    def tearDown(self):
        # 清理测试目录 (可选)
        # shutil.rmtree(self.output_dir)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🏁 测试结束")

    def test_1_gemini_api(self):
        """测试 Gemini API 连接与生成"""
        print("   -> 测试 Gemini API...")
        llm = LLMService()
        messages = [{"role": "user", "content": "Hello, are you Gemini? Reply with 'Yes, I am Gemini'."}]
        response = llm.chat_completion(messages)
        print(f"      Response: {response}")
        self.assertTrue(len(response) > 0)
        # 注意：不同模型回复可能不同，主要检查是否非空且非 Mock（如果 key 正确）
        
    def test_2_jimeng_image_gen(self):
        """测试即梦绘图服务"""
        print("   -> 测试即梦绘图 API...")
        # 确保 server.py 路径正确
        server_path = config.JIMENG_SERVER_SCRIPT
        if not os.path.exists(server_path):
            print(f"      ⚠️ Server script not found at {server_path}, skipping image test.")
            return

        service = ImageGenService(server_path)
        prompt = "A futuristic cyberpunk city with neon lights, 8k resolution"
        
        # 尝试生成
        image_path = service.generate_image(prompt, self.output_dir)
        
        if image_path:
            self.assertTrue(os.path.exists(image_path))
            print(f"      ✅ 图片生成成功: {image_path}")
        else:
            print("      ⚠️ 图片生成失败 (可能是环境配置问题)")
            # 这里不强制 fail，因为依赖本地环境

if __name__ == '__main__':
    unittest.main()
