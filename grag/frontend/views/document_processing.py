"""
Document Processing Page View
文檔處理頁面，主要業務邏輯的視圖組合
"""
import asyncio
import streamlit as st
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from grag.frontend.components import FileUpload, ProcessingDisplay
# from grag.frontend.services import FileProcessingService  # TODO: 實作此服務
from grag.frontend.utils import MAX_FILES, SUPPORTED_FORMATS, format_batch_results, display_metrics_grid
from grag.ingestion.indexing.ingestion_service import IngestionService

def render_document_processing_page(config: Dict[str, Any]):
    """
    渲染文檔處理頁面

    Args:
        config: 應用配置字典
    """
    # 初始化組件
    upload_component = FileUpload()
    processing_display = ProcessingDisplay()

    # 獲取配置
    vlm_strategy = config.get('vlm_strategy', '自動判斷')
    force_vlm = config.get('force_vlm', None)
    embedding_provider = config.get('embedding_provider', 'sentence_transformers')

    # 文件上傳區域
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 📤 文件上傳模式")

        # 選擇上傳模式
        upload_mode = st.radio(
            "選擇上傳類型", ["單個文件", "批量上傳"],
            key="upload_mode_radio",
            help="單個文件: 上傳一個文件進行處理 | 批量上傳: 上傳多個文件同時處理"
        )

    with col2:
        # 顯示配置摘要
        st.markdown("### ⚙️ 當前配置")
        st.info(f"""
        **VLM策略**: {vlm_strategy}
        **嵌入模型**: {embedding_provider}
        **文件限制**: {MAX_FILES} 個
        """)

    # 根據模式處理文件
    if upload_mode == "單個文件":
        _handle_single_file_upload(vlm_strategy, force_vlm, embedding_provider)
    else:
        _handle_batch_file_upload(vlm_strategy, force_vlm, embedding_provider)

def _handle_single_file_upload(vlm_strategy: str, force_vlm: bool, embedding_provider: str):
    """處理單個文件上傳"""
    st.markdown("### 📄 單個文件上傳")

    # 文件上傳器
    uploaded_file = st.file_uploader(
        "選擇測試文檔",
        type=SUPPORTED_FORMATS,
        help=f"支援的文件格式: {', '.join(SUPPORTED_FORMATS).upper()}",
        key="single_file_uploader"
    )

    if uploaded_file is not None:
        # 顯示文件資訊
        _display_file_info(uploaded_file)

        # 處理按鈕
        if st.button("🚀 開始處理", type="primary", use_container_width=True):
            _process_single_file(uploaded_file, force_vlm, embedding_provider)

def _handle_batch_file_upload(vlm_strategy: str, force_vlm: bool, embedding_provider: str):
    """處理批量文件上傳"""
    st.markdown("### 📂 批量文件上傳")

    # 批量文件上傳器
    uploaded_files = st.file_uploader(
        "選擇多個測試文檔",
        type=SUPPORTED_FORMATS,
        accept_multiple_files=True,
        help=f"支援的文件格式: {', '.join(SUPPORTED_FORMATS).upper()}，一次最多 {MAX_FILES} 個文件",
        key="batch_file_uploader"
    )

    if uploaded_files:
        if len(uploaded_files) > MAX_FILES:
            st.error(f"🚫 一次性最多只能上傳 {MAX_FILES} 個文件。您目前選擇了 {len(uploaded_files)} 個文件。")
            return

        st.success(f"📂 已選擇 {len(uploaded_files)} 個文件")

        # 處理按鈕
        if st.button(f"🚀 批量處理 {len(uploaded_files)} 個文件", type="primary", use_container_width=True):
            _process_batch_files(uploaded_files, force_vlm, embedding_provider)

def _display_file_info(uploaded_file):
    """顯示上傳文件的資訊"""
    filename = uploaded_file.name
    file_ext = Path(filename).suffix.lower()

    st.success(f"📄 已選擇: {filename}")

    # 文件資訊
    from grag.frontend.utils import get_file_info
    file_info = get_file_info(uploaded_file)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📏 大小", file_info['size_formatted'])
    with col2:
        st.metric("🏷️ 格式", file_ext.upper())
    with col3:
        status = "✅ 支援" if file_info['is_supported'] else "❌ 不支援"
        st.metric("📋 狀態", status)

