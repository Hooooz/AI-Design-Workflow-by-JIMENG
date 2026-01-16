# 设计领域外部知识库 (Knowledge Base)

此文档存储了设计行业的通用知识、趋势源和 Prompt 技巧。系统会在运行时自动读取此文件，并将其作为“专家知识”注入给 AI Agent。

## 1. 权威资讯来源 (Information Sources)
当进行市场和视觉分析时，请模拟参考以下权威平台的数据和风格：
*   **趋势预测**: WGSN, Pantone Color Institute, McKinsey Design Reports.
*   **工业设计**: Core77, Dezeen, Yanko Design, Red Dot Award Winners.
*   **UI/UX**: Nielsen Norman Group, Mobbin, Awwwards.
*   **视觉灵感**: Pinterest (Moodboards), Behance (Case Studies), ArtStation (Concept Art).

## 2. 2024-2025 设计趋势关键词 (Trend Keywords)
*   **CMF (Color, Material, Finish)**:
    *   *Neo-Ecology*: 再生塑料、菌丝体材料、生物基皮革。
    *   *Digital Lavender*: 疗愈感的数字薰衣草紫。
    *   *Brushed Metal*: 粗犷的拉丝金属与高光泽表面的对比。
*   **UI 风格**:
    *   *Bento Grids*: 便当盒式网格布局。
    *   *Spatial UI*: 空间感、玻璃拟态 (Glassmorphism) 的进化版。

## 3. 高质量 AI 绘图 Prompt 技巧 (Prompt Engineering)
生成 Midjourney/Stable Diffusion 提示词时，请遵循以下结构：

**[主体描述] + [环境/背景] + [构图/视角] + [光影/氛围] + [风格/参考] + [渲染参数]**

*   **材质词 (Materials)**: `translucent polycarbonate` (半透明聚碳酸酯), `anodized aluminum` (阳极氧化铝), `knitted fabric texture` (针织纹理).
*   **光影词 (Lighting)**: `volumetric lighting` (体积光), `rembrandt lighting` (伦勃朗光), `studio softbox` (摄影棚柔光), `bioluminescent` (生物发光).
*   **渲染词 (Render)**: `Unreal Engine 5`, `Octane Render`, `8k resolution`, `hyper-realistic`, `ray tracing`.
*   **相机词 (Camera)**: `macro lens` (微距), `telephoto` (长焦), `depth of field` (景深), `bokeh` (散景).
*   **否定词 (Negative - 仅 SD)**: `blurry, low quality, distorted, watermark, text`.

## 4. 行业特定规则 (Industry Specifics)
*   **消费电子**: 强调倒角 (Chamfer)、接缝 (Part line) 的处理，以及人机工程学。
*   **家居用品**: 强调温暖感 (Warmth)、触感 (Tactility) 和融入环境的能力。
*   **SaaS 界面**: 强调信息密度 (Information Density)、可读性 (Readability) 和操作效率。
