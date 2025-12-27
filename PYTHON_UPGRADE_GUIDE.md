# Python 升級指南 - 支援 LangChain 1.x / LangGraph 1.x

## 📋 升級總覽

本專案需要升級到 **LangChain 1.2.0** 和 **LangGraph 1.0.5**，這些版本需要 **Python 3.10+**。

## 🔍 當前狀態
- **當前 Python**: 3.9.6
- **目標 Python**: 3.10.12+ (推薦)
- **升級依賴**: LangChain 1.2.0, LangGraph 1.0.5

## 🚀 升級步驟

### 步驟 1: 備份重要數據
```bash
# 備份當前環境（可選但推薦）
pip freeze > requirements_backup.txt
```

### 步驟 2: 安裝 Python 3.10+

#### 選項 A: 使用 Homebrew (推薦)
```bash
# 安裝 Python 3.10
brew install python@3.10

# 驗證安裝
python3.10 --version
# 應顯示: Python 3.10.x

# 設定為預設 Python（可選）
echo 'export PATH="/opt/homebrew/opt/python@3.10/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### 選項 B: 使用 pyenv (靈活)
```bash
# 安裝 pyenv
brew install pyenv

# 安裝 Python 3.10.12
pyenv install 3.10.12

# 設定全域版本
pyenv global 3.10.12

# 重新載入 shell
exec $SHELL

# 驗證
python --version
# 應顯示: Python 3.10.12
```

### 步驟 3: 升級 pip
```bash
python -m pip install --upgrade pip
```

### 步驟 4: 安裝專案依賴
```bash
# 進入專案目錄
cd /Users/rex/grag

# 安裝所有依賴
pip install --upgrade -r requirements.txt
```

### 步驟 5: 驗證安裝
```bash
# 檢查版本
python --version
# 應顯示: Python 3.10.x

# 檢查關鍵套件
python -c "import langchain; print(f'LangChain: {langchain.__version__}')"
python -c "import langgraph; print(f'LangGraph: {langgraph.__version__}')"

# 應顯示:
# LangChain: 1.2.0
# LangGraph: 1.0.5
```

### 步驟 6: 測試專案功能
```bash
cd project

# 測試 Schema
python test_schema.py

# 測試 Vision Router
python test_vision_router.py

# 測試 Ollama 客戶端
python test_ollama_client.py
```

## ⚠️ 重要注意事項

### 相容性問題
1. **系統應用**: 升級 Python 可能影響系統其他應用
2. **舊腳本**: 使用 `python` 而不是 `python3` 的腳本可能需要調整
3. **虛擬環境**: 如果使用虛擬環境，需要重建

### 故障排除
```bash
# 如果遇到權限問題
pip install --user package_name

# 如果遇到路徑問題
export PATH="/opt/homebrew/opt/python@3.10/bin:$PATH"

# 檢查 Python 路徑
which python
which python3
which python3.10
```

### 回滾方案
如果遇到問題，可以回滾：
```bash
# 使用 pyenv 切換回舊版本
pyenv global 3.9.6

# 或重新安裝舊版本依賴
pip install langchain==0.3.27 langgraph==0.6.11
```

## 🔧 環境變數更新

升級後，更新 `.env` 檔案：
```bash
# Python 版本確認
PYTHON_VERSION=3.10.12

# 依賴版本記錄
LANGCHAIN_VERSION=1.2.0
LANGGRAPH_VERSION=1.0.5
```

## ✅ 升級完成檢查清單

- [ ] Python 版本 ≥ 3.10.0
- [ ] LangChain 版本 = 1.2.0
- [ ] LangGraph 版本 = 1.0.5
- [ ] 所有專案測試通過
- [ ] 核心功能正常工作

## 📞 支援

如果升級過程中遇到問題：
1. 檢查錯誤訊息
2. 確認網路連接
3. 考慮使用虛擬環境
4. 查看 Python 官方文檔

## 🎯 預期效益

升級後您將獲得：
- ✅ LangChain 1.x 的最新功能和效能改進
- ✅ LangGraph 1.x 的新架構優勢
- ✅ 更好的開發體驗和 API 設計
- ✅ 長期支援和安全性更新
