# -*- coding: utf-8 -*-
"""
QVeris iFinD 数据源

使用 QVeris Search & Action Engine 获取同花顺 iFinD 的A股数据
- 无需注册 token (用户自备)
- 数据稳定
- 支持沪深两市
"""

import json
import logging
import requests
from typing import Optional
import pandas as pd
from datetime import datetime

from .base import BaseFetcher
from config import get_config

logger = logging.getLogger(__name__)


class QverisFetcher(BaseFetcher):
    """
    QVeris iFinD 数据获取器

    通过 QVeris REST API 直接调用同花顺 iFinD 接口获取A股数据
    """

    name = "QverisFetcher"
    priority = 0  # 最高优先级，因为数据稳定

    def __init__(self):
        super().__init__()
        config = get_config()
        self.api_key = config.qveris_api_key
        self.base_url = "https://qveris.ai/api/v1"
        self.search_id = None  # 缓存搜索ID

    def is_available(self) -> bool:
        """检查数据源是否可用"""
        return bool(self.api_key)

    def _get_search_id(self) -> Optional[str]:
        """获取或缓存搜索ID"""
        if self.search_id:
            return self.search_id

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "content-type": "application/json"
            }
            payload = {
                "query": "China A-share stock historical kline data iFinD",
                "limit": 3
            }

            response = requests.post(
                f"{self.base_url}/search",
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                self.search_id = data.get('search_id')
                if self.search_id:
                    logger.info(f"[Qveris] 获取到搜索ID: {self.search_id}")
                    return self.search_id
        except Exception as e:
            logger.warning(f"[Qveris] 搜索失败: {e}")

        return None

    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        从 QVeris iFinD 获取原始数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            原始数据 DataFrame
        """
        # 转换代码格式
        if stock_code.startswith('6'):  # 沪市
            ifind_code = f"{stock_code}.SH"
        elif stock_code.startswith(('0', '2', '3')):  # 深市
            ifind_code = f"{stock_code}.SZ"
        else:
            ifind_code = stock_code

        # 获取搜索ID
        sid = self._get_search_id()
        if not sid:
            raise Exception("无法获取 QVeris 搜索ID")

        # 调用 execute 接口 (使用正确的 API 格式)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "content-type": "application/json"
        }

        # 注意: QVeris API 使用 /tools/execute?tool_id= 格式
        # 参数名是 parameters 不是 params
        payload = {
            "search_id": sid,
            "parameters": {
                "codes": ifind_code,
                "startdate": start_date,
                "enddate": end_date,
                "indicators": "stock_all"
            }
        }

        logger.info(f"[Qveris] 调用 iFinD: {ifind_code}, {start_date} ~ {end_date}")

        response = requests.post(
            f"{self.base_url}/tools/execute",
            params={"tool_id": "ths_ifind.history_quotation.v1"},
            json=payload,
            headers=headers,
            timeout=60
        )

        if response.status_code != 200:
            raise Exception(f"QVeris API 错误: {response.status_code} - {response.text}")

        result = response.json()

        # 检查状态
        if not result.get('success'):
            raise Exception(f"QVeris 执行失败: {result.get('error_message', '未知错误')}")

        # 获取数据
        data = self._extract_data(result)

        # 转换为 DataFrame
        df = pd.DataFrame(data)

        logger.info(f"[Qveris] 获取成功: 共 {len(df)} 条数据")

        return df

    def _extract_data(self, result: dict) -> list:
        """从响应中提取股票数据"""
        # QVeris 返回的数据结构: {"result": {"data": [[{stock_data}, ...]]}}
        try:
            data = result.get('result', {}).get('data', [])
            # 数据是嵌套数组格式 [[{stock1_data}, ...]]
            if isinstance(data, list) and len(data) > 0:
                inner = data[0]
                if isinstance(inner, list):
                    return inner
                return data
            return []
        except Exception as e:
            logger.error(f"[Qveris] 数据解析失败: {e}")
            return []

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        标准化 iFinD 数据格式

        QVeris iFinD 返回的字段:
        - thscode: 股票代码 (如 "600519.SH")
        - time: 日期
        - open, high, low, close: OHLC价格
        - volume: 成交量
        - amount: 成交额
        - changeRatio: 涨跌幅
        """
        if df.empty:
            return df

        # 字段映射
        column_mapping = {
            'time': 'date',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume',
            'amount': 'amount',
            'changeRatio': 'pct_chg'
        }

        # 重命名列
        df = df.rename(columns=column_mapping)

        # 转换日期格式
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])

        # 添加股票代码
        if 'thscode' in df.columns and len(df) > 0:
            code = df['thscode'].iloc[0].split('.')[0]
        else:
            code = stock_code
        df['code'] = code

        # 选择需要的列
        standard_columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount', 'pct_chg']

        # 确保所有列都存在
        for col in standard_columns:
            if col not in df.columns:
                df[col] = None

        return df[['code'] + standard_columns]
