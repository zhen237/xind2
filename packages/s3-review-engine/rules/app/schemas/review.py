from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any

class ReviewCheckItem(BaseModel):
    rule_id: int = Field(..., gt=0, description="规则ID必须大于0")
    rule_code: str = Field(..., min_length=1, max_length=64, description="规则编号不能为空")
    rule_name: str = Field(..., min_length=1, max_length=128, description="规则名称不能为空")
    category: str = Field(..., min_length=1, max_length=64, description="分类不能为空")
    risk_level: Optional[str] = Field("warning", pattern="^(critical|error|warning|pending)$",
                                      description="风险等级：critical/error/warning 或 pending(待核查)")
    threshold: Optional[str] = None
    actual_value: Optional[str] = None
    standard_value: Optional[str] = None
    coordinates: Optional[List[float]] = None

    @field_validator('coordinates')
    def check_coordinates_length(cls, v):
        if v and len(v) > 3:
            raise ValueError('坐标最多包含3个值（经度、纬度、高度）')
        return v

class ReviewCheckRequest(BaseModel):
    task_id: int = Field(..., gt=0, description="任务ID必须大于0")
    design_task_id: str = Field(..., min_length=1, max_length=64, description="设计任务ID不能为空")
    task_name: Optional[str] = Field(None, max_length=256, description="任务名称")
    items: List[ReviewCheckItem] = Field(..., min_length=1, description="规则列表不能为空")
    
    # 兼容S1传来的结构化设计数据格式
    design_data: Optional[Dict[str, Any]] = None

    @field_validator('items')
    def check_items_not_empty(cls, v):
        if not v:
            raise ValueError('规则列表不能为空')
        return v

    @field_validator('items')
    def check_items_unique(cls, v):
        rule_codes = [item.rule_code for item in v]
        if len(rule_codes) != len(set(rule_codes)):
            raise ValueError('规则编号不能重复')
        return v

class ReviewResultItem(BaseModel):
    rule_id: int
    rule_code: str
    rule_name: str
    category: str
    actual_value: Optional[str] = None
    standard_value: Optional[str] = None
    coordinates: Optional[List[float]] = None
    risk_level: str = Field(..., pattern="^(critical|error|warning|pending)$",
                           description="风险等级：critical/error/warning 或 pending(待核查)")
    suggestion: Optional[str] = None
    # 新增字段
    standard_param: Optional[str] = Field(None, description="标准参数说明")
    device_type: Optional[str] = Field(None, description="设备类型")
    checked_value: Optional[float] = Field(None, description="校验值")
    passed: Optional[bool] = Field(None, description="是否通过")
    check_time: Optional[str] = Field(None, description="校验时间")

class ApiResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None

class ReviewCheckResponse(ApiResponse):
    data: List[ReviewResultItem] = []

class ValidationErrorResponse(ApiResponse):
    code: int = 400
    message: str = "validation error"
    detail: Optional[List[Dict[str, Any]]] = None

class ErrorResponse(ApiResponse):
    code: int = 500
    message: str = "server error"
