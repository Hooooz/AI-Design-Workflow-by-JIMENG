import os
import sys
import time
from typing import List, Dict, Any

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

import config

class LLMService:
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or config.OPENAI_API_KEY
        self.base_url = base_url or config.OPENAI_BASE_URL
        self.client = None
        
        # 只要有 API Key 就尝试初始化，不再检查前缀
        if OpenAI and self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except Exception as e:
                print(f"Warning: Failed to initialize OpenAI client: {e}")

    def chat_completion(self, messages: List[Dict[str, str]], model: str = config.DEFAULT_MODEL) -> str:
        """
        调用 LLM 生成回复。
        """
        if not self.client:
            # 如果没有初始化 client，直接抛出异常，不再静默 Mock
            raise ValueError("OpenAI client not initialized. Please check OPENAI_API_KEY.")

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling API: {e}")
            # 在生产环境中，我们希望看到真实的错误，而不是 Mock 数据
            raise e

    def _mock_response(self, messages: List[Dict[str, str]]) -> str:
        # Mock 逻辑保留用于测试，但不再自动触发
        last_user_msg = messages[-1]['content']
        time.sleep(1.5) # 模拟思考时间
        
        if "市场调研专家" in last_user_msg:
            return """
### 市场趋势分析
1. **极简主义与材质回归**：消费者偏向于实木、黄铜、水泥等天然材质，追求“去电子化”的触感。
2. **多功能融合**：不仅仅是相框，可能结合了无线充电、氛围灯或蓝牙音箱功能。
3. **动态展示**：高分辨率墨水屏（E-ink）相框正在兴起，既有纸质质感又能更换照片。

### 竞品痛点
1. **更换麻烦**：传统相框更换照片需要拆卸背板，非常繁琐。
2. **审美疲劳**：数码相框往往带有粗大的黑边和发光的屏幕，在温馨家居环境中显得突兀。
3. **摆放限制**：大多数相框只能横放或竖放，支架结构不稳定。
            """
        elif "视觉设计师" in last_user_msg:
             return """
### 视觉参考方向
1. **Reference A (Herman Miller style)**: 结合弯曲木工艺，流线型设计，温暖且现代。
2. **Reference B (Braun style)**: 德国博朗风格，理性、几何、黑白灰配色，强调功能美学。
3. **Reference C (Japandi style)**: 北欧与日式的结合，原木色+棉麻纹理，强调自然与宁静。

### 现有弊端分析
- 参考图A中的产品虽然美观，但**稳定性不足**，容易碰倒。
- 参考图B中的产品**缺乏温度**，像工业仪器。
- 普遍问题：**玻璃反光**严重，影响观感。
             """
        elif "产品设计总监" in last_user_msg:
            return """
### 方案一：磁吸悬浮实木相框
*   **核心理念**：利用磁悬浮技术让照片模块悬浮在木质框架中心，解决更换麻烦和摆放不稳的问题。
*   **材质**：胡桃木外框 + 亚克力照片封存块 + 磁吸底座。
*   **Prompt**: `product design, floating wooden photo frame, walnut wood texture, magnetic levitation, minimalism, warm lighting, high detail, 8k resolution, cinematic lighting --ar 3:4`

### 方案二：E-ink 纸感动态画廊
*   **核心理念**：使用彩色电子墨水屏，完全模拟印刷品且不发光，配合超薄金属边框。
*   **材质**：拉丝铝合金边框 + 磨砂防眩光屏幕。
*   **Prompt**: `product design, e-ink digital photo frame, matte screen, brushed aluminum thin bezel, museum gallery style, realistic texture, soft daylight --ar 16:9`

### 方案三：模块化拼贴墙
*   **核心理念**：六边形单元，可无限拼接，内置连接触点，单电源供电。
*   **材质**：再生塑料 + 织物表面。
*   **Prompt**: `product design, hexagonal modular photo frame system, fabric texture surface, wall mounted, creative collage, colorful geometric pattern, modern home decor --ar 1:1`
            """
        else:
            return "这是一个模拟回复。请配置有效的 API Key 以获得真实结果。"

