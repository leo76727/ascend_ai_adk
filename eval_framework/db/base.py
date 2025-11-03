# db/base.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..models import EvalTestCase

class EvalDB(ABC):
    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def disconnect(self):
        pass

    @abstractmethod
    async def save_test_case(self, test_case: EvalTestCase):
        pass

    @abstractmethod
    async def load_approved_test_cases(self, test_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        pass