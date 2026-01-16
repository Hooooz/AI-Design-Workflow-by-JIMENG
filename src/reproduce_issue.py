from image_gen import ImageGenService
import os

def test():
    # 使用配置中的脚本路径
    script_path = "/Users/huangchuhao/Downloads/AI 工具/Cursor 代码库/Howie AI 工作室/彩友乐 AI 提效/AI设计工作流/test_workspace/image-gen-server/server.py"
    service = ImageGenService(server_script_path=script_path)
    
    output_dir = "test_output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print("Testing ImageGenService...")
    result = service.generate_image("A futuristic city", output_dir)
    print(f"Result: {result}")

if __name__ == "__main__":
    test()
