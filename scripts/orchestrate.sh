#!/usr/bin/env bash
# orchestrate.sh - 5つのエージェントを並列起動するスクリプト
# 使い方: ./scripts/orchestrate.sh

set -euo pipefail

echo "======================================================"
echo "  椎葉村議会 議事録自動生成システム - エージェント並列起動"
echo "======================================================"
echo ""
echo "5つのエージェントをバックグラウンドで起動します..."
echo ""

# 実装担当エージェント: 音声→文字起こし→Word生成パイプラインを実装
claude --agent .claude/agents/implementer.md &
IMPLEMENTER_PID=$!
echo "[起動] implementer (PID: $IMPLEMENTER_PID) - パイプライン実装担当"

# テスト担当エージェント: テストを実行しカバレッジを測定・改善
claude --agent .claude/agents/tester.md &
TESTER_PID=$!
echo "[起動] tester     (PID: $TESTER_PID) - テスト・カバレッジ担当"

# レビュー担当エージェント: Gem指示書との整合性をコードレビュー
claude --agent .claude/agents/reviewer.md &
REVIEWER_PID=$!
echo "[起動] reviewer   (PID: $REVIEWER_PID) - コードレビュー担当"

# ドキュメント担当エージェント: APIドキュメントを生成
claude --agent .claude/agents/documenter.md &
DOCUMENTER_PID=$!
echo "[起動] documenter (PID: $DOCUMENTER_PID) - ドキュメント担当"

# QA担当エージェント: エンドツーエンドテストを実行
claude --agent .claude/agents/qa.md &
QA_PID=$!
echo "[起動] qa         (PID: $QA_PID) - QA・E2Eテスト担当"

echo ""
echo "全エージェントの完了を待機中..."
echo ""

# 全エージェントの完了を待つ
FAILED=0

wait $IMPLEMENTER_PID || { echo "✗ implementer が失敗しました"; FAILED=1; }
echo "✓ implementer 完了"

wait $TESTER_PID || { echo "✗ tester が失敗しました"; FAILED=1; }
echo "✓ tester 完了"

wait $REVIEWER_PID || { echo "✗ reviewer が失敗しました"; FAILED=1; }
echo "✓ reviewer 完了"

wait $DOCUMENTER_PID || { echo "✗ documenter が失敗しました"; FAILED=1; }
echo "✓ documenter 完了"

wait $QA_PID || { echo "✗ qa が失敗しました"; FAILED=1; }
echo "✓ qa 完了"

echo ""
echo "======================================================"
if [ $FAILED -eq 0 ]; then
    echo "  全エージェント正常終了"
else
    echo "  一部エージェントが失敗しました"
fi
echo "======================================================"

exit $FAILED
