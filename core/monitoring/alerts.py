"""告警模块

提供基于规则的告警功能，支持 AlertManager 集成。
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from core.config import MonitoringConfig
from core.logging_config import get_logger

logger = get_logger(__name__)


class AlertSeverity(str, Enum):
    """告警严重级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """告警状态"""
    FIRING = "firing"
    RESOLVED = "resolved"


@dataclass
class Alert:
    """告警数据"""
    name: str
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.FIRING
    message: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    value: Optional[float] = None
    threshold: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "severity": self.severity.value,
            "status": self.status.value,
            "message": self.message,
            "labels": self.labels,
            "annotations": self.annotations,
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "threshold": self.threshold,
        }

    def to_prometheus(self) -> Dict[str, Any]:
        """转换为 Prometheus AlertManager 格式"""
        return {
            "labels": {
                **self.labels,
                "alertname": self.name,
                "severity": self.severity.value,
                "status": self.status.value,
            },
            "annotations": {
                **self.annotations,
                "message": self.message,
                "summary": f"{self.severity.value.upper()}: {self.name}",
            },
            "startsAt": self.timestamp.isoformat(),
            "endsAt": self.timestamp.isoformat() if self.status == AlertStatus.RESOLVED else "",
        }


class AlertChannel(ABC):
    """告警通道抽象基类"""

    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """发送告警

        Args:
            alert: 告警对象

        Returns:
            bool: 是否发送成功
        """
        pass


class LogAlertChannel(AlertChannel):
    """日志告警通道

    将告警记录到日志中。
    """

    async def send(self, alert: Alert) -> bool:
        """发送告警到日志"""
        log_func = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.CRITICAL: logger.critical,
        }.get(alert.severity, logger.warning)

        log_func(
            f"Alert: {alert.name}",
            extra={
                "alert": alert.to_dict(),
            }
        )
        return True


class AlertManagerChannel(AlertChannel):
    """AlertManager 告警通道

    将告警发送到 Prometheus AlertManager。
    """

    def __init__(
        self,
        alertmanager_url: str = MonitoringConfig.DEFAULT_ALERTMANAGER_URL,
    ):
        self.alertmanager_url = alertmanager_url.rstrip("/")

    async def send(self, alert: Alert) -> bool:
        """发送告警到 AlertManager"""
        try:
            import httpx

            url = f"{self.alertmanager_url}/api/v1/alerts"
            payload = [alert.to_prometheus()]

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

            logger.info(f"Alert sent to AlertManager: {alert.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send alert to AlertManager: {e}", exc_info=True)
            return False


class WebhookAlertChannel(AlertChannel):
    """Webhook 告警通道

    通过 HTTP Webhook 发送告警。
    """

    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {"Content-Type": "application/json"}

    async def send(self, alert: Alert) -> bool:
        """通过 Webhook 发送告警"""
        try:
            import httpx

            payload = alert.to_dict()

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers=self.headers,
                )
                response.raise_for_status()

            logger.info(f"Alert sent via webhook: {alert.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to send alert via webhook: {e}", exc_info=True)
            return False


@dataclass
class AlertRule:
    """告警规则"""

    name: str
    condition: Callable[[], Union[bool, float]]
    severity: AlertSeverity = AlertSeverity.WARNING
    message_template: str = "Alert {name} triggered"
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    cooldown_seconds: float = 300  # 冷却时间（秒）
    threshold: Optional[float] = None

    # 内部状态
    _last_triggered: Optional[datetime] = None
    _current_alert: Optional[Alert] = None

    def check(self) -> Optional[Alert]:
        """检查告警规则

        Returns:
            Alert: 如果规则触发，返回告警对象；否则返回 None
        """
        if not self.enabled:
            return None

        # 检查冷却时间
        if self._last_triggered:
            elapsed = (datetime.now() - self._last_triggered).total_seconds()
            if elapsed < self.cooldown_seconds:
                return None

        try:
            result = self.condition()

            # 处理布尔结果
            if isinstance(result, bool):
                if result:
                    return self._create_alert()
                return None

            # 处理数值结果
            if isinstance(result, (int, float)):
                if self.threshold is not None:
                    if result >= self.threshold:
                        return self._create_alert(value=float(result))
                return None

            return None

        except Exception as e:
            logger.error(f"Error checking alert rule {self.name}: {e}", exc_info=True)
            return None

    def _create_alert(self, value: Optional[float] = None) -> Alert:
        """创建告警"""
        message = self.message_template.format(name=self.name, value=value)
        self._last_triggered = datetime.now()

        self._current_alert = Alert(
            name=self.name,
            severity=self.severity,
            message=message,
            labels=self.labels.copy(),
            annotations=self.annotations.copy(),
            value=value,
            threshold=self.threshold,
        )
        return self._current_alert

    def reset(self) -> None:
        """重置告警状态"""
        self._last_triggered = None
        self._current_alert = None


