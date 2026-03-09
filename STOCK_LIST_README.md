# 股票列表管理说明

## 文件说明

### stock_list.txt
- 存储股票代码和名称
- 每行格式: `股票代码 股票名称`
- 支持 `#` 开头的注释行
- 可以手动编辑添加/删除股票

### stock_codes.txt
- 仅包含股票代码（逗号分隔）
- 由 `stock_list.txt` 自动生成

### .env
- 系统配置文件
- `STOCK_LIST` 变量存储当前分析的股票列表

## 使用方法

### 方式一: 手动编辑 stock_list.txt

1. 编辑 `stock_list.txt`，添加或删除股票
2. 运行同步命令:
   ```bash
   python update_stock_list.py --sync
   ```

### 方式二: 使用命令行工具

```bash
# 查看当前股票列表
python update_stock_list.py

# 添加股票
python update_stock_list.py --add 600000 浦发银行
python update_stock_list.py.py --add 600031  # 不指定名称也可以

# 删除股票
python update_stock_list.py --remove 600000

# 同步到 .env
python update_stock_list.py --sync
```

### 方式三: 直接修改 .env

直接编辑 `.env` 文件中的 `STOCK_LIST` 变量:
```bash
STOCK_LIST=600519,300750,601318,...
```

## 股票代码格式

- 沪市: `600xxx`, `601xxx`, `603xxx`, `688xxx` (科创板)
- 深市: `000xxx`, `002xxx`, `300xxx` (创业板)

## 当前配置

当前已配置 **65 只** 沪深300核心成分股。

如需添加完整沪深300或中证A500成分股，可以:
1. 从官方渠道下载完整名单
2. 复制到 `stock_list.txt`
3. 运行 `python update_stock_list.py --sync`

## 官方数据源

- 沪深300: https://www.csindex.com.cn/#/indices/family/detail?indexCode=000300
- 中证A500: https://www.csindex.com.cn/#/indices/family/detail?indexCode=000851
