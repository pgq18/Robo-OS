import logging
import os
import multiprocessing
from logging.handlers import RotatingFileHandler
from typing import Optional
from utils.utils import Config

class MultiProcessingRotatingFileHandler(RotatingFileHandler):
    """
    支持多进程的RotatingFileHandler
    """
    def emit(self, record):
        """
        重写emit方法以支持多进程写入
        """
        # 在写入前先获取文件锁
        try:
            # 确保文件存在
            if not os.path.exists(self.baseFilename):
                fd = os.open(self.baseFilename, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
                os.close(fd)
            
            # 打开文件并获取独占锁
            with open(self.baseFilename, 'a+', encoding=self.encoding) as f:
                # 在写入前刷新缓冲区
                f.flush()
                # 写入日志记录
                msg = self.format(record)
                f.write(msg + self.terminator)
                f.flush()
        except Exception:
            self.handleError(record)


class LoggerManager:
    """
    统一日志管理器，确保所有模块的日志都写入同一个文件，支持多进程环境
    """
    _instance = None
    _initialized = False
    _lock = multiprocessing.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LoggerManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, log_file: str = "./app.log", max_bytes: int = 10*1024*1024, backup_count: int = 5, log_level: int = logging.INFO):
        """
        初始化日志管理器
        
        Args:
            log_file: 日志文件路径
            max_bytes: 单个日志文件最大字节数
            backup_count: 保留的备份文件数量
            log_level: 日志级别，默认为INFO，不输出DEBUG级别的日志
        """
        if LoggerManager._initialized:
            return
            
        self.log_file = log_file
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.log_level = log_level
        self._setup_logger()
        LoggerManager._initialized = True

    def _setup_logger(self):
        """设置日志记录器"""
        # 创建日志目录（如果不存在）
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 创建格式化器，移除了 %(name)s 字段
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )

        # 创建支持多进程的文件处理器（带轮转）
        try:
            # 尝试使用多进程安全的处理器
            file_handler = MultiProcessingRotatingFileHandler(
                self.log_file, 
                maxBytes=self.max_bytes, 
                backupCount=self.backup_count,
                encoding='utf-8'
            )
        except:
            # 如果多进程处理器不可用，则回退到标准RotatingFileHandler
            file_handler = RotatingFileHandler(
                self.log_file, 
                maxBytes=self.max_bytes, 
                backupCount=self.backup_count,
                encoding='utf-8'
            )
            
        file_handler.setFormatter(formatter)
        file_handler.setLevel(self.log_level)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(self.log_level)

        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        # 避免重复添加处理器
        root_logger.propagate = False

        # 控制第三方库的日志级别
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """
        获取日志记录器实例
        
        Args:
            name: 日志记录器名称，通常为模块名(__name__)
            
        Returns:
            logging.Logger: 配置好的日志记录器
        """
        return logging.getLogger(name)


# 全局日志管理器实例，默认日志级别为INFO，不输出DEBUG级别的日志
logger_manager = LoggerManager()

# 便捷函数，用于快速获取日志记录器
def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    获取日志记录器的便捷函数
    
    Args:
        name: 日志记录器名称
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    return logger_manager.get_logger(name)