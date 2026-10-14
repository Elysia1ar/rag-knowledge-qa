"""全局异常定义。"""


class RAGBaseError(Exception):
    """项目内异常基类。"""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class UnsupportedFileTypeError(RAGBaseError):
    """不支持的文件类型。"""


class DocumentLoadError(RAGBaseError):
    """文档加载失败。"""


class IndexingError(RAGBaseError):
    """向量入库失败。"""


class RetrievalError(RAGBaseError):
    """检索失败。"""