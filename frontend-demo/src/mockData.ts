/**
 * Mock data for SatVLALab Frontend 2.0 Demo
 * Sourced from 前端展示用_真实运行结果记录.json + project configs
 */

export const TEST_IMAGE_URL = 'http://localhost:8000/data/100000007.png';

export const fastCloudCover = 0.041;
export const cloudCoverThreshold = 0.6;

export const visualFeatures = {
  objects: ['aircraft_carrier', 'destroyer'],
};

export const ragContext = `从知识图谱检索到的相关信息：

相关节点：
- 驱逐舰 (Destroyer)
- 航空母舰 (Aircraft Carrier)
- 集装箱船
- Level-1 (航母)
- Level-2 (驱逐舰)

相关关系：
航空母舰 (Aircraft Carrier) --[RELATIONTYPE1]--> 一级高价值目标
驱逐舰 (Destroyer) --[RELATIONTYPE6]--> 红外波段
Level-1 (航母) --[ATTRIBUTE]--> Track Duration >15秒
Level-1 (航母) --[ATTRIBUTE]--> Settle Time <2.0秒
Level-1 (航母) --[ATTRIBUTE]--> Max Slew <30.0度
Level-1 (航母) --[REQUIRE]--> ABORT_MANEUVER
Level-2 (驱逐舰) --[ATTRIBUTE]--> Max Slew <45.0度`;

/** 视觉描述（Perception 节点展示） */
export const visualDesc = `在这张卫星照片中，我们可以看到一个海军基地和港口。该地区有多个建筑物，其中包括一些大型的白色屋顶结构，这些可能是仓库或办公室。在水域上，有两个主要的船舶，一艘是航空母舰（Aircraft Carrier），而另一艘则是一艘驱逐舰（Destroyer）。航空母舰位于靠近岸边的区域，而驱逐舰则停泊在更远处的一个小岛附近。在周围的水域上，还有一些较小的船只，包括一个红色的小船和几个黑色的小船。`;

export const reasoningChain = [
  {
    round: 1,
    input_image: TEST_IMAGE_URL,
    tool_used: true,
    tool_name: 'image_binary',
    new_image: 'output/tool_binary.jpg',
  },
  {
    round: 2,
    input_image: 'output/tool_binary.jpg',
    tool_used: false,
    mode: 'B',
    soap_extracted: true,
  },
];

export const soapOutput = {
  raw: `<S>我认为这是一个海军基地和港口，包含多种类型的船舶和建筑物。我可以清楚地看到航空母舰和驱逐舰，以及其他小型船只和建筑物。</S>
<O>我可以看到航空母舰和驱逐舰的具体特征，如其大小、颜色和位置，以及周围环境的细节，如建筑物、水域和天气情况等等。这些特征让我相信，我已经拥有足够的信息来做出正确的判断。</O>
<A>基于我的观察和分析，我得出的结论是，这个场景非常重要，因为它涉及国家安全和战略决策。</A>
<P>收集更多的情报，以便更深入地了解这个场景；评估潜在的威胁和机会，并制定相应的计划和策略；确保我们的国防部队和盟友保持高度警惕状态，以应对任何不寻常的情况；维护良好的国际关系，以避免误解和冲突的发生。同时，也要注意保护自己的国家安全和利益，同时尊重他国的权益和安全。</P>`,
  subjective:
    '我认为这是一个海军基地和港口，包含多种类型的船舶和建筑物。我可以清楚地看到航空母舰和驱逐舰，以及其他小型船只和建筑物。',
  objective:
    '我可以看到航空母舰和驱逐舰的具体特征，如其大小、颜色和位置，以及周围环境的细节，如建筑物、水域和天气情况等等。这些特征让我相信，我已经拥有足够的信息来做出正确的判断。',
  assessment:
    '基于我的观察和分析，我得出的结论是，这个场景非常重要，因为它涉及国家安全和战略决策。',
  plan: '收集更多的情报，以便更深入地了解这个场景；评估潜在的威胁和机会，并制定相应的计划和策略；确保我们的国防部队和盟友保持高度警惕状态，以应对任何不寻常的情况；维护良好的国际关系，以避免误解和冲突的发生。同时，也要注意保护自己的国家安全和利益，同时尊重他国的权益和安全。',
};

