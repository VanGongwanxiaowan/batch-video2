"""Pipeline 执行器

负责 Pipeline 的执行逻辑，包括传统模式和函数式模式。

这是从 VideoPipeline 类中提取出来的专门模块，用于处理步骤执行。

代码重构说明：
- 使用 core.config.status.ExecutionStatus 枚举替换硬编码状态字符串
"""
from typing import Any, Dict, List, TYPE_CHECKING

from core.config.status import ExecutionStatus
from core.exceptions import BatchShortException
from core.logging_config import setup_logging

from .context import PipelineContext

if TYPE_CHECKING:
    from .steps.base import BaseStep
    from .results import StepResult
    from .input_resolver import StepInputResolver
    from .result_manager import StepResultManager

logger = setup_logging("worker.pipeline.executor")


class PipelineException(BatchShortException):
    """Pipeline 执行异常"""

    def __init__(self, message: str, job_id: int = None):
        """初始化 Pipeline 异常

        Args:
            message: 错误消息
            job_id: 任务ID
        """
        self.job_id = job_id
        if job_id:
            message = f"[Job {job_id}] {message}"
        super().__init__(message, "PIPELINE_ERROR")


class PipelineExecutor:
    """Pipeline 执行器

    负责 Pipeline 的执行逻辑，支持两种模式：
    1. 传统模式：步骤通过修改 context 传递数据（向后兼容）
    2. 函数式模式：步骤返回 StepResult，结果在步骤间显式传递

    Attributes:
        context: Pipeline 上下文
        input_resolver: 输入解析器（函数式模式）
        result_manager: 结果管理器（函数式模式）
    """

    def __init__(
        self,
        context: PipelineContext,
        input_resolver: "StepInputResolver" = None,
        result_manager: "StepResultManager" = None,
    ):
        """初始化执行器

        Args:
            context: Pipeline 上下文
            input_resolver: 输入解析器（函数式模式使用）
            result_manager: 结果管理器（函数式模式使用）
        """
        self.context = context
        self.input_resolver = input_resolver
        self.result_manager = result_manager

    def execute_traditional(self, steps: List["BaseStep"]) -> PipelineContext:
        """执行 Pipeline（传统模式）

        按顺序执行所有步骤，如果某个步骤失败则停止执行。
        步骤通过修改 context 传递数据（向后兼容）。

        Args:
            steps: 要执行的步骤列表

        Returns:
            PipelineContext: 最终的上下文

        Raises:
            PipelineException: Pipeline 执行失败时抛出

        代码重构说明：
            使用 ExecutionStatus 枚举替换硬编码状态字符串
        """
        job_id = self.context.job_id
        total_steps = len(steps)

        if total_steps == 0:
            logger.warning(f"[PipelineExecutor] 没有步骤需要执行 (job_id={job_id})")
            return self.context

        logger.info(
            f"[PipelineExecutor] 开始执行 Pipeline (传统模式) "
            f"(job_id={job_id}, 步骤数={total_steps})"
        )

        # 更新任务状态为处理中
        self.context.update_job_status(
            ExecutionStatus.PROCESSING,
            f"Pipeline 开始执行，共 {total_steps} 个步骤"
        )

        try:
            # 依次执行每个步骤
            for index, step in enumerate(steps, start=1):
                logger.info(
                    f"[PipelineExecutor] 执行步骤 {index}/{total_steps}: {step.name} "
                    f"(job_id={job_id})"
                )

                # 更新状态详情
                step_progress = f"正在执行: {step.name} ({index}/{total_steps})"
                self.context.update_job_status(ExecutionStatus.PROCESSING, step_progress)

                # 执行步骤（传统模式，不传递 kwargs）
                self.context = step.run(self.context)

                # 检查是否在步骤中标记了失败
                if self.context.failed_step:
                    raise PipelineException(
                        f"Pipeline 执行失败: 步骤 '{self.context.failed_step}' 失败"
                    )

            # 所有步骤成功完成
            logger.info(
                f"[PipelineExecutor] Pipeline 执行成功 "
                f"(job_id={job_id}, 耗时={self.context.get_duration():.2f}秒)"
            )

            return self.context

        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise

        except Exception as exc:
            # Pipeline 执行失败
            logger.exception(
                f"[PipelineExecutor] Pipeline 执行失败 "
                f"(job_id={job_id}, 失败步骤={self.context.failed_step})"
            )

            # 更新任务状态
            self.context.update_job_status(
                ExecutionStatus.FAILED,
                f"Pipeline 执行失败: {str(exc)}"
            )

            # 重新抛出异常
            raise PipelineException(
                f"Pipeline 执行失败 (job_id={job_id}): {str(exc)}"
            ) from exc

    def execute_functional(
        self,
        steps: List["BaseStep"]
    ) -> Dict[str, "StepResult"]:
        """执行 Pipeline（函数式模式）

        按顺序执行所有步骤，每个步骤返回 StepResult。
        结果在步骤间显式传递，提供更好的类型安全和可测试性。

        Args:
            steps: 要执行的步骤列表

        Returns:
            Dict[str, StepResult]: 所有步骤的结果字典

        Raises:
            PipelineException: Pipeline 执行失败时抛出

        代码重构说明：
            使用 ExecutionStatus 枚举替换硬编码状态字符串
        """
        job_id = self.context.job_id
        total_steps = len(steps)

        if total_steps == 0:
            logger.warning(f"[PipelineExecutor] 没有步骤需要执行 (job_id={job_id})")
            return {}

        logger.info(
            f"[PipelineExecutor] 开始执行 Pipeline (函数式模式) "
            f"(job_id={job_id}, 步骤数={total_steps})"
        )

        # 更新任务状态为处理中
        self.context.update_job_status(
            ExecutionStatus.PROCESSING,
            f"Pipeline 开始执行，共 {total_steps} 个步骤"
        )

        try:
            # 依次执行每个步骤
            for index, step in enumerate(steps, start=1):
                logger.info(
                    f"[PipelineExecutor] 执行步骤 {index}/{total_steps}: {step.name} "
                    f"(job_id={job_id})"
                )

                # 更新状态详情
                step_progress = f"正在执行: {step.name} ({index}/{total_steps})"
                self.context.update_job_status(ExecutionStatus.PROCESSING, step_progress)

                # 准备输入参数（从之前步骤的结果中提取）
                step_kwargs = self.input_resolver.resolve_inputs(step, self.context)

                # 执行步骤（函数式模式，传递 kwargs）
                result = step._execute_functional(self.context, **step_kwargs)

                # 缓存结果
                self.result_manager.store(step.name, result)
                self.input_resolver.update_results(step.name, result)

                # 将结果合并到 context（向后兼容）
                step._merge_result_to_context(self.context, result)

                # 检查是否在步骤中标记了失败
                if self.context.failed_step:
                    raise PipelineException(
                        f"Pipeline 执行失败: 步骤 '{self.context.failed_step}' 失败"
                    )

            # 所有步骤成功完成
            logger.info(
                f"[PipelineExecutor] Pipeline 执行成功 (函数式模式) "
                f"(job_id={job_id}, 耗时={self.context.get_duration():.2f}秒)"
            )

            return self.result_manager.get_all()

        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise

        except Exception as exc:
            # Pipeline 执行失败
            logger.exception(
                f"[PipelineExecutor] Pipeline 执行失败 "
                f"(job_id={job_id}, 失败步骤={self.context.failed_step})"
            )

            # 更新任务状态
            self.context.update_job_status(
                ExecutionStatus.FAILED,
                f"Pipeline 执行失败: {str(exc)}"
            )

            # 重新抛出异常
            raise PipelineException(
                f"Pipeline 执行失败 (job_id={job_id}): {str(exc)}"
            ) from exc


__all__ = [
    "PipelineExecutor",
    "PipelineException",
]
