from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 8100
    host: str = "127.0.0.1"        # 默认仅本地回环（联调暴露局域网时设 S4_HOST=0.0.0.0）
    java_backend_url: str = "http://127.0.0.1:8090"   # 用 IP 避免 localhost→IPv6 解析问题

    # ── 数据源切换（联调关键配置）────────────────────────
    # data_source: mock | real
    #   mock: 从 data/mock/*.json 读取模拟设计清单（默认，本地演示）
    #   real: 请求 S1 真实接口 GET {s1_base_url}/api/s1/design/tasks/{designTaskId}
    data_source: str = "mock"
    s1_base_url: str = ""          # real 模式下必填（S1 服务地址）
    s3_base_url: str = ""          # real 模式下选填（S3 服务地址；缺省复用 java_backend_url）
    s1_timeout: int = 15           # 请求 S1/S3 的超时秒数

    class Config:
        env_prefix = "S4_"
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