/** 每一轮大模型的完整输出（含 <think> 和工具调用/ SOAP） */
export const reasoningRoundsOutput = [
  {
    round: 1,
    tool_used: true,
    tool_name: 'image_binary',
    modelOutput: `<think>
我们正在查看一幅卫星图像，该图像显示了一个海军基地和港口。其中有两种类型的船舶：一种是航空母舰，另一种是驱逐舰。我们还可以看到其他小型船只以及一些建筑物。这场景似乎非常重要，因为它涉及国家安全和战略决策。
然而，当前光学图像中舰船轮廓与背景的对比度不够明显，我无法完全确认目标类型和精确边界。我需要调用 image_binary 工具进行二值化处理，以强化轮廓、突出目标与背景的差异，从而更准确地识别舰船类型和位置，为后续决策提供可靠依据。
</think>

<use_mcp_tool>
<server_name>satellite_analysis</server_name>
<tool_name>image_binary</tool_name>
<arguments>{}</arguments>
</use_mcp_tool>`,
  },
  {
    round: 2,
    tool_used: false,
    mode: 'B',
    soap_extracted: true,
    modelOutput: `<think>
根据我所见的最新处理图像，特征已经变得更加明显。现在我能够区分出不同类型的船舶，并且能够确定它们的大小、颜色和位置。此外，我还可以识别出建筑物的基本形状和大小。这些特征让我相信，我已经拥有足够的信息来做出正确的判断。
</think>

<S>我认为这是一个海军基地和港口，包含多种类型的船舶和建筑物。我可以清楚地看到航空母舰和驱逐舰，以及其他小型船只和建筑物。</S>
<O>我可以看到航空母舰和驱逐舰的具体特征，如其大小、颜色和位置，以及周围环境的细节，如建筑物、水域和天气情况等等。这些特征让我相信，我已经拥有足够的信息来做出正确的判断。</O>
<A>基于我的观察和分析，我得出的结论是，这个场景非常重要，因为它涉及国家安全和战略决策。</A>
<P>收集更多的情报，以便更深入地了解这个场景；评估潜在的威胁和机会，并制定相应的计划和策略；确保我们的国防部队和盟友保持高度警惕状态，以应对任何不寻常的情况；维护良好的国际关系，以避免误解和冲突的发生。同时，也要注意保护自己的国家安全和利益，同时尊重他国的权益和安全。</P>`,
  },
];

/** Reasoning output for Intermediate panel: no SOAP, but include JSON */
export const reasoningRoundsForIntermediate = [
  {
    round: 1,
    tool_used: true,
    tool_name: 'image_binary',
    modelOutput: `<think>
我们正在查看一幅卫星图像，该图像显示了一个海军基地和港口。其中有两种类型的船舶：一种是航空母舰，另一种是驱逐舰。我们还可以看到其他小型船只以及一些建筑物。这场景似乎非常重要，因为它涉及国家安全和战略决策。
然而，当前光学图像中舰船轮廓与背景的对比度不够明显，我无法完全确认目标类型和精确边界。我需要调用 image_binary 工具进行二值化处理，以强化轮廓、突出目标与背景的差异，从而更准确地识别舰船类型和位置，为后续决策提供可靠依据。
</think>

<use_mcp_tool>
<server_name>satellite_analysis</server_name>
<tool_name>image_binary</tool_name>
<arguments>{}</arguments>
</use_mcp_tool>`,
  },
  {
    round: 2,
    tool_used: false,
    modelOutput: `<think>
根据我所见的最新处理图像，特征已经变得更加明显。现在我能够区分出不同类型的船舶，并且能够确定它们的大小、颜色和位置。此外，我还可以识别出建筑物的基本形状和大小。这些特征让我相信，我已经拥有足够的信息来做出正确的判断。
</think>

\`\`\`json
{"action": "TRACK", "params": {"slew_target": 15.0, "compression_rate": 0.0, "priority": "HIGH"}}
\`\`\``,
  },
];

