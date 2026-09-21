from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union
from .schemas import DocumentProcessingResult

class DocumentProcessor(ABC):
    """
    Interface dasar untuk semua document processors.
    """
    @abstractmethod
    def process(self, file_path: Union[Path, str]) -> DocumentProcessingResult:
        pass