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
2. **Smart Extraction (Cost-Optimized):**
    *   **Strategy A (Semantic):** 优先尝试提取 `Abstract`, `Introduction`, `Conclusion` 等高价值段落。如果提取内容充足 (>600 chars)，直接用于分析，极大节省 Token。
    *   **Strategy B (Positional):** 如果语义提取失败，回退到 "Head-4 Tail-5" 策略（前 4 页 + 后 5 页），确保覆盖开头和结尾。
    *   **Logic:** 自动剔除 References 和 Appendix，减少噪音。
    *   **Fallback:** 如果提取内容过少（<100字），标记为 `INSUFFICIENT_DATA`。
3. **Intelligence (Brain):**
    *   **Model:** Amazon Bedrock -> Claude 3 Haiku (速度快，成本极低)。
    *   **Prompt Logic:** 要求 AI 扮演研究馆员，输出严格的 JSON，包含：
        *   `summary`: 一句话核心贡献。
        *   `category`: 基于预定义列表（CS, Bio, Physics...）+ AI 智能推断的路径。
        *   `tags`: 提取 3-5 个语义标签。
    *   **Embedding (Vectorization):**
        *   **Model:** Amazon Titan Embeddings v2。
        *   **Input:** 拼接 `Title + Summary + Tags`。
        *   **Output:** 1024维向量，存入 DynamoDB，用于后续的语义检索。

4. **Persistence (Memory):**
    *   **Database:** DynamoDB (On-Demand Mode)。
    *   **State Lock:** 写入前检查 file_id，防止 S3 事件重试导致的重复计费。

5. **Action (Routing):**
    *   调用 S3 API 将物理文件移动到 `/processed/{Category}/{SubCategory}/`。

### Phase 2: The Frontend (Interaction)
* **Stack:** Streamlit (Python)。
* **Search Logic (Dual Mode):**
    *   **Mode A: Traditional Search (Keyword):**
        *   用户选择“精确搜索”模式。
        *   基于 DynamoDB 的 `FilterExpression` 或内存中的 Pandas 过滤。
        *   场景：已知文件名、特定标签（如 `#Transformer`）或作者。
    *   **Mode B: Natural Language Search (Semantic/RAG):**
        *   用户选择“AI 语义搜索”模式。
        *   输入自然语言（如“找一篇关于注意力机制的论文”）。
        *   流程：调用 Titan 生成查询向量 -> 计算余弦相似度 -> 返回 Top-K 结果。
    *   **Implementation:** 利用 Streamlit 的内存缓存机制加载 DynamoDB 数据，避免昂贵的向量数据库成本（适合 <10k 文档规模）。

## 4. Data Schema (DynamoDB)
**Table Name:** `DocuMetaTable`
**PartitionKey:** `file_id` (UUIDv4) - 确保全局唯一
**GSI (Index):** `category-index` (用于侧边栏导航)

```json
{
  "file_id": "550e8400-e29b...",
  "original_name": "Attention_is_all_you_need.pdf",
  "s3_key": "processed/ComputerScience/NLP/Attention.pdf",
  "upload_timestamp": "2023-10-27T10:00:00Z",
  "status": "AUTO_TAGGED", // UPLOADED | PROCESSING | AUTO_TAGGED | NEEDS_REVIEW | ERROR
  "is_verified": false,    // 人工审核状态
  
  // --- The Soul (AI 生成的元数据) ---
  "ai_analysis": {
      "summary": "Proposes the Transformer model, replacing RNNs with self-attention mechanisms.",
      "category_path": "ComputerScience/NLP",
      "tags": ["#Transformer", "#GoogleBrain", "#SOTA"],
      "confidence_score": 0.98
  },
  "embedding": [0.123, -0.456, ...], // 1024-dim vector (Titan v2)
  "user_notes": "" // 用户手动备注
}
```

## 5. Cost Control (防破产风控)
1. **Hard Limit:** $5.00/month Budget.
2. **Model:** Haiku Only.
3. **Token Optimization:** 
    *   优先使用语义提取（Semantic Extraction），仅发送几百个 Token 给 AI。
    *   正则过滤参考文献（References）和附录（Appendix）。
4. **Circuit Breaker:**
    Lambda 仅响应 `/inbox`。处理完立即移走文件，防止死循环。


## 7. LOGO
这个项目的痛点是解决习惯大量囤积文件的人群，而会这样做的这种人（学生 程序员 科研工作者等）基本都有仓鼠病，未来设计仓鼠形象。