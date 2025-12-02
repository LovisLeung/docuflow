# DocuFlow - Intelligent Document Router & Retriever

## 1. Project Vision (项目愿景)
构建一个**企业级**的智能文档管理 Web 应用。
**核心价值：** 将非结构化的“死”文件（PDF），转化为结构化的“活”知识（带摘要、分类、标签）。
**解决痛点：** 解决学术论文与技术文档的“只存不看”和“检索困难”问题。

## 2. Product Experience (产品体验)
* **Form Factor:** Web Application (Streamlit).
* **User Journey:**
    1. **Ingest:** 用户拖拽上传 PDF 到网页。
    2. **Process:** 系统自动分析（约 5-10秒），显示 "Processing..."。
    3. **Organize:** 文件自动从“收件箱”移动到左侧的“分类树”中（如 `CS > AI > Transformers`）。
    4. **Retrieve:** 用户在搜索框输入“讲注意力机制的那篇”，系统瞬间返回相关论文卡片。

## 3. Architecture & Workflows (技术架构)

### Phase 1: The Backend (Ingestion Pipeline)
**核心思想：** Serverless 事件驱动，算力前置。
1. **Trigger:** File uploaded to S3 Bucket (`/inbox/`) -> Triggers Lambda.
2. **Smart Extraction:**
    Strategy: "3+2 Truncation" (前 3 页 + 后 2 页)。
    Logic: 仅提取 PDF 的头尾关键信息（Title, Abstract, Conclusion），放弃中间的公式推导和实验数据，将 Token 消耗控制在 3k 以内。
    Fallback: 如果提取内容过少（<100字），标记为 NEEDS_REVIEW，不强行分类。
3. **Intelligence (Brain):**
    Model: Amazon Bedrock -> Claude 3 Haiku (速度快，成本极低)。
    Prompt Logic: 要求 AI 输出严格的 JSON，包含：
        summary: 一句话核心贡献。
        category: 基于预定义列表（CS, Bio, Physics...）+ AI 智能推断的路径。
        tags: 提取 3-5 个语义标签。
4. **Persistence (Memory):**
    Database: DynamoDB (On-Demand Mode)。
    State Lock: 写入前检查 file_id，防止 S3 事件重试导致的重复计费。
5. **Action (Routing):**
    调用 S3 API 将物理文件移动到 /processed/{Category}/{SubCategory}/。

### Phase 2: The Frontend (Interaction)
* **Stack:**
    Streamlit (Python)。
* **Search Logic:**
    用户输入查询词 -> 前端（可选）进行关键词提取 -> 在 DynamoDB 的 summary 和 tags 字段中进行 Contains 查询。
    利用 AI 预生成的“高质量摘要”来实现比全文检索更准的“语义级”搜索。

## 4. Data Schema (DynamoDB)
**Table Name:** `DocuMetaTable`
**PartitionKey:** `file_id` (UUIDv4) - 确保全局唯一
GSI (Index): category-index (用于侧边栏导航)


```json
{
  "file_id": "550e8400-e29b...",
  "original_name": "Attention_is_all_you_need.pdf",
  "s3_key": "processed/ComputerScience/NLP/Attention.pdf",
  "upload_timestamp": "2023-10-27T10:00:00Z",
  "status": "COMPLETED", // UPLOADED | PROCESSING | COMPLETED | ERROR
  
  // --- The Soul (AI 生成的元数据) ---
  "ai_analysis": {
      "summary": "Proposes the Transformer model, replacing RNNs with self-attention mechanisms.",
      "category_path": "ComputerScience/NLP",
      "ai_tags": ["#Transformer", "#GoogleBrain", "#SOTA"],
      "user_tags": ["#ThesisReference"], // 用户手动补充的标签
      "confidence_score": 0.98
  }
}
```

## 5. Cost Control (防破产风控)
1. **Hard Limit:** $5.00/month Budget.
2. **Model:** Haiku Only.
3. **Circuit Breaker:**
    Lambda 仅响应 `/inbox`。
    处理完立即移走文件，防止死循环。
4. **Security:**
    Streamlit 前端通过 S3 Presigned URL 获取文件下载链接（时效性链接），不直接暴露 Bucket。

