#!/bin/bash
# Oracle Cloud (Ubuntu) 一键部署脚本
# 用法：bash setup.sh

set -e
PROJECT_DIR="$HOME/lof_arbitrage"

echo ">>> 安装系统依赖"
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv

echo ">>> 创建项目目录"
mkdir -p "$PROJECT_DIR"

echo ">>> 创建 Python 虚拟环境"
python3 -m venv "$PROJECT_DIR/venv"
source "$PROJECT_DIR/venv/bin/activate"

echo ">>> 安装 Python 依赖"
pip install --upgrade pip
pip install akshare pandas requests pytz

echo ">>> 配置 cron 定时任务"
# 每 5 分钟执行一次，覆盖 A 股交易时段（UTC 时间 01:00-07:30，即北京时间 09:00-15:30）
# Python 脚本内部会精确判断是否在交易时段
CRON_CMD="*/5 1-7 * * 1-5 cd $PROJECT_DIR && $PROJECT_DIR/venv/bin/python main.py >> $PROJECT_DIR/cron.log 2>&1"
(crontab -l 2>/dev/null | grep -v "lof_arbitrage"; echo "$CRON_CMD") | crontab -

echo ""
echo "============================================"
echo "部署完成！接下来："
echo "1. 上传项目文件到 ~/lof_arbitrage/"
echo "   scp -r ./lof_arbitrage/* ubuntu@<你的IP>:~/lof_arbitrage/"
echo ""
echo "2. 编辑配置，填入 PushPlus token："
echo "   nano ~/lof_arbitrage/config.py"
echo ""
echo "3. 测试运行："
echo "   cd ~/lof_arbitrage"
echo "   source venv/bin/activate"
echo "   python test_run.py --notify"
echo ""
echo "4. 查看 cron 日志："
echo "   tail -f ~/lof_arbitrage/cron.log"
echo "============================================"