class AlertManager:
    """告警管理器

    管理告警规则和告警通道。
    """

    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.channels: List[AlertChannel] = []
        self._enabled = MonitoringConfig.DEFAULT_ALERTING_ENABLED

    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则"""
        self.rules[rule.name] = rule
        logger.info(f"Alert rule added: {rule.name}")

    def remove_rule(self, name: str) -> None:
        """移除告警规则"""
        if name in self.rules:
            del self.rules[name]
            logger.info(f"Alert rule removed: {name}")

    def add_channel(self, channel: AlertChannel) -> None:
        """添加告警通道"""
        self.channels.append(channel)
        logger.info(f"Alert channel added: {channel.__class__.__name__}")

    async def check_rules(self) -> List[Alert]:
        """检查所有告警规则

        Returns:
            List[Alert]: 触发的告警列表
        """
        if not self._enabled:
            return []

        triggered_alerts = []

        for rule in self.rules.values():
            alert = rule.check()
            if alert:
                triggered_alerts.append(alert)

        return triggered_alerts

    async def send_alert(self, alert: Alert) -> None:
        """发送告警到所有通道"""
        for channel in self.channels:
            try:
                await channel.send(alert)
            except Exception as e:
                logger.error(
                    f"Failed to send alert via {channel.__class__.__name__}: {e}",
                    exc_info=True
                )

    async def check_and_alert(self) -> int:
        """检查规则并发送告警

        Returns:
            int: 发送的告警数量
        """
        alerts = await self.check_rules()

        for alert in alerts:
            await self.send_alert(alert)

        return len(alerts)

    def enable(self) -> None:
        """启用告警"""
        self._enabled = True
        logger.info("Alerting enabled")

    def disable(self) -> None:
        """禁用告警"""
        self._enabled = False
        logger.info("Alerting disabled")

    def is_enabled(self) -> bool:
        """检查告警是否启用"""
        return self._enabled


# 全局告警管理器实例
_global_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """获取全局告警管理器"""
    global _global_alert_manager
    if _global_alert_manager is None:
        _global_alert_manager = AlertManager()
    return _global_alert_manager


def setup_alerting(
    enabled: bool = MonitoringConfig.DEFAULT_ALERTING_ENABLED,
    alertmanager_url: Optional[str] = None,
    webhook_urls: Optional[List[str]] = None,
) -> AlertManager:
    """设置告警系统

    Args:
        enabled: 是否启用告警
        alertmanager_url: AlertManager URL
        webhook_urls: Webhook URL 列表

    Returns:
        AlertManager: 告警管理器实例
    """
    manager = get_alert_manager()

    if enabled:
        manager.enable()
    else:
        manager.disable()

    # 添加日志通道（默认）
    manager.add_channel(LogAlertChannel())

    # 添加 AlertManager 通道
    if alertmanager_url:
        manager.add_channel(AlertManagerChannel(alertmanager_url))
        logger.info(f"AlertManager channel configured: {alertmanager_url}")

    # 添加 Webhook 通道
    if webhook_urls:
        for url in webhook_urls:
            manager.add_channel(WebhookAlertChannel(url))
        logger.info(f"Webhook channels configured: {len(webhook_urls)}")

    return manager


async def check_alert_rules() -> List[Alert]:
    """检查所有告警规则

    Returns:
        List[Alert]: 触发的告警列表
    """
    manager = get_alert_manager()
    return await manager.check_rules()


async def send_alert(
    name: str,
    severity: AlertSeverity = AlertSeverity.WARNING,
    message: str = "",
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None,
    value: Optional[float] = None,
    threshold: Optional[float] = None,
) -> None:
    """发送告警

    Args:
        name: 告警名称
        severity: 严重级别
        message: 告警消息
        labels: 标签
        annotations: 注释
        value: 当前值
        threshold: 阈值
    """
    alert = Alert(
        name=name,
        severity=severity,
        message=message,
        labels=labels or {},
        annotations=annotations or {},
        value=value,
        threshold=threshold,
    )

    manager = get_alert_manager()
    await manager.send_alert(alert)


# 预定义的告警规则
def create_high_error_rate_rule(
    service_name: str,
    threshold: float = MonitoringConfig.HIGH_ERROR_RATE_THRESHOLD,
    window_seconds: int = 60,
) -> AlertRule:
    """创建高错误率告警规则"""
    # 这里需要实际实现错误率计算
    # 简化版本：返回一个占位符规则
    return AlertRule(
        name=f"{service_name}_high_error_rate",
        condition=lambda: False,  # 需要实际实现
        severity=AlertSeverity.WARNING,
        message_template=f"High error rate detected for {service_name}",
        threshold=threshold,
    )


def create_high_latency_rule(
    service_name: str,
    threshold: float = MonitoringConfig.HIGH_LATENCY_THRESHOLD_SECONDS,
) -> AlertRule:
    """创建高延迟告警规则"""
    return AlertRule(
        name=f"{service_name}_high_latency",
        condition=lambda: False,  # 需要实际实现
        severity=AlertSeverity.WARNING,
        message_template=f"High latency detected for {service_name}",
        threshold=threshold,
    )


def create_high_memory_usage_rule(
    threshold: float = MonitoringConfig.MEMORY_USAGE_WARNING_THRESHOLD,
) -> AlertRule:
    """创建高内存使用告警规则"""
    def check_memory() -> bool:
        import psutil
        memory = psutil.virtual_memory()
        usage = memory.percent / 100
        return usage >= threshold

    return AlertRule(
        name="high_memory_usage",
        condition=check_memory,
        severity=AlertSeverity.WARNING,
        message_template=f"High memory usage: {{value:.1%}}",
        threshold=threshold,
        cooldown_seconds=1800,  # 30 分钟冷却
    )
