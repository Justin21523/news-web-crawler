#!/bin/bash
# 監控 CKIP 管線進度
echo "======================================"
echo "📊 CKIP GPU 管線監控"
echo "======================================"
echo ""

# 檢查 tmux session
if tmux has-session -t ckip_pipeline 2>/dev/null; then
    echo "✅ tmux 會話: 運行中"
else
    echo "⚠️  tmux 會話: 未找到"
fi

echo ""

# 檢查程序
PROCESS=$(ps aux | grep "run_full_pipeline" | grep -v grep | head -1)
if [ -n "$PROCESS" ]; then
    PID=$(echo $PROCESS | awk '{print $2}')
    CPU=$(echo $PROCESS | awk '{print $3}')
    MEM=$(echo $PROCESS | awk '{print $4}')
    echo "✅ 程序運行中: PID=$PID, CPU=${CPU}%, MEM=${MEM}%"
else
    echo "⚠️  程序未運行"
fi

echo ""
echo "📝 最新進度:"
echo "--------------------------------------"
tail -8 /home/justin/web-projects/news-web-crawler/pipeline_tmux.log | grep -E "(進度|完成|步驟|CKIP|TF-IDF|匯出)" | tail -5

echo ""
echo "--------------------------------------"
echo "💡 提示:"
echo "  - 即時查看: tail -f /home/justin/web-projects/news-web-crawler/pipeline_tmux.log"
echo "  - 進入 tmux: tmux attach -t ckip_pipeline"
echo "  - 離開 tmux: Ctrl+B, D"
echo "  - 停止管線: tmux kill-session -t ckip_pipeline"
echo "======================================"