def _process_single_file(uploaded_file, force_vlm: bool, embedding_provider: str):
    """處理單個文件"""
    # 創建進度顯示
    progress_bar = st.progress(0, "初始化處理...")
    status_text = st.empty()
    result_area = st.empty()

    try:
        # 保存文件到臨時位置
        with st.spinner("準備文件..."):
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{uploaded_file.name}") as tmp_file:
                tmp_file.write(uploaded_file.read())
                file_path = Path(tmp_file.name)

        progress_bar.progress(20, "初始化處理服務...")

        # 初始化處理服務
        ingestion_service = IngestionService()

        progress_bar.progress(40, "開始文件處理...")

        # 執行處理
        status_text.text("🎯 正在處理文件...")

        # 檢查事件循環狀態
        try:
            asyncio.get_running_loop()
            # 如果能夠獲取到運行中的循環，就不做任何事
        except RuntimeError:
            # 如果事件循環不存在，使用 nest_asyncio
            import nest_asyncio
            nest_asyncio.apply()

        start_time = asyncio.get_event_loop().time()

        # 注意：這裡的實現可能需要根據實際的 IngestionService API 調整
        result = asyncio.run(ingestion_service.ingest_document_enhanced(
            file_path=file_path,
            force_vlm=force_vlm
            # embedding_provider 參數可能需要添加到 API 中
        ))

        processing_time = asyncio.get_event_loop().time() - start_time

        progress_bar.progress(100, "處理完成！")

        # 顯示結果
        with result_area.container():
            if result.get("success"):
                st.success("🎉 處理成功！")

                # 處理統計
                metadata = result.get("metadata", {})
                chunks_created = metadata.get("chunks_created", 0)
                embeddings_created = metadata.get("embeddings_created", 0)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("⏱️ 處理時間", f"{processing_time:.1f}s")
                with col2:
                    st.metric("📊 分塊數", chunks_created)
                with col3:
                    st.metric("🧮 向量數", embeddings_created)

                # 處理模塊資訊
                strategy_used = result.get("strategy_used", {})
                if strategy_used:
                    st.markdown("#### 🔧 處理模塊")
                    processing_modules = _format_processing_modules(strategy_used)
                    st.info(f"🛠️ **處理鏈**: {processing_modules}")

                # 嵌入資訊
                if embeddings_created > 0:
                    provider_name = metadata.get("embedding_provider", embedding_provider).upper()
                    dimension = metadata.get("embedding_dimension", "N/A")

                    # 嘗試獲取實際的.embedding_dimension信息
                    if dimension == "N/A" and result.get("statistics", {}).get("embeddings", {}).get("dimension"):
                        dimension = result.get("statistics", {}).get("embeddings", {}).get("dimension")

                    st.info(f"🤖 **嵌入資訊**: 使用 {provider_name} 模型，"
                           f"向量維度: {dimension}，生成向量: {embeddings_created} 個")

            else:
                st.error(f"❌ 處理失敗: {result.get('error', '未知錯誤')}")

        # 清理臨時文件
        try:
            file_path.unlink(missing_ok=True)
        except:
            pass

    except Exception as e:
        st.error(f"❌ 處理過程發生錯誤: {str(e)}")

    finally:
        # 清理進度顯示
        progress_bar.empty()
        status_text.empty()

