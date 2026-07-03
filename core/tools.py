"""
EduAgent 工具系统 —— 轻量级工具注册与调用框架
"""

import inspect
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ToolDef:
    """工具定义"""
    name: str
    description: str
    func: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """工具注册中心 —— 管理所有可用工具"""

    def __init__(self):
        self._tools: Dict[str, ToolDef] = {}

    def register(
        self,
        name: Optional[str] = None,
        description: str = "",
    ) -> Callable:
        """装饰器：注册一个工具函数"""

        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            # 从函数签名提取参数信息
            sig = inspect.signature(func)
            params = {}
            for param_name, param in sig.parameters.items():
                params[param_name] = {
                    "type": self._py_type_to_json(param.annotation),
                    "required": param.default is inspect.Parameter.empty,
                }

            self._tools[tool_name] = ToolDef(
                name=tool_name,
                description=description or func.__doc__ or "",
                func=func,
                parameters=params,
            )
            return func

        return decorator

    def get_schema(self) -> List[Dict[str, Any]]:
        """返回所有工具的 OpenAI function-calling schema"""
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": tool.parameters,
                        "required": [
                            k for k, v in tool.parameters.items()
                            if v.get("required", False)
                        ],
                    },
                },
            })
        return schemas

    def call(self, name: str, **kwargs) -> Any:
        """调用指定工具"""
        if name not in self._tools:
            raise ValueError(f"工具 '{name}' 未注册，可用工具: {list(self._tools.keys())}")
        return self._tools[name].func(**kwargs)

    @staticmethod
    def _py_type_to_json(annotation) -> str:
        """Python 类型 → JSON Schema 类型"""
        mapping = {
            str: "string", int: "integer", float: "number",
            bool: "boolean", list: "array", dict: "object",
        }
        if annotation in mapping:
            return mapping[annotation]
        return "string"


# 便捷别名
tool = ToolRegistry.register
