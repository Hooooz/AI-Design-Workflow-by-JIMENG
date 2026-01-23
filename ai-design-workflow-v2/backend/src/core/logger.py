"""
日志模块 - AI 设计工作流 v2

提供结构化日志，支持：
- 不同环境（日志级别）
- 文件和控制台输出
- 请求追踪
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """自定义JSON日志格式"""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.utcnow().isoformat()
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["message"] = record.getMessage()

        # 添加源代码位置
        if hasattr(record, "filename"):
            log_record["source"] = f"{record.filename}:{record.lineno}"


def setup_logger(name: str = "ai-design-workflow", level: int = logging.INFO):
    """设置logger"""
    # 确保logs目录存在
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 清除现有处理器
    logger.handlers.clear()

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # 文件处理器 (JSON格式)
    log_file = logs_dir / f"api_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)

    # 格式化
    if logger.level == logging.DEBUG:
        # 开发环境使用人类可读的格式
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    else:
        # 生产环境使用JSON格式
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(message)s", rename_fields={"message": "message"}
        )

    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# 创建全局logger
logger = setup_logger()