def _process_batch_files(uploaded_files: List, force_vlm: bool, embedding_provider: str):
    """批量處理文件"""
    total_files = len(uploaded_files)

    # 創建整體進度顯示
    main_progress = st.progress(0, f"準備處理 {total_files} 個文件...")
    status_text = st.empty()
    results_summary = st.empty()

    # 收集處理結果
    successful_uploads = 0
    failed_uploads = 0
    processing_results = []

    try:
        # 初始化處理服務
        ingestion_service = IngestionService()

        for i, uploaded_file in enumerate(uploaded_files):
            filename = uploaded_file.name
            current_progress = i / total_files

            # 更新進度
            main_progress.progress(current_progress, f"處理文件 {i+1}/{total_files}: {filename}")
            status_text.text(f"正在處理: {filename}")

            try:
                # 保存文件到臨時位置
                with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    file_path = Path(tmp_file.name)

                # 處理文件 - 檢查事件循環
                try:
                    asyncio.get_running_loop()
                    # 如果能夠獲取到運行中的循環，就不做任何事
                except RuntimeError:
                    # 如果事件循環不存在，使用 nest_asyncio
                    import nest_asyncio
                    nest_asyncio.apply()

                result = asyncio.run(ingestion_service.ingest_document_enhanced(
                    file_path=file_path,
                    force_vlm=force_vlm
                ))

                # 記錄結果
                processing_results.append({
                    'filename': filename,
                    'success': result.get('success', False),
                    'metadata': result.get('metadata', {}),
                    'error': result.get('error')
                })

                if result.get('success'):
                    successful_uploads += 1
                    st.success(f"✅ {filename} 處理成功")
                else:
                    failed_uploads += 1
                    st.error(f"❌ {filename} 處理失敗: {result.get('error', '未知錯誤')}")

                # 清理臨時文件
                try:
                    file_path.unlink(missing_ok=True)
                except:
                    pass

            except Exception as e:
                failed_uploads += 1
                processing_results.append({
                    'filename': filename,
                    'success': False,
                    'error': str(e)
                })
                st.error(f"❌ {filename} 處理異常: {str(e)}")

        # 更新最終進度
        main_progress.progress(1.0, "批量處理完成！")

        # 顯示總結結果
        with results_summary.container():
            st.markdown("### 📊 批量處理結果總結")

            # 結果統計
            formatted_results = format_batch_results(processing_results)
            display_metrics_grid({
                key: str(value) if not isinstance(value, str) else value
                for key, value in formatted_results.items()
            }, columns=2)

            if successful_uploads > 0:
                st.success(f"🎉 批量上傳完成！成功處理 {successful_uploads} 個文件。")
            else:
                st.error("❌ 沒有成功處理任何文件。")

    except Exception as e:
        st.error(f"❌ 批量處理過程中發生錯誤: {str(e)}")

    finally:
        # 清理進度顯示
        main_progress.empty()
        status_text.empty()

def _format_processing_modules(strategy_used: Dict[str, Any]) -> str:
    """格式化處理模塊資訊顯示"""
    modules = []

    # 處理主要策略
    if strategy_used.get("vlm_used"):
        if strategy_used.get("vlm_success"):
            # VLM成功的情況
            processing_layer = strategy_used.get("processing_layer", "").lower()
            if processing_layer == "vlm":
                vlm_provider = strategy_used.get("vlm_provider", "unknown")
                if vlm_provider == "ollama":
                    modules.append("📅 Ollama本地VLM")
                elif vlm_provider == "openai":
                    modules.append("🌐 OpenAI雲端VLM")
                else:
                    modules.append("🤖 VLM服務")
            elif processing_layer == "mineru":
                modules.append("📄 MinerU PDF解析器")
            elif processing_layer == "ocr":
                modules.append("📝 Tesseract OCR")
            else:
                modules.append(f"⚡ {processing_layer.upper()}")
        else:
            # VLM失敗，顯示fallback
            processing_layer = strategy_used.get("processing_layer", "").lower()
            modules.append(f"⚠️ VLM降級至{processing_layer}")
    else:
        modules.append("📝 直接文字處理")

    # 添加LangChain
    if strategy_used.get("langchain_loaded"):
        modules.append("🔗 LangChain")

    # 添加分塊和嵌入
    modules.extend(["📊 LlamaIndex分塊", "🧮 SentenceTransformers嵌入"])

    # 組合成鏈
    return " → ".join(modules)
