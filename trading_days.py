# -*- coding: utf-8 -*-
"""
===================================
交易日判断工具模块
===================================

职责：
1. 判断指定日期是否为交易日
2. 获取下一个交易日
3. 跳过周末和节假日

说明：
- A股交易日：周一至周五，排除法定节假日
- 使用 akshare 获取交易日历
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional

import akshare as ak

logger = logging.getLogger(__name__)


class TradingCalendar:
    """
    交易日历管理

    缓存交易日历数据，避免频繁请求
    """

    def __init__(self):
        self._trading_days = set()
        self._last_fetch_year = None
        self._fetch_year_range = 2  # 缓存前后几年的数据

    def _fetch_trading_days(self, target_date: date) -> set:
        """
        从 akshare 获取交易日历

        Args:
            target_date: 目标日期

        Returns:
            交易日集合（日期字符串格式 YYYYMMDD）
        """
        try:
            year = target_date.year

            # 如果已经缓存了该年份的数据，直接返回
            if self._last_fetch_year == year:
                return self._trading_days

            logger.info(f"获取 {year} 年交易日历...")

            # 获取前后几年的交易日历（缓存更多数据）
            trading_days = set()
            for y in range(year - self._fetch_year_range, year + self._fetch_year_range + 1):
                try:
                    # 获取该年份的所有交易日
                    df = ak.tool_trade_date_hist_sina()

                    if df is not None and not df.empty:
                        # akshare 返回的 trade_date 列是交易日
                        # 筛选目标年份的数据
                        df['trade_date'] = df['trade_date'].astype(str)
                        year_days = set(df[df['trade_date'].str.startswith(str(y))]['trade_date'])
                        trading_days.update(year_days)
                        logger.info(f"获取 {y} 年交易日 {len(year_days)} 天")
                except Exception as e:
                    logger.warning(f"获取 {y} 年交易日历失败: {e}")

            self._trading_days = trading_days
            self._last_fetch_year = year
            logger.info(f"交易日历缓存完成，共 {len(trading_days)} 天")

            return trading_days

        except Exception as e:
            logger.error(f"获取交易日历失败: {e}")
            # 返回空集合，失败时回退到简单判断
            return set()

    def is_trading_day(self, target_date: Optional[date] = None) -> bool:
        """
        判断指定日期是否为交易日

        Args:
            target_date: 目标日期（默认今天）

        Returns:
            是否为交易日
        """
        if target_date is None:
            target_date = date.today()

        # 先做简单判断：周末不是交易日
        weekday = target_date.weekday()
        if weekday >= 5:  # 5=周六, 6=周日
            return False

        try:
            # 获取交易日历
            trading_days = self._fetch_trading_days(target_date)

            if trading_days:
                # 检查目标日期是否在交易日历中
                # akshare 返回的格式是 YYYY-MM-DD
                date_str = target_date.strftime('%Y-%m-%d')
                is_trading = date_str in trading_days
                logger.debug(f"{date_str} 是否为交易日: {is_trading}")
                return is_trading
            else:
                # 如果获取交易日历失败，回退到简单判断
                # 工作日默认是交易日（排除周末）
                logger.warning("交易日历获取失败，使用简单判断（工作日=交易日）")
                return weekday < 5

        except Exception as e:
            logger.error(f"判断交易日失败: {e}")
            # 异常时回退到简单判断
            return weekday < 5

    def get_next_trading_day(self, target_date: Optional[date] = None, max_days: int = 10) -> Optional[date]:
        """
        获取下一个交易日

        Args:
            target_date: 起始日期（默认今天）
            max_days: 最多查找天数

        Returns:
            下一个交易日，如果找不到则返回 None
        """
        if target_date is None:
            target_date = date.today()

        # 从明天开始查找
        check_date = target_date + timedelta(days=1)

        for _ in range(max_days):
            if self.is_trading_day(check_date):
                return check_date
            check_date += timedelta(days=1)

        logger.warning(f"在 {max_days} 天内未找到下一个交易日")
        return None

    def is_market_open_time(self, current_time: Optional[datetime] = None) -> bool:
        """
        判断当前时间是否在交易时段内

        A股交易时段：
        - 上午：9:30 - 11:30
        - 下午：13:00 - 15:00

        Args:
            current_time: 当前时间（默认现在）

        Returns:
            是否在交易时段内
        """
        if current_time is None:
            current_time = datetime.now()

        # 检查是否为交易日
        if not self.is_trading_day(current_time.date()):
            return False

        # 检查时间
        hour = current_time.hour
        minute = current_time.minute
        time_value = hour * 100 + minute

        # 上午 9:30-11:30 或 下午 13:00-15:00
        return (930 <= time_value <= 1130) or (1300 <= time_value <= 1500)


# 全局单例
_trading_calendar_instance: Optional[TradingCalendar] = None


def get_trading_calendar() -> TradingCalendar:
    """获取交易日历单例"""
    global _trading_calendar_instance
    if _trading_calendar_instance is None:
        _trading_calendar_instance = TradingCalendar()
    return _trading_calendar_instance


def is_trading_day(target_date: Optional[date] = None) -> bool:
    """
    判断指定日期是否为交易日（便捷函数）

    Args:
        target_date: 目标日期（默认今天）

    Returns:
        是否为交易日
    """
    return get_trading_calendar().is_trading_day(target_date)


def get_next_trading_day(target_date: Optional[date] = None, max_days: int = 10) -> Optional[date]:
    """
    获取下一个交易日（便捷函数）

    Args:
        target_date: 起始日期（默认今天）
        max_days: 最多查找天数

    Returns:
        下一个交易日
    """
    return get_trading_calendar().get_next_trading_day(target_date, max_days)


if __name__ == "__main__":
    # 测试交易日判断
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
    )

    calendar = get_trading_calendar()

    today = date.today()
    print(f"\n=== 交易日判断测试 ===")
    print(f"今天: {today}")
    print(f"是否为交易日: {calendar.is_trading_day(today)}")

    next_trading = calendar.get_next_trading_day(today)
    print(f"下一个交易日: {next_trading}")

    # 测试未来几天
    print("\n=== 未来7天交易日历 ===")
    for i in range(7):
        check_date = today + timedelta(days=i)
        is_trading = calendar.is_trading_day(check_date)
        weekday_str = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][check_date.weekday()]
        print(f"{check_date} ({weekday_str}): {'交易日' if is_trading else '休市'}")

    # 测试交易时段
    print("\n=== 交易时段判断 ===")
    now = datetime.now()
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"是否在交易时段: {calendar.is_market_open_time(now)}")
