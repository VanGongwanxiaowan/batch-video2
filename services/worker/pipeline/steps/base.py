"""Pipeline 步骤基类

定义所有 Pipeline 步骤的抽象基类和通用功能。
使用策略模式，每个步骤都是独立的策略，可以自由组合。

架构设计：
- 支持传统的 Context 模式（向后兼容）
- 支持新的函数式模式（推荐）
- 步骤可以返回 StepResult 或修改 PipelineContext
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Union, TYPE_CHECKING

from core.exceptions import BatchShortException
from core.logging_config import setup_logging

if TYPE_CHECKING:
    from ..results import StepResult
    from ..context import PipelineContext

logger = setup_logging("worker.pipeline.steps")

# Type alias for result
StepOutput = Union["PipelineContext", "StepResult"]

T = TypeVar('T')


class StepException(BatchShortException):
    """步骤执行异常"""

    def __init__(
        self,
        step_name: str,
        message: str,
        original_error: Optional[Exception] = None,
        error_code: Optional[str] = None
    ):
        """初始化步骤异常

        Args:
            step_name: 步骤名称
            message: 错误消息
            original_error: 原始异常（如果有）
            error_code: 错误代码
        """
        self.step_name = step_name
        self.original_error = original_error
        full_message = f"[{step_name}] {message}"
        if original_error:
            full_message += f" (原因: {str(original_error)})"
        error_code = error_code or f"STEP_ERROR_{step_name.upper()}"
        super().__init__(full_message, error_code)


class BaseStep(ABC):
    """Pipeline 步骤抽象基类

    所有 Pipeline 步骤都必须继承此类。

    支持两种执行模式：
    1. 传统模式（向后兼容）：execute() 返回 PipelineContext
    2. 函数式模式（推荐）：_execute_functional() 返回 StepResult

    步骤执行流程:
    1. validate() - 验证输入数据
    2. execute() - 执行步骤逻辑（传统模式）
       或 _execute_functional() - 执行步骤逻辑（函数式模式）
    3. post_process() - 后处理（可选）

    传统模式示例:
        ```python
        class MyStep(BaseStep):
            name = "MyStep"

            def validate(self, context: PipelineContext) -> None:
                if not context.title:
                    raise StepException(self.name, "标题不能为空")

            def execute(self, context: PipelineContext) -> PipelineContext:
                context.my_result = do_something()
                return context
        ```

    函数式模式示例:
        ```python
        class MyStep(BaseStep):
            name = "MyStep"

            def _use_functional_style(self) -> bool:
                return True  # 启用函数式模式

            def validate(self, context: PipelineContext) -> None:
                if not context.title:
                    raise StepException(self.name, "标题不能为空")

            def _execute_functional(
                self,
                context: PipelineContext,
                **kwargs
            ) -> StepResult:
                result = do_something(context.title)
                return MyResult(
                    step_name=self.name,
                    data={"my_result": result}
                )
        ```
    """

    # 步骤名称（类属性，子类可以覆盖）
    name: str = "BaseStep"

    # 步骤描述（类属性，子类可以覆盖）
    description: str = "基础步骤"

    # 是否启用函数式模式（子类可以覆盖）
    _functional_mode: bool = False

    def validate(self, context: "PipelineContext") -> None:
        """验证输入数据

        在执行步骤前验证上下文数据是否满足要求。
        如果验证失败，应抛出 StepException。

        Args:
            context: Pipeline 上下文

        Raises:
            StepException: 验证失败时抛出
        """
        pass

    @abstractmethod
    def execute(self, context: "PipelineContext") -> "PipelineContext":
        """执行步骤逻辑（传统模式）

        这是步骤的核心方法，包含具体的业务逻辑。
        子类必须实现此方法（向后兼容）。

        注意：如果子类启用函数式模式（_use_functional_style 返回 True），
        则可以只实现 _execute_functional，此方法返回未修改的 context。

        Args:
            context: Pipeline 上下文

        Returns:
            PipelineContext: 更新后的上下文

        Raises:
            StepException: 步骤执行失败时抛出
        """
        pass

    def _use_functional_style(self) -> bool:
        """判断是否使用函数式模式

        子类可以覆盖此方法来启用函数式模式。

        Returns:
            bool: True 表示使用函数式模式，False 表示使用传统模式
        """
        return self._functional_mode

    def _execute_functional(
        self,
        context: "PipelineContext",
        *args,
        **kwargs
    ) -> "StepResult":
        """执行步骤逻辑（函数式模式）

        这是函数式模式的核心方法，子类可以选择实现。
        如果实现了此方法，应该同时覆盖 _use_functional_style 返回 True。

        Args:
            context: Pipeline 上下文（包含全局配置）
            *args: 位置参数（来自上一步的输出）
            **kwargs: 关键字参数（来自上一步的输出或配置）

        Returns:
            StepResult: 步骤执行结果

        Raises:
            StepException: 步骤执行失败时抛出
        """
        # 默认实现：调用传统模式并转换结果
        from ..results import StepResult
        result_context = self.execute(context)

        # 从 context 提取变化并转换为 StepResult
        return self._context_to_result(result_context)

    def _context_to_result(self, context: "PipelineContext") -> "StepResult":
        """将 PipelineContext 转换为 StepResult

        这是一个兼容性方法，用于将传统模式的结果转换为函数式模式。

        Args:
            context: PipelineContext

        Returns:
            StepResult: 通用的 StepResult
        """
        from ..results import StepResult

        # 子类可以覆盖此方法来提供更精确的转换
        return StepResult(
            step_name=self.name,
            data={},  # 子类应该填充具体数据
            metadata={"mode": "context_compat"}
        )

    def post_process(self, context: "PipelineContext", result: Optional[StepOutput] = None) -> None:
        """后处理（可选）

        在步骤执行成功后进行的后处理操作，
        如清理临时文件、记录日志等。

        Args:
            context: Pipeline 上下文
            result: 步骤执行结果（函数式模式下可用）
        """
        pass

    def run(self, context: "PipelineContext", **kwargs) -> "PipelineContext":
        """运行步骤的完整流程

        根据模式选择执行方式：
        - 传统模式：调用 execute()
        - 函数式模式：调用 _execute_functional() 并合并到 context

        Args:
            context: Pipeline 上下文
            **kwargs: 额外的关键字参数（函数式模式下传递给步骤）

        Returns:
            PipelineContext: 更新后的上下文

        Raises:
            StepException: 步骤执行失败时抛出
        """
        context.mark_step_started(self.name)

        try:
            # 1. 验证输入
            self.validate(context)

            # 2. 判断执行模式
            if self._use_functional_style() or kwargs:
                # 函数式模式
                logger.debug(
                    f"[{self.name}] 执行模式: 函数式 "
                    f"(job_id={context.job_id}, "
                    f"kwargs_keys={list(kwargs.keys())})"
                )
                result = self._execute_functional(context, **kwargs)

                # 将结果合并到 context（向后兼容）
                self._merge_result_to_context(context, result)

            else:
                # 传统模式
                logger.debug(
                    f"[{self.name}] 执行模式: 传统 "
                    f"(job_id={context.job_id})"
                )
                result_context = self.execute(context)
                # 同步 context（以防返回了不同的对象）
                if result_context is not context:
                    # 更新当前 context 的状态
                    pass

            # 3. 后处理
            self.post_process(context, result if kwargs else None)

            context.mark_step_completed(self.name)

            return context

        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise

        except StepException:
            # 步骤异常，直接抛出
            raise

        except Exception as exc:
            # 其他异常，包装为 StepException
            raise StepException(
                self.name,
                f"步骤执行失败: {str(exc)}",
                original_error=exc
            ) from exc

    def _merge_result_to_context(
        self,
        context: "PipelineContext",
        result: "StepResult"
    ) -> None:
        """将 StepResult 合并到 PipelineContext

        这是一个兼容性方法，用于在函数式模式下
        将结果同步到传统的 context。

        Args:
            context: PipelineContext
            result: StepResult
        """
        # 将 result.data 中的所有属性设置到 context
        for key, value in result.data.items():
            if not hasattr(context, key):
                logger.debug(
                    f"[{self.name}] 添加新属性到 context: {key}"
                )
            setattr(context, key, value)

    def __repr__(self) -> str:
        """字符串表示"""
        mode = "functional" if self._use_functional_style() else "context"
        return f"{self.__class__.__name__}(name={self.name}, mode={mode})"


class SkipStepException(BatchShortException):
    """跳过步骤异常

    抛出此异常表示该步骤应该被跳过，
    Pipeline 会继续执行后续步骤。
    """

    def __init__(self, step_name: str, reason: str = ""):
        """初始化跳过异常

        Args:
            step_name: 步骤名称
            reason: 跳过原因
        """
        self.step_name = step_name
        self.reason = reason
        message = f"[{step_name}] 步骤已跳过"
        if reason:
            message += f": {reason}"
        super().__init__(message, "STEP_SKIPPED")


class ConditionalStep(BaseStep):
    """条件步骤基类

    根据条件决定是否执行某个步骤。
    子类需要实现 should_execute() 方法来判断是否执行。

    传统模式示例:
        ```python
        class DigitalHumanStep(ConditionalStep):
            name = "DigitalHumanStep"

            def should_execute(self, context: PipelineContext) -> bool:
                return context.extra.get("enable_digital_human", False)

            def execute(self, context: PipelineContext) -> PipelineContext:
                # 数字人合成逻辑
                ...
        ```

    函数式模式示例:
        ```python
        class DigitalHumanStep(ConditionalStep):
            name = "DigitalHumanStep"

            def _use_functional_style(self) -> bool:
                return True

            def should_execute(self, context: PipelineContext) -> bool:
                return context.extra.get("enable_digital_human", False)

            def _execute_functional(
                self,
                context: PipelineContext,
                **kwargs
            ) -> DigitalHumanResult:
                # 数字人合成逻辑
                return DigitalHumanResult(...)
        ```
    """

    @abstractmethod
    def should_execute(self, context: "PipelineContext") -> bool:
        """判断是否应该执行此步骤

        Args:
            context: Pipeline 上下文

        Returns:
            bool: True 表示执行，False 表示跳过
        """
        pass

    def run(self, context: "PipelineContext", **kwargs) -> "PipelineContext":
        """运行条件步骤

        Args:
            context: Pipeline 上下文
            **kwargs: 额外的关键字参数

        Returns:
            PipelineContext: 更新后的上下文
        """
        if not self.should_execute(context):
            reason = f"条件不满足，跳过步骤: {self.name}"
            logger.info(f"[{self.name}] {reason} (job_id={context.job_id})")
            context.mark_step_completed(f"{self.name}(skipped)")
            return context

        return super().run(context, **kwargs)


class RetryableStep(BaseStep):
    """可重试步骤基类 (已废弃)

    .. deprecated::
        此类已废弃，不应再使用。

        废弃原因：
        1. 应用层重试无法处理 Worker 崩溃的情况
        2. 使用 time.sleep() 阻塞 Worker 进程
        3. 无法跨 Worker 重试
        4. 网络中断时无法有效恢复

        替代方案：
        - 使用 Celery 的任务级重试机制 (@shared_task 的 max_retries 参数)
        - Celery 重试在任务调度层面，更强大健壮：
          * Worker 崩溃时重试不会丢失
          * 支持跨 Worker 重试
          * 网络中断时可以等待后重试
          * 不会阻塞 Worker 进程

        示例：
            ```python
            @shared_task(
                bind=True,
                name='my.task',
                max_retries=3,
                default_retry_delay=60
            )
            def my_task(self, job_id):
                # 任务逻辑
                pass
            ```
    """

    # 最大重试次数 (已废弃)
    max_retries: int = 3

    # 重试延迟（秒） (已废弃)
    retry_delay: int = 5

    # 是否使用指数退避 (已废弃)
    use_backoff: bool = True

    def __init__(self, *args, **kwargs):
        """初始化时发出废弃警告"""
        super().__init__(*args, **kwargs)
        import warnings
        warnings.warn(
            f"{self.__class__.__name__} 使用了已废弃的 RetryableStep 基类。"
            "请改用 BaseStep，并依赖 Celery 的任务级重试机制。"
            "详见 RetryableStep 类文档中的替代方案。",
            DeprecationWarning,
            stacklevel=2
        )

    def run(self, context: "PipelineContext", **kwargs) -> "PipelineContext":
        """运行可重试步骤 (已废弃)

        此方法已不再实现应用层重试，直接调用父类方法。
        重试由 Celery 任务级处理。
        """
        # 不再执行应用层重试，直接调用父类方法
        # 重试由 Celery 任务级处理
        return super().run(context, **kwargs)


# 导出所有类
__all__ = [
    "BaseStep",
    "ConditionalStep",
    # "RetryableStep",  # 已废弃：使用 Celery 任务级重试代替应用层重试
    "SkipStepException",
    "StepException",
    # Type aliases
    "StepOutput",
]
