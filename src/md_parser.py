import re
import yaml

def parse_request_md(file_path):
    """
    解析 REQUEST.md 获取项目名称和需求描述
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取项目名称
    project_name_match = re.search(r'\*\*项目名称\*\*:\s*(.*?)\n', content)
    project_name = project_name_match.group(1).strip() if project_name_match else "untitled_project"
    
    # 提取需求描述 (假设在 "## 2. 详细需求描述" 之后)
    desc_match = re.search(r'## 2\. 详细需求描述.*?\n>(.*?)\n\n(.*?)$', content, re.DOTALL)
    # 简单的 fallback 逻辑
    if not desc_match:
        # 尝试匹配引用块之后的所有内容
        desc_match = re.search(r'## 2\. 详细需求描述.*?\n>.*?\n(.*)', content, re.DOTALL)
    
    description = desc_match.group(1).strip() if desc_match else ""
    
    return {
        "project_name": project_name,
        "description": description
    }

def parse_config_md(file_path):
    """
    解析 CONFIG.md 获取配置和 Prompts
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    config = {}
    
    # 1. 提取 YAML 配置块
    yaml_match = re.search(r'```yaml\n(.*?)\n```', content, re.DOTALL)
    if yaml_match:
        try:
            yaml_config = yaml.safe_load(yaml_match.group(1))
            config.update(yaml_config)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML config: {e}")
    
    # 2. 提取 Prompts
    # 使用简单的正则提取各个 Agent 的 prompt 代码块
    
    prompts = {}
    
    # Dynamic parsing of agents
    # Format: ### Agent X: Name (Key) ...
    # Be robust to variations like "### Agent: Name (Key)" or "### Agent 1: Name (Key)"
    agent_pattern = r'### Agent.*?: .*? \((.*?)\).*?\n```text\n(.*?)\n```'
    
    for match in re.finditer(agent_pattern, content, re.DOTALL):
        agent_key_raw = match.group(1)
        prompt_content = match.group(2).strip()
        
        # Support spaces in name like "Variant Generator" -> "variant_generator"
        agent_key = agent_key_raw.lower().replace(' ', '_')
        prompts[agent_key] = prompt_content
        
    config['prompts'] = prompts
    
    return config