export const reasoningFullText = `<think>
根据我所见的最新处理图像，特征已经变得更加明显。现在我能够区分出不同类型的船舶，并且能够确定它们的大小、颜色和位置。此外，我还可以识别出建筑物的基本形状和大小。这些特征让我相信，我已经拥有足够的信息来做出正确的判断。
</think>

<S>我认为这是一个海军基地和港口，包含多种类型的船舶和建筑物。我可以清楚地看到航空母舰和驱逐舰，以及其他小型船只和建筑物。</S>
<O>我可以看到航空母舰和驱逐舰的具体特征，如其大小、颜色和位置，以及周围环境的细节，如建筑物、水域和天气情况等等。这些特征让我相信，我已经拥有足够的信息来做出正确的判断。</O>
<A>基于我的观察和分析，我得出的结论是，这个场景非常重要，因为它涉及国家安全和战略决策。</A>
<P>收集更多的情报，以便更深入地了解这个场景；评估潜在的威胁和机会，并制定相应的计划和策略；确保我们的国防部队和盟友保持高度警惕状态，以应对任何不寻常的情况；维护良好的国际关系，以避免误解和冲突的发生。同时，也要注意保护自己的国家安全和利益，同时尊重他国的权益和安全。</P>`;

export const finalDecision =
  '{"action": "TRACK", "params": {"slew_target": 15.0, "compression_rate": 0.0, "priority": "HIGH"}}';

// ─── LLaVA Control Panel options (Mock) ─────────────────────────────────
export const visionHeadOptions = [
  { value: 'clip', label: 'openai/clip-vit-large' },
  { value: 'siglip', label: 'google/siglip-so400m' },
  { value: 'dinov2', label: 'facebook/dinov2-large' },
];

export const mlpProjectorOptions = [
  { value: '2layer', label: '2-Layer MLP' },
  { value: '3layer', label: '3-Layer MLP' },
  { value: 'qformer', label: 'Q-Former' },
];

export const llmOptions = [
  { value: 'vicuna_7b', label: 'lmsys/vicuna-7b-v1.5' },
  { value: 'mistral_7b', label: 'mistralai/Mistral-7B-Instruct' },
  { value: 'qwen2.5_7b', label: 'Qwen/Qwen2.5-7B-Instruct' },
];

/** 与 multiagent 阶段四 Tavily 联网检索一致时的算法取值 */
export const RETRIEVAL_ALGORITHM_WEB_SEARCH = 'web_search';

// ─── RAG Configuration（与后端实际检索解耦）────────────────────────────────
export const knowledgeBaseOptions = [
  { value: 'test', label: 'Neo4j 图 test' },
  { value: 'maritime_intel', label: 'maritime_intel' },
  { value: 'satellite_ops', label: 'satellite_ops' },
];

export const retrievalAlgorithmOptions = [
  { value: RETRIEVAL_ALGORITHM_WEB_SEARCH, label: 'TAVILY网络搜索' },
  { value: 'neo4j_cypher', label: 'Neo4j Cypher 检索' },
  { value: 'vector_similarity', label: '向量相似度' },
  { value: 'hybrid_graph', label: '图 + 向量混合' },
];

// ─── Skill Library (CV Tools) - from modules/cv_tools.py + mock ───────────
export const skillLibraryTools = [
  { id: 'cv_tools',    label: 'CV_Tools',       desc: 'Core CV toolkit: dehaze / SR / binarize / grey' },
  { id: 'sar_decode',  label: 'SAR_Decode',      desc: 'SAR image decoding & amplitude-to-dB conversion' },
  { id: 'change_det',  label: 'Change_Detect',   desc: 'Multi-temporal change detection between image pairs' },
  { id: 'cloud_mask',  label: 'Cloud_Mask',      desc: 'Cloud & shadow masking for optical satellite imagery' },
  { id: 'obj_detect',  label: 'Obj_Detect',      desc: 'GroundingDINO open-vocabulary object detection' },
  { id: 'geo_rect',    label: 'Geo_Rectify',     desc: 'Geometric rectification & orthorectification' },
];

// ─── Action MLP options (task-dependent naming) ──────────────────────────
export const actionMlpOptions = [
  { value: 'track_mlp', label: 'Track-Task MLP' },
  { value: 'scan_mlp', label: 'Scan-Task MLP' },
  { value: 'emergency_mlp', label: 'Emergency-Task MLP' },
];

// ─── Action Result Output (VLM→Action 执行结果，展示于右侧底部) ─────────
export const actionResultOutput = {
  action: 'TRACK',
  satComms: {
    compressionRate: 0.65,
    downlinkPriority: 'HIGH',
  },
  satAttitude: {
    rollAngle: 15.0,
    pitchAngle: -2.5,
    yawAngle: 8.0,
  },
};
