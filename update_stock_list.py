#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票列表更新工具

用法:
    python update_stock_list.py          # 从 stock_list.txt 同步到 .env
    python update_stock_list --add 600000  # 添加一只股票
    python update_stock_list --remove 600000  # 删除一只股票
"""

import os
import re
import argparse
from pathlib import Path


def read_stock_list(file_path='stock_list.txt'):
    """从 stock_list.txt 读取股票代码"""
    codes = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过注释和空行
            if line and not line.startswith('#'):
                parts = line.split()
                if len(parts) >= 1:
                    code = parts[0]
                    if code.isdigit() and len(code) == 6:
                        codes.append(code)
    return codes


def update_env_stock_list(codes):
    """更新 .env 文件中的 STOCK_LIST"""
    env_path = Path('.env')
    if not env_path.exists():
        print('错误: .env 文件不存在')
        return False

    stock_list_str = ','.join(codes)

    # 读取 .env 文件
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换 STOCK_LIST
    pattern = r'^STOCK_LIST=.*$'
    replacement = f'STOCK_LIST={stock_list_str}'
    new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    # 写回 .env 文件
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    updated = False
    for i, line in enumerate(lines):
        if line.startswith('STOCK_LIST='):
            lines[i] = f'STOCK_LIST={stock_list_str}\n'
            updated = True
            break

    if not updated:
        # 如果没有找到 STOCK_LIST，添加到文件开头
        lines.insert(2, f'STOCK_LIST={stock_list_str}\n')

    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    return True


def add_stock(code, name=''):
    """添加股票到 stock_list.txt"""
    if not re.match(r'^\d{6}$', code):
        print(f'错误: 股票代码格式不正确: {code}')
        return False

    # 检查是否已存在
    codes = read_stock_list()
    if code in codes:
        print(f'股票 {code} 已存在')
        return True

    # 添加到文件
    with open('stock_list.txt', 'a', encoding='utf-8') as f:
        if name:
            f.write(f'{code} {name}\n')
        else:
            f.write(f'{code}\n')

    print(f'已添加股票: {code}')
    return True


def remove_stock(code):
    """从 stock_list.txt 删除股票"""
    lines = []
    removed = False

    with open('stock_list.txt', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith(code):
                removed = True
                continue
            lines.append(line)

    if removed:
        with open('stock_list.txt', 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f'已删除股票: {code}')
    else:
        print(f'股票 {code} 不存在')

    return removed


def main():
    parser = argparse.ArgumentParser(description='股票列表更新工具')
    parser.add_argument('--add', metavar='CODE', help='添加股票代码')
    parser.add_argument('--name', metavar='NAME', help='股票名称（配合 --add 使用）')
    parser.add_argument('--remove', metavar='CODE', help='删除股票代码')
    parser.add_argument('--sync', action='store_true', help='从 stock_list.txt 同步到 .env')

    args = parser.parse_args()

    if args.add:
        add_stock(args.add, args.name or '')
        codes = read_stock_list()
        update_env_stock_list(codes)
        print(f'已更新 .env，共 {len(codes)} 只股票')

    elif args.remove:
        remove_stock(args.remove)
        codes = read_stock_list()
        update_env_stock_list(codes)
        print(f'已更新 .env，共 {len(codes)} 只股票')

    elif args.sync:
        codes = read_stock_list()
        update_env_stock_list(codes)
        print(f'已同步到 .env，共 {len(codes)} 只股票')

    else:
        # 默认: 显示当前股票列表
        codes = read_stock_list()
        print(f'当前股票列表 ({len(codes)} 只):')
        print(','.join(codes))


if __name__ == '__main__':
    main()
