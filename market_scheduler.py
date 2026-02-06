# -*- coding: utf-8 -*-
"""
===================================
收盘复盘定时调度模块
===================================

职责：
1. 交易日每天指定时间执行大盘复盘分析
2. 自动过滤非交易日（周末、节假日）
3. 将复盘结果发送到指定邮箱
4. 支持命令行启动和配置文件启动

依赖：
- schedule: 轻量级定时任务库
- trading_days: 交易日判断模块
"""

import logging
import signal
import sys
import time
import threading
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """
    优雅退出处理器

    捕获 SIGTERM/SIGINT 信号，确保任务完成后再退出
    """

    def __init__(self):
        self.shutdown_requested = False
        self._lock = threading.Lock()

        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """信号处理函数"""
        with self._lock:
            if not self.shutdown_requested:
                logger.info(f"收到退出信号 ({signum})，等待当前任务完成...")
                self.shutdown_requested = True

    @property
    def should_shutdown(self) -> bool:
        """检查是否应该退出"""
        with self._lock:
            return self.shutdown_requested


class MarketScheduler:
    """
    收盘复盘定时任务调度器

    基于 schedule 库实现，支持：
    - 交易日每日定时执行
    - 自动过滤非交易日
    - 启动时立即执行（可选）
    - 优雅退出
    """

    def __init__(self, schedule_time: str = "15:05"):
        """
        初始化调度器

        Args:
            schedule_time: 每日执行时间，格式 "HH:MM"，默认 15:05（A股收盘后）
        """
        try:
            import schedule
            self.schedule = schedule
        except ImportError:
            logger.error("schedule 库未安装，请执行: pip install schedule")
            raise ImportError("请安装 schedule 库: pip install schedule")

        # 延迟导入 trading_days 避免循环依赖
        from trading_days import is_trading_day
        self.is_trading_day = is_trading_day

        self.schedule_time = schedule_time
        self.shutdown_handler = GracefulShutdown()
        self._task_callback: Optional[Callable] = None
        self._running = False

    def _should_execute_task(self) -> bool:
        """
        判断是否应该执行任务

        只在交易日执行

        Returns:
            是否应该执行
        """
        return self.is_trading_day()

    def set_daily_task(self, task: Callable, run_immediately: bool = True):
        """
        设置每日定时任务（仅在交易日执行）

        Args:
            task: 要执行的任务函数（无参数）
            run_immediately: 是否在设置后立即执行一次
        """
        self._task_callback = task

        # 设置每日定时任务，但会检查是否为交易日
        def scheduled_job():
            if self._should_execute_task():
                logger.info("今天是交易日，执行大盘复盘任务")
                self._safe_run_task()
            else:
                logger.info("今天不是交易日，跳过大盘复盘任务")

        self.schedule.every().day.at(self.schedule_time).do(scheduled_job)
        logger.info(f"已设置收盘复盘定时任务，执行时间: {self.schedule_time}（仅交易日）")

        if run_immediately:
            if self._should_execute_task():
                logger.info("立即执行一次任务...")
                self._safe_run_task()
            else:
                logger.info("今天不是交易日，跳过立即执行")

    def _safe_run_task(self):
        """安全执行任务（带异常捕获）"""
        if self._task_callback is None:
            return

        try:
            logger.info("=" * 50)
            logger.info(f"收盘复盘任务开始执行 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 50)

            self._task_callback()

            logger.info(f"收盘复盘任务执行完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            logger.exception(f"收盘复盘任务执行失败: {e}")

    def run(self):
        """
        运行调度器主循环

        阻塞运行，直到收到退出信号
        """
        self._running = True
        logger.info("收盘复盘调度器开始运行...")
        logger.info(f"下次执行时间: {self._get_next_run_time()}")

        while self._running and not self.shutdown_handler.should_shutdown:
            self.schedule.run_pending()
            time.sleep(30)  # 每30秒检查一次

            # 每小时打印一次心跳
            if datetime.now().minute == 0 and datetime.now().second < 30:
                logger.info(f"调度器运行中... 下次执行: {self._get_next_run_time()}")

        logger.info("收盘复盘调度器已停止")

    def _get_next_run_time(self) -> str:
        """获取下次执行时间"""
        jobs = self.schedule.get_jobs()
        if jobs:
            next_run = min(job.next_run for job in jobs)
            return next_run.strftime('%Y-%m-%d %H:%M:%S')
        return "未设置"

    def stop(self):
        """停止调度器"""
        self._running = False


def run_market_schedule(
    task: Callable,
    schedule_time: str = "15:05",
    run_immediately: bool = True
):
    """
    便捷函数：使用收盘复盘定时调度运行任务

    Args:
        task: 要执行的任务函数
        schedule_time: 每日执行时间（默认 15:05）
        run_immediately: 是否立即执行一次（默认 True）
    """
    scheduler = MarketScheduler(schedule_time=schedule_time)
    scheduler.set_daily_task(task, run_immediately=run_immediately)
    scheduler.run()


if __name__ == "__main__":
    # 测试收盘复盘定时调度
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    )

    def test_task():
        print(f"收盘复盘任务执行中... {datetime.now()}")
        time.sleep(2)
        print("收盘复盘任务完成!")

    print("启动收盘复盘测试调度器（按 Ctrl+C 退出）")
    run_market_schedule(test_task, schedule_time="15:05", run_immediately=True)
