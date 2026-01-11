"""统一数据模型定义

包含所有数据库模型的定义，包括用户、任务、账户等核心实体。
"""
import uuid
from datetime import datetime

import pytz
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from .session import Base


# 定义一个函数来获取北京时间
def get_beijing_time() -> datetime:
    """获取北京时间
    
    Returns:
        datetime: 当前北京时间
    """
    tz = pytz.timezone("Asia/Shanghai")
    return datetime.now(tz)


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    user_id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=get_beijing_time)
    last_login_at = Column(
        DateTime, default=get_beijing_time, onupdate=get_beijing_time, nullable=True
    )


class Language(Base):
    """语言模型
    
    表示支持的语言类型。
    
    注意：
        - name有唯一索引，用于语言查询
    """
    __tablename__ = "languages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)  # 语言名称，唯一索引
    platform = Column(String(255), nullable=True)  # 平台名称
    language_name = Column(String(255), nullable=True)  # 语言显示名称
    created_at = Column(DateTime, default=get_beijing_time)  # 创建时间
    updated_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time)
    user_id = Column(CHAR(36), ForeignKey("users.user_id"), nullable=True)
    user = relationship("User")


class Voice(Base):
    """音色模型"""
    __tablename__ = "voices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    path = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=get_beijing_time)
    updated_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time)
    user_id = Column(CHAR(36), ForeignKey("users.user_id"), nullable=True)
    user = relationship("User")


class Topic(Base):
    """话题模型"""
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    prompt_gen_image = Column(Text, nullable=True)
    prompt_cover_image = Column(Text, nullable=True)
    prompt_image_prefix = Column(Text, nullable=True)
    prompt_l4 = Column(Text, nullable=True)
    loraname = Column(String(255), unique=True, index=True, nullable=True, default="")
    loraweight = Column(Integer, default=100, nullable=True)
    extra = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime, default=get_beijing_time)
    updated_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time)
    user_id = Column(CHAR(36), ForeignKey("users.user_id"), nullable=True)
    user = relationship("User")


