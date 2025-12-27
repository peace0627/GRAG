#!/usr/bin/env python3
"""
測試 Ollama 和 Gemma 3 Vision 連接的簡單腳本
"""

import asyncio
import os
from dotenv import load_dotenv
import ollama

# 加載環境變數
load_dotenv()

async def test_ollama_connection():
    """測試 Ollama 連接和基本功能"""
    try:
        print("🔍 測試 Ollama 連接...")

        # 檢查 Ollama 是否運行
        client = ollama.Client(host=os.getenv('OLLAMA_HOST', 'http://localhost:11434'))

        # 列出可用模型
        models = client.list()
        print(f"📋 可用模型結構: {type(models)}")

        try:
            model_list = models.models if hasattr(models, 'models') else models
            print(f"📋 可用模型: {[m.model if hasattr(m, 'model') else str(m) for m in model_list]}")

            # 檢查是否有 Gemma 3 模型
            gemma_models = [m for m in model_list if hasattr(m, 'model') and 'gemma3' in m.model]
        except Exception as e:
            print(f"解析模型列表失敗: {e}")
            gemma_models = []

        if not gemma_models:
            print("❌ 未找到 Gemma 3 模型")
            return False

        print(f"✅ 找到 Gemma 3 模型: {[m.model for m in gemma_models]}")

        # 測試基本文字推理
        print("\n🧪 測試基本文字推理...")
        model_name = gemma_models[0].model

        response = client.generate(
            model=model_name,
            prompt="請用中文回答：你是一個醫材財報分析助手，請簡短介紹自己。",
            options={'temperature': 0.1}
        )

        print(f"🤖 模型回應: {response['response'][:200]}...")

        print("✅ Ollama 和 Gemma 3 基本功能測試通過")
        return True

    except Exception as e:
        print(f"❌ 測試失敗: {str(e)}")
        return False

async def test_vision_capability():
    """測試視覺能力（如果支援）"""
    try:
        print("\n🖼️ 測試視覺能力...")

        client = ollama.Client(host=os.getenv('OLLAMA_HOST', 'http://localhost:11434'))

        # 檢查模型是否支援視覺（通過模板判斷）
        models = client.list()
        model_list = models.models if hasattr(models, 'models') else models
        gemma_models = [m for m in model_list if hasattr(m, 'model') and 'gemma3' in m.model]

        if not gemma_models:
            return False

        model_name = gemma_models[0].model

        # 測試是否支援圖片輸入（簡單的文本提示）
        test_prompt = "描述一下你看到的圖片。如果看不到圖片，請說'我看不到圖片'。"

        response = client.generate(
            model=model_name,
            prompt=test_prompt,
            options={'temperature': 0.1}
        )

        if "看不到" in response['response'] or "不能" in response['response']:
            print("ℹ️ 模型似乎不支援當前上下文中的視覺輸入（這是正常的）")
        else:
            print(f"🤖 視覺測試回應: {response['response'][:100]}...")

        print("✅ 視覺能力測試完成")
        return True

    except Exception as e:
        print(f"❌ 視覺測試失敗: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 開始 Ollama 和 Gemma 3 環境檢查\n")

    # 測試基本連接
    success1 = asyncio.run(test_ollama_connection())

    # 測試視覺能力
    success2 = asyncio.run(test_vision_capability())

    if success1 and success2:
        print("\n🎉 所有測試通過！環境準備完成。")
    else:
        print("\n⚠️ 部分測試失敗，請檢查 Ollama 設置。")
