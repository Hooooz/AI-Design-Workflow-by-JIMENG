import re
import json
import logging
from typing import List, Dict, Any, Optional
from services import db_service
import config

logger = logging.getLogger("design-workflow")


class ProjectService:
    @staticmethod
    def fix_image_urls(images: List[str]) -> List[str]:
        """
        将路径转换为 Supabase 公网 URL。
        业务逻辑：处理旧 IP、处理相对路径、识别 ID。
        """
        if not images:
            return []

        supabase_url = config.SUPABASE_URL
        if not supabase_url:
            return images

        bucket = "project-images"
        fixed_images = []

        for img in images:
            if not img:
                continue

            # 处理旧的 IP 访问地址
            if "47.89.249.90" in img and "/projects/" in img:
                parts = img.split("/projects/")[-1].split("/")
                if len(parts) >= 2:
                    project_id = db_service.get_project_id(parts[0])
                    filename = parts[1]
                    fixed_images.append(
                        f"{supabase_url}/storage/v1/object/public/{bucket}/{project_id}/{filename}"
                    )
                    continue

            # 如果已经是正确的 Supabase 公网 URL，直接保留
            if img.startswith("http") and "supabase.co" in img:
                fixed_images.append(img)
                continue

            # 处理本地/相对路径格式: /projects/{project_id}/{filename}
            if img.startswith("/projects/"):
                parts = img.replace("/projects/", "").split("/")
                if len(parts) >= 2:
                    segment = parts[0]
                    # 智能识别：如果是12位16进制字符串，认为是ID；否则认为是项目名
                    if re.match(r"^[0-9a-f]{12}$", segment):
                        project_id = segment
                    else:
                        project_id = db_service.get_project_id(segment)

                    filename = parts[1]
                    fixed_images.append(
                        f"{supabase_url}/storage/v1/object/public/{bucket}/{project_id}/{filename}"
                    )
                else:
                    fixed_images.append(img)
            else:
                fixed_images.append(img)

        return fixed_images

    @staticmethod
    def fix_markdown_images(text: str, project_name: str) -> str:
        """
        修复 Markdown 文本中的图片链接（针对 jimeng_ 开头的文件）
        """
        if not text:
            return ""

        # 匹配 Markdown 图片语法: ![alt](filename) 或 [alt](filename)
        # 捕获组 1: alt text, 捕获组 2: filename (仅匹配 jimeng_ 开头且不含 / 的文件名)
        pattern = r"(!?\[.*?\])\((jimeng_[^)]+\.(?:jpg|png|jpeg))\)"

        def replace_url(match):
            prefix = match.group(1)
            filename = match.group(2)
            project_id = db_service.get_project_id(project_name)
            temp_path = f"/projects/{project_id}/{filename}"
            fixed_urls = ProjectService.fix_image_urls([temp_path])
            final_url = fixed_urls[0] if fixed_urls else filename
            return f"{prefix}({final_url})"

        return re.sub(pattern, replace_url, text)

    @classmethod
    def process_project_data(cls, project: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理项目数据，包括 URL 修复和结构调整，供前端使用。
        """
        project_name = project.get("project_name")
        if not project_name:
            return project

        content = project.get("content", {})
        if isinstance(content, dict):
            market_analysis = content.get("market_analysis", "")
            visual_research = content.get("visual_research", "")
            design_proposals = content.get("design_proposals", "")
            full_report = content.get("full_report", "")
        else:
            market_analysis = project.get("market_analysis", "")
            visual_research = project.get("visual_research", "")
            design_proposals = project.get("design_proposals", "")
            full_report = project.get("full_report", "")

        if "images" in project:
            project["images"] = cls.fix_image_urls(project["images"])

        if design_proposals and isinstance(design_proposals, str):
            try:
                dp_data = json.loads(design_proposals)

                if "prompts" in dp_data and isinstance(dp_data["prompts"], list):
                    for prompt in dp_data["prompts"]:
                        if "image_path" in prompt and prompt["image_path"]:
                            raw_path = prompt["image_path"]
                            if not raw_path.startswith("http") and "/" not in raw_path:
                                project_id = db_service.get_project_id(project_name)
                                raw_path = f"/projects/{project_id}/{raw_path}"

                            fixed_urls = cls.fix_image_urls([raw_path])
                            prompt["image_path"] = (
                                fixed_urls[0] if fixed_urls else prompt["image_path"]
                            )

                if "content" in dp_data and isinstance(dp_data["content"], str):
                    dp_data["content"] = cls.fix_markdown_images(
                        dp_data["content"], project_name
                    )

                design_proposals = json.dumps(dp_data, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                design_proposals = cls.fix_markdown_images(
                    design_proposals, project_name
                )

        market_analysis = cls.fix_markdown_images(market_analysis, project_name)
        visual_research = cls.fix_markdown_images(visual_research, project_name)
        full_report = cls.fix_markdown_images(full_report, project_name)

        # 4. 构造前端预期的结构
        metadata_fields = [
            "project_name",
            "brief",
            "model_name",
            "creation_time",
            "status",
            "current_step",
            "tags",
        ]
        metadata = {k: project.get(k) for k in metadata_fields if k in project}

        return {
            "metadata": metadata,
            "market_analysis": market_analysis,
            "visual_research": visual_research,
            "design_proposals": design_proposals,
            "full_report": full_report,
            "images": project.get("images", []),
        }