class Account(Base):
    """账号模型"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    logo = Column(String(255), default="")
    platform = Column(String(255), default="youtube")
    area = Column(String(255), default="")
    extra = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime, default=get_beijing_time)
    updated_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time)
    user_id = Column(CHAR(36), ForeignKey("users.user_id"), nullable=True)
    user = relationship("User")


class Job(Base):
    """任务模型 - 任务配置

    表示一个视频生成任务的配置和定义，不包含执行状态。
    这是任务的"模板"，可以被多次执行。

    字段分类：
    - 配置字段: title, content, language_id, voice_id, speech_speed 等
    - 不包含: status, status_detail, job_result_key 等执行状态字段
      这些字段已移至 JobExecution 表

    注意：
        - 使用复合索引优化常用查询
        - deleted_at用于软删除，查询时需要过滤
        - 一个 Job 可以对应多个 JobExecution
    """
    __tablename__ = "jobs"

    # 定义复合索引，优化常用查询
    __table_args__ = (
        # 优化待处理任务查询：deleted_at + runorder + id
        Index('idx_deleted_runorder_id', 'deleted_at', 'runorder', 'id'),
        # 优化用户任务列表查询：user_id + deleted_at + id
        Index('idx_user_deleted_id', 'user_id', 'deleted_at', 'id'),
        # 优化账户任务查询：account_id + deleted_at + id
        Index('idx_account_deleted_id', 'account_id', 'deleted_at', 'id'),
        # 优化语言任务查询：language_id + deleted_at + id
        Index('idx_language_deleted_id', 'language_id', 'deleted_at', 'id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    runorder = Column(Integer, default=0, nullable=False, index=True)  # 添加索引用于排序
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    language_id = Column(Integer, ForeignKey("languages.id"), nullable=True, index=True)  # 添加索引
    language = relationship("Language")
    voice_id = Column(Integer, ForeignKey("voices.id"), nullable=True)
    voice = relationship("Voice")
    description = Column(Text, nullable=False)
    publish_title = Column(Text, nullable=False)  # 发布标题
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    topic = relationship("Topic")
    speech_speed = Column(Float, default=0.9, nullable=False)
    created_at = Column(DateTime, default=get_beijing_time, index=True)  # 添加索引用于排序
    updated_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time)
    user_id = Column(CHAR(36), ForeignKey("users.user_id"), nullable=True, index=True)  # 添加索引
    user = relationship("User")
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)  # 添加索引
    account = relationship("Account")
    is_horizontal = Column(Boolean, default=True, nullable=False)
    extra = Column(JSON, nullable=False, default={})
    deleted_at = Column(DateTime, nullable=True, index=True)  # 添加索引用于软删除过滤

    # 关系：一个 Job 可以有多个执行记录
    executions = relationship("JobExecution", back_populates="job", cascade="all, delete-orphan")

    # 为了向后兼容，提供最新执行状态的快捷访问
    @property
    def latest_execution(self):
        """获取最新的执行记录"""
        if hasattr(self, '_latest_execution') and self._latest_execution:
            return self._latest_execution

        # 这个属性需要在查询时预加载
        # 使用: session.query(Job).options(joinedload(Job.latest_execution))
        return None

    @property
    def status(self):
        """向后兼容：获取最新执行状态"""
        execution = self.latest_execution
        return execution.status if execution else "待处理"

    @property
    def status_detail(self):
        """向后兼容：获取最新执行详情"""
        execution = self.latest_execution
        return execution.status_detail if execution else ""

    @property
    def job_result_key(self):
        """向后兼容：获取最新执行结果"""
        execution = self.latest_execution
        return execution.result_key if execution else None


class JobExecution(Base):
    """任务执行记录表

    存储每一次任务执行的记录，包括状态、结果、执行时间等。
    一个 Job 可以有多条 JobExecution 记录（支持重试、重新运行）。

    设计优势：
    1. 历史追溯：可以清楚看到 Job 被执行了多少次，每次成功还是失败
    2. 表结构清晰：Job 表更稳定，JobExecution 表频繁写入
    3. 支持重新运行：用户可以对已完成或失败的 Job 发起重新运行
    4. 性能优化：对 Job 表的查询不会被 JobExecution 的频繁写入影响

    字段说明：
    - job_id: 关联的 Job ID
    - status: 执行状态 (PENDING, RUNNING, SUCCESS, FAILED)
    - status_detail: 状态详情
    - result_key: 结果存储键
    - worker_hostname: 执行该任务的 Worker 主机名
    - started_at: 开始执行时间
    - finished_at: 完成时间
    - retry_count: 重试次数
    - error_message: 错误信息（如果失败）
    - execution_metadata: 执行元数据（JSON格式）
    """
    __tablename__ = "job_executions"

    # 定义复合索引，优化常用查询
    __table_args__ = (
        # 优化查询 Job 的执行记录：job_id + status
        Index('idx_job_status', 'job_id', 'status'),
        # 优化查询待处理的执行记录：status + created_at
        Index('idx_status_created', 'status', 'created_at'),
        # 优化查询 Worker 的任务：worker_hostname + status
        Index('idx_worker_status', 'worker_hostname', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    status = Column(
        Enum("PENDING", "RUNNING", "SUCCESS", "FAILED", name="job_execution_status"),
        default="PENDING",
        index=True,
        nullable=False,
    )
    status_detail = Column(String(500), default="")
    result_key = Column(Text, nullable=True)
    worker_hostname = Column(String(255), nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    execution_metadata = Column(JSON, nullable=False, default={})
    created_at = Column(DateTime, default=get_beijing_time, index=True)
    updated_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time)

    # 关系：属于一个 Job
    job = relationship("Job", back_populates="executions")

    @property
    def duration(self):
        """获取执行时长（秒）"""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    @property
    def is_successful(self):
        """是否执行成功"""
        return self.status == "SUCCESS"

    @property
    def is_failed(self):
        """是否执行失败"""
        return self.status == "FAILED"

    @property
    def is_running(self):
        """是否正在执行"""
        return self.status == "RUNNING"

    @property
    def is_pending(self):
        """是否待处理"""
        return self.status == "PENDING"


class JobSplit(Base):
    """任务分片模型
    
    表示任务的一个分割片段，包含该片段的文本、图像、视频等信息。
    
    注意：
        - job_id + index 复合索引优化按任务查询分割项
    """
    __tablename__ = "job_splits"
    
    # 定义复合索引，优化按任务查询分割项
    __table_args__ = (
        Index('idx_job_index', 'job_id', 'index'),  # 优化按任务和索引查询
    )

    id = Column(Integer, primary_key=True, index=True)
    start = Column(Integer, nullable=False)  # 开始时间（毫秒）
    end = Column(Integer, nullable=False)  # 结束时间（毫秒）
    text = Column(String(255), nullable=False)  # 文本内容
    prompt = Column(String(255), nullable=True)  # 图像生成提示词
    images = Column(Text, nullable=True)  # 存储为JSON字符串
    video = Column(String(255), nullable=True)  # 视频路径
    selected = Column(String(255), nullable=True)  # 选中的图像
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)  # 添加索引
    index = Column(Integer, nullable=False)  # 分割项索引，用于排序
    created_at = Column(DateTime, default=get_beijing_time)
    updated_at = Column(DateTime, default=get_beijing_time, onupdate=get_beijing_time)
    job = relationship("Job")

