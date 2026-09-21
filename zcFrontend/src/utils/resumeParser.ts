/**
 * 简历技能解析（纯前端）：别名字典 + 词边界匹配 + 结构化提取。
 * PDF/DOCX/TXT 文件解析均懒加载。
 */

export interface ParsedSkill {
  name: string
  confidence: number // 0-1
  hits: number
  /** 达标(有项目/经验上下文证据) / listed(仅技能清单罗列) */
  evidence: 'mastered' | 'listed'
  /** 实际命中的匹配词（字典名 + 命中别名去重），后端拿它与岗位技能点比对 */
  terms: string[]
}

/** 简历中识别出的一个项目：名称 + 含金量信号词 */
export interface ProjectInfo {
  name: string
  signals: string[]
}

export interface ResumeParseResult {
  skills: ParsedSkill[]
  years?: number
  education?: string
  certificates: string[]
  awards: string[]
  projects: ProjectInfo[]
  rawText: string
}

interface DictEntry {
  name: string
  aliases: string[]
  /** false 时仅匹配别名（Go/C 等易误报词） */
  matchCanonical: boolean
}

// 人工别名表：字典名 → 别名
// 只收本身陈述该能力的词，不收碰巧相关的泛词
const ALIASES: Record<string, string[]> = {
  'Python': ['python3', 'py'],
  '机器学习': ['machine learning', 'ml', '机器学习算法'],
  '深度学习': ['deep learning', 'dl', '深度神经网络'],
  '大模型': ['llm', 'large language model', '大语言模型', '大模型应用', '大型语言模型', 'llm应用'],
  'NLP': ['自然语言处理', 'nlu', 'nlp技术'],
  '计算机视觉': ['computer vision', 'opencv'],
  'Kubernetes': ['k8s', 'kubectl'],
  'C++': ['cpp', 'c/c++', 'cplusplus'],
  'C': ['c语言', 'c programming'],
  'Go': ['golang', 'go语言', 'go语言开发'],
  'TypeScript': ['typescript', 'ts'],
  'JavaScript': ['javascript', 'js', 'es6'],
  'SQL': ['结构化查询', 'sql语句', 'mybatis'],
  'MySQL': ['mysql', 'mysqld'],
  'Redis': ['redis'],
  'Kafka': ['kafka'],
  'RAG': ['检索增强生成', 'retrieval augmented', 'rag检索', 'rag技术', 'graphrag', '知识库检索', '向量检索'],
  'Prompt设计': ['prompt engineering', '提示词工程', '提示工程', 'prompt工程', '结构化抽取'],
  'Transformer': ['transformers', 'huggingface'],
  'BERT': ['bert模型'],
  'Vue': ['vue.js', 'vuejs', 'vue3', 'vue2', 'vue框架', 'vue 3', 'vue 2'],
  'React': ['reactjs', 'react.js', 'react框架'],
  '前端开发': ['web前端', 'h5'],
  'Docker': ['容器化', 'docker容器', '容器化部署', '容器编排'],
  '微服务': ['microservice', '微服务架构'],
  '数据分析': ['数据分析', 'data analysis'],
  '数据仓库': ['数仓', 'data warehouse'],
  '测试': ['自动化测试', '功能测试'],
  // 性能测试与性能优化分开，避免互判
  '性能测试': ['压测', '压力测试'],
  '性能优化': ['性能优化', '性能调优', '性能提升'],
  // 安全测试≠渗透测试，不收
  '渗透测试': ['pentest', '漏洞挖掘'],
  '网络协议': ['tcp/ip', 'http协议'],
  '架构设计': ['系统架构', '技术架构', '安全架构', '架构设计能力'],
  '人工智能': ['ai', 'artificial intelligence', 'ai应用', 'ai技术', 'ai辅助开发'],

  'Agent': ['智能体', '多智能体', 'multi-agent', 'ai agent', 'agent开发', '智能体开发'],
  'LangChain': ['langchain'],
  'LlamaIndex': ['llamaindex', 'llama index'],
  'LangGraph': ['langgraph'],
  'AutoGen': ['autogen', 'crewai', 'swarm'],
  'MoE': ['moe架构', '混合专家'],
  '扩散模型': ['diffusion', 'diffusion建模', 'stable diffusion'],
  '目标检测': ['yolo', 'yolov5', 'yolov8', 'object detection', '目标识别'],
  '模型微调': ['finetune', 'fine-tune', 'lora', 'qlora', 'sft'],
  '模型量化': ['qat', 'int8', '模型压缩'],
  '模型部署': ['模型部署', '推理部署', '模型上线', '部署链路', 'onnx runtime', 'tensorrt', 'tensorrt-llm'],
  '预训练': ['pretrain', 'pretraining', '预训练模型'],
  '强化学习': ['reinforcement learning', 'rlhf'],
  '知识蒸馏': ['distillation', '蒸馏'],
  '特征工程': ['feature engineering'],
  '增量学习': ['类别增量学习', '持续学习', 'continual learning', '灾难性遗忘'],
  '多模态': ['multimodal', '多模态大模型', '视觉语言模型', 'vlm'],
  '向量数据库': ['qdrant', 'chromadb', 'chroma', 'milvus', 'faiss', 'embedding', '向量检索', 'top-k召回', '相似度检索'],
  'MCP': ['mcp协议', 'model context protocol'],
  '高性能计算': ['hpc', 'cuda', '并行计算', '分布式训练', '分布式训练优化', 'ray'],
  '差分隐私': ['differential privacy'],
  '组合优化': ['组合优化', 'qaoa', 'qubo', '模拟退火', '遗传算法'],

  '数据标注': ['标注流程', '标注质检', '标注工作流', '标注规范', '数据标注流程'],
  '标注质量评估': ['iaa', 'inter-annotator agreement', '标注一致性', '置信度建模', '标注质量'],
  '标注工具': ['label studio', 'cvat', 'labelimg', 'doccano'],
  '数据治理': ['数据质量', '元数据', '数据血缘'],
  '数据流水线': ['数据流水线', 'data pipeline', '数据管道', '调度编排', 'airflow', 'dolphinscheduler'],
  '数据湖': ['iceberg', 'hudi', 'delta lake'],
  'ETL': ['etl', 'elt', '数据抽取'],

  'FastAPI': ['fastapi'],
  'Node.js': ['nodejs', 'node.js', 'node'],
  'SQLite': ['sqlite'],
  'JWT': ['jwt', '鉴权', 'token鉴权'],
  'gRPC': ['grpc', 'protobuf'],
  '组件化开发': ['组件化', '组件库', '组件封装'],
  'i18n': ['i18n', '国际化', '多语言切换'],
  'Element Plus': ['element plus', 'element ui'],
  '跨浏览器兼容': ['跨浏览器兼容', '浏览器兼容', '兼容性适配'],
  '大屏开发': ['大屏开发', '数据大屏', '可视化大屏'],
  '持续集成': ['ci/cd', '持续集成', '持续交付', 'jenkins', 'gitlab ci', 'github actions'],
  '云平台': ['aws', '阿里云', '腾讯云', 'azure', '华为云', '云平台'],
  '云安全': ['云安全', '云原生安全'],

  '电路设计': ['电路设计', '原理图', 'pcb', '硬件电路', '电路板'],
  '模拟电路': ['模拟电路', '数模混合'],
  '数字电路': ['数字电路', 'verilog', 'fpga'],
  '电路仿真': ['circuit simulation', 'multisim', 'pspice'],
  'MATLAB': ['matlab', 'simulink'],
  '示波器': ['示波器', 'oscilloscope'],
  '逻辑分析仪': ['逻辑分析仪', 'logic analyzer'],
  '硬件调试': ['硬件调试', '硬件测试', '板级调试'],
  '元器件选型': ['元器件选型', '器件选型', 'bom'],
  '电源完整性': ['电源完整性', '信号完整性'],
  'EMC设计': ['emc', 'emi', '电磁兼容'],
  '自动控制': ['自动控制', '控制算法', 'pid', '闭环控制'],
  '机电一体化': ['机电一体化', '机电系统'],
  '电机控制': ['bldc', 'pmsm', 'foc', '电机控制', '无刷电机'],
  'PLC': ['plc', '西门子plc', '三菱plc'],
  'KEIL': ['keil', 'mdk'],
  'CANoe': ['canoe', 'can总线', 'canalyzer'],
  'Android': ['android', '安卓'],
  'IoT': ['物联网', 'iot', 'mqtt'],
  '多传感器融合': ['多传感器融合', 'sensor fusion', '3d感知', '点云'],

  '产品规划': ['产品规划', '产品定位', '产品路线图', 'roadmap', '产品方向'],
  '需求分析': ['需求分析', '需求拆解', '需求梳理', '功能规划', '需求评审', '业务流程设计'],
  '需求优先级': ['需求优先级', '优先级管理', '需求排期', '优先级'],
  'PRD撰写': ['prd', '需求文档', '产品文档'],
  '用户故事': ['用户故事', 'user story'],
  'Jira': ['jira'],
  '原型设计': ['原型设计', '原型图', 'axure', 'figma', '陌刀', '墨刀', 'mockplus'],
  '竞品分析': ['竞品分析', '竞品调研'],
  '技术可行性评估': ['可行性分析', '技术可行性', '技术选型', '方案评审'],
  '用户研究': ['用户研究', '用户调研', '用户访谈', '问卷调研'],
  '项目管理': ['项目管理', '项目推进', '项目统筹', '任务分工', '资源协调', '排期管理', 'jira', 'confluence', 'pmp'],
  '敏捷开发': ['敏捷开发', 'scrum', '看板', '迭代开发', 'agile'],
  '跨部门协作': ['跨部门协作', '团队协作', '跨团队协作', '统筹协调', '组织协调', '协同推进', '跨职能协作'],
  '文档编写': ['文档编写', '技术文档', '文档撰写', '方案编写'],
  '工作流编排': ['工作流', 'dify', 'coze', 'n8n', '流程编排', '低代码'],

  '数据采集': ['数据采集', '爬虫', '爬取', '网络爬虫', '数据抓取', 'scrapy', '采集数据', '数据爬取'],
  '数据可视化': ['数据可视化', '可视化', '图表', '报表', 'echarts', 'tableau'],
  '监控告警': ['prometheus', 'grafana', 'elk', '日志分析', '监控告警', '可观测性'],
  'AI辅助开发': ['ai辅助开发', 'ai辅助编程', 'ai辅助编码', 'copilot', 'cursor', 'claude code', 'codex', 'ai编程助手'],
  '服务端部署': ['服务端部署', '服务部署', '服务器部署', '线上部署', '生产环境部署', '线上运维'],
  'DevSecOps': ['devsecops', '安全左移'],
  '学术论文': ['论文发表', '发表论文', '学术论文', '第一作者', 'sci论文', '期刊论文', 'ei论文'],
  'VueRouter': ['vuerouter', 'vue-router', 'vuex', 'vue router'],
  'Git': ['版本控制', 'gitlab', 'github', 'git版本控制'],
}

// 后端技能矩阵中的高频技术名词，避免漏识别
const SKILL_NAMES: string[] = [
  'PyTorch', 'TensorFlow', 'Keras', 'NumPy', 'Pandas', 'Scikit-learn', 'Matplotlib', 'Seaborn',
  'OpenCV', 'CUDA', 'ONNX', 'LangChain', 'LlamaIndex', 'GPT', 'LoRA', 'RLHF', 'GAN', 'Agent',
  '自然语言处理', '强化学习', '神经网络', '卷积神经网络', '循环神经网络', '多模态', '扩散模型',
  '微调', '知识蒸馏', '模型量化',
  'Java', 'Spring', 'Spring Boot', 'Spring Cloud', 'MyBatis', 'JVM', 'Golang', 'Node.js',
  '分布式', '高并发', '高可用', 'RESTful', 'gRPC', 'Dubbo', 'RabbitMQ', 'PostgreSQL', 'MongoDB', 'Elasticsearch',
  'Spark', 'Flink', 'Hadoop', 'Hive', 'ETL', '数据挖掘', '数据可视化', 'ClickHouse', 'OLAP', 'Tableau',
  'Webpack', 'Vite', 'Flutter', '小程序', '鸿蒙', 'HTML', 'CSS', 'ECharts',
  'DevOps', 'Jenkins', 'CI/CD', 'Prometheus', 'Grafana', 'Terraform', 'Ansible', 'Istio',
  '云原生', 'Linux', 'Nginx', 'Shell',
  '网络安全', '漏洞挖掘', 'XSS', 'SQL注入', 'Burp Suite', 'WAF', '零信任', '加密',
  'RTOS', 'ARM', '单片机', '嵌入式', '物联网', 'MCU', 'MQTT', 'PCB',
  '功能测试', '自动化测试', 'Selenium', 'JMeter', 'Postman', '回归测试', '测试用例',
  '需求分析', '项目管理', '用户研究', 'PRD', '敏捷开发', 'Git', '数据结构', '操作系统', '算法',
]

let _dict: DictEntry[] | null = null
function buildDict(): DictEntry[] {
  const map = new Map<string, DictEntry>()
  const add = (name: string, alias?: string) => {
    const n = (name || '').trim()
    if (!n) return
    if (!map.has(n)) map.set(n, { name: n, aliases: [], matchCanonical: true })
    if (alias) map.get(n)!.aliases.push(alias)
  }
  for (const [name, aliases] of Object.entries(ALIASES)) {
    for (const a of aliases) add(name, a)
  }
  for (const name of SKILL_NAMES) add(name)
  // 易误报词仅匹配别名
  for (const risky of ['C', 'Go']) {
    const e = map.get(risky)
    if (e) e.matchCanonical = false
  }
  return [...map.values()]
}
function getDict(): DictEntry[] {
  if (!_dict) _dict = buildDict()
  return _dict
}

function escapeReg(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
function skillRegex(term: string): RegExp {
  const esc = escapeReg(term)
  const hasCJK = /[\u4e00-\u9fff]/.test(term)
  // 纯 ASCII 词加后缀边界，避免子串误报
  // 不用后行断言（Safari<16.4 不支持），前缀边界改由 countUniqueHits 判断
  if (!hasCJK) return new RegExp(`${esc}(?![a-z0-9])`, 'gi')
  return new RegExp(esc, 'gi')
}
/** 按起始位置去重统计命中数 */
function countUniqueHits(terms: string[], lower: string): { hits: number; matched: string[] } {
  const positions = new Set<number>()
  const matched = new Set<string>()
  for (const term of terms) {
    const re = skillRegex(term)
    const ascii = !/[\u4e00-\u9fff]/.test(term)
    let m: RegExpExecArray | null
    while ((m = re.exec(lower)) !== null) {
      // 补前缀边界，等价于负向后行断言
      if (ascii && m.index > 0 && /[a-z0-9]/.test(lower[m.index - 1])) {
        if (m[0].length === 0) re.lastIndex++
        continue
      }
      positions.add(m.index)
      matched.add(term)
      if (m[0].length === 0) re.lastIndex++ // 防零宽死循环
    }
  }
  return { hits: positions.size, matched: [...matched] }
}

/** 泛用 ASCII 缩写，不构成技能身份 */
const GENERIC_ASCII = new Set([
  'ai', 'ml', 'dl', 'llm', 'api', 'sdk', 'ui', 'ux', 'os', 'db',
  'it', 'id', 'web', 'app', 'dev', 'ops', 'demo', 'proj', 'sys', 'code',
])

/** 别名筛选：太短的 ASCII 和泛用缩写别名不作为独立词面 */
function emitTerms(name: string, matched: string[]): string[] {
  const out = [name]
  for (const t of matched) {
    if (out.includes(t)) continue
    const asciiTokens = t.toLowerCase().match(/[a-z0-9+#.]+/g) || []
    if (asciiTokens.length > 0) {
      const strong = asciiTokens.filter(a => a.length >= 3 && !GENERIC_ASCII.has(a))
      if (strong.length === 0) continue
    }
    out.push(t)
  }
  return out
}

/** 落库 / 送后端的扁平技能词表：每条技能的 canonical + 命中别名。 */
export function flattenSkillTerms(skills: ParsedSkill[]): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const s of skills) {
    for (const t of s.terms?.length ? s.terms : [s.name]) {
      if (!seen.has(t)) {
        seen.add(t)
        out.push(t)
      }
    }
  }
  return out
}

/** 与 userSkills 一一对应的证据表（键 = 扁平词表里的每个词）。 */
export function skillEvidenceMap(skills: ParsedSkill[]): Record<string, 'mastered' | 'listed'> {
  const m: Record<string, 'mastered' | 'listed'> = {}
  for (const s of skills) {
    for (const t of s.terms?.length ? s.terms : [s.name]) m[t] = s.evidence
  }
  return m
}
function confidenceFor(hits: number): number {
  if (hits <= 0) return 0
  if (hits >= 4) return 0.95
  if (hits === 3) return 0.9
  if (hits === 2) return 0.82
  return 0.72
}

function extractYears(text: string): number | undefined {
  // 「年」与「经验」之间最多 15 个字符，避免跨句误匹配
  const re = /(\d{1,2})\s*年[^。；，,\n]{0,15}?经验/g
  let max: number | undefined
  let m: RegExpExecArray | null
  while ((m = re.exec(text)) !== null) {
    const v = parseInt(m[1], 10)
    if (v <= 30 && (max === undefined || v > max)) max = v
  }
  return max
}
function extractEducation(text: string): string | undefined {
  if (/博士/.test(text)) return '博士'
  if (/硕士/.test(text)) return '硕士'
  if (/本科/.test(text)) return '本科'
  if (/大专/.test(text)) return '大专'
  return undefined
}

/** 动作动词：出现在做事上下文的技能才记为达标 */
const ACTION_VERBS = /负责|开发|实现|搭建|设计|优化|使用|主导|参与|基于|完成|构建|部署|上线|应用|利用|维护|重构|编写|撰写|落地|交付|支撑|驱动|改造|升级|解决|调优|自研|集成|研发|迭代|承担|采用|借助|通过/

/** 证书：正则 -> 规范化标签 */
const CERT_PATTERNS: [RegExp, string][] = [
  [/软件设计师|系统架构设计师|系统分析师|网络工程师|数据库系统工程师|信息安全工程师|软考/, '软考'],
  [/CISSP/i, 'CISSP'],
  [/CISP/i, 'CISP'],
  [/CKA|CKAD|CKS/i, 'CKA'],
  [/PMP/i, 'PMP'],
  [/AWS Certified|AWS认证/i, 'AWS认证'],
  [/阿里云(ACA|ACP|ACE)/i, '阿里云认证'],
  [/华为(HCIA|HCIP|HCIE)/i, '华为认证'],
  [/CET-?4|CET-?6|英语四级|英语六级/i, '英语四六级'],
  [/雅思|IELTS/i, '雅思'],
  [/托福|TOEFL/i, '托福'],
  [/计算机等级|计算机[一二三四]级/, '计算机等级考试'],
  [/教师资格证/, '教师资格证'],
  [/注册会计师|CPA/i, '注册会计师'],
  [/法律职业资格|法考/, '法律职业资格'],
]

/** 获奖/荣誉：正则 -> 规范化标签 */
const AWARD_PATTERNS: [RegExp, string][] = [
  [/国家奖学金|国家励志奖学金/, '国家奖学金'],
  [/奖学金/, '奖学金'],
  [/ACM|ICPC/i, 'ACM/ICPC'],
  [/数学建模|MathorCup|美赛/i, '数学建模竞赛'],
  [/蓝桥杯/, '蓝桥杯'],
  [/电子设计大赛|电赛/, '电子设计大赛'],
  [/挑战杯/, '挑战杯'],
  [/互联网\+|创新创业大赛|创青春/, '创新创业大赛'],
  [/大创|大学生创新创业/, '大创项目'],
  [/机器人大赛|RoboMaster|RoboCup/i, '机器人大赛'],
  [/计算机设计大赛|中国大学生计算机设计/, '计算机设计大赛'],
  [/服务外包创新创业|软件测试大赛|程序设计大赛|算法竞赛|Kaggle|天池/i, '算法/程序竞赛'],
  [/优秀毕业生/, '优秀毕业生'],
  [/三好学生|优秀学生|优秀干部|先进个人|荣誉称号/, '荣誉称号'],
]

/** 项目含金量信号：正则 -> 规范化信号词 */
const PROJECT_SIGNALS: [RegExp, string][] = [
  [/上线|发布|落地|投产|商用|交付/, '已上线/交付'],
  [/高并发|亿级|千万级|百万级|海量|大规模|分布式/, '规模化/高并发'],
  [/自研|从0到1|从零到一|独立开发|独立完成|独立设计|独立实现/, '自研/独立完成'],
  [/主导|牵头|带领|负责核心/, '主导/核心负责'],
  [/大模型|深度学习|机器学习|推荐系统|搜索|风控|算法/, '算法/AI'],
  [/性能优化|提速|降本|压缩|加速|优化了|提升了|降低了/, '优化提效'],
  [/获奖|一等奖|二等奖|三等奖/, '获奖'],
  [/开源|GitHub|star/i, '开源贡献'],
  [/千万|百万|亿/, '业务规模'],
  [/日活|DAU|MAU|GMV|转化率|用户量/, '业务指标'],
]

/** 项目名词，用于识别项目描述句 */
const PROJECT_NOUNS = /系统|平台|项目|App|小程序|网站|引擎|模块|工具|中台|服务|数据库|商城|门户|后台|框架/

/**
 * 叙述型能力短语 → 标准技能名的映射。
 * 收录标准同别名表：模式本身必须已断言该能力。正则不能加 g 标志（test 会记忆 lastIndex）。
 */
const CAPABILITY_PATTERNS: [RegExp, string][] = [
  [/跨(部门|团队|职能)/, '跨部门协作'],
  [/(统筹|牵头|带领|组织|协调).{0,10}(团队|小组|成员|部门|各方|资源)/, '跨部门协作'],
  [/(团队|小组)(协作|合作|配合|沟通)/, '跨部门协作'],
  [/(任务分工|资源协调|进度(管理|跟进|把控|推进)|项目(管理|推进|统筹|落地|交付|排期))/, '项目管理'],
  [/(统筹|牵头|主导|策划|组织).{0,12}(项目|竞赛|活动|培训|会议)/, '项目管理'],
  [/(梳理|拆解|分析|调研|挖掘|澄清|反推|明确).{0,8}需求/, '需求分析'],
  [/需求(梳理|拆解|分析|调研|评审|管理|文档|优先级)/, '需求分析'],
  [/(功能|产品|业务)(规划|主线|范围|清单|链路|流程|取舍)/, '需求分析'],
  [/(产品|业务|运营)(规划|方向|定位|路线图|roadmap|模式)/i, '产品规划'],
  [/(产品|方案|功能)(设计|评审|取舍)/, '产品规划'],
  [/(用户|客户|受众|使用者)(调研|访谈|研究|反馈|画像|需求|体验|习惯|场景)/, '用户研究'],
  [/竞品(分析|调研|对比|研究)/, '竞品分析'],
  [/(原型|交互稿|线框)/, '原型设计'],
  [/(技术|方案)(选型|可行性|论证|评估)/, '技术可行性评估'],
  [/(可行性|技术方案)(分析|评估|论证)/, '技术可行性评估'],
  [/(撰写|编写|输出|整理|产出|沉淀).{0,8}(文档|说明书|方案|报告|规范|手册|清单|白皮书)/, '文档编写'],
  [/(数据|指标).{0,4}(分析|洞察|复盘|统计|监控|看板)/, '数据分析'],
  [/(数据|信息)(采集|抓取|爬取|获取)/, '数据采集'],
  [/(爬取|爬虫|抓取).{0,8}(数据|岗位|网页|信息|内容)/, '数据采集'],
  [/(模型|算法|推理).{0,6}(部署|上线|投产)/, '模型部署'],
  [/(容器化|docker|k8s|kubernetes).{0,6}(部署|编排|管理|迁移)/i, 'Docker'],
  [/(工作流|流程|流水线)(编排|设计|搭建|自动化)/, '工作流编排'],
  [/(自动化|批量).{0,4}(流水线|流程|脚本|创作|生产|生成)/, '工作流编排'],
  [/(单元测试|集成测试|回归测试|测试用例|自动化测试|接口测试)/, '测试'],
  // 性能优化≠性能测试，分开匹配
  [/(性能|压力|负载)(测试|压测)/, '性能测试'],
  [/(性能|负载|吞吐|耗时).{0,4}(优化|提升|调优|降低)/, '性能优化'],
  [/(日志|监控|告警).{0,4}(分析|体系|平台|接入|搭建)/, '监控告警'],
  [/(标注|打标)(流程|规范|工作流|质检|质量|一致性|体系)/, '数据标注'],
  [/(标注|数据)(质量|一致性|准确率).{0,4}(评估|校验|审核|监控)/, '标注质量评估'],
]

/** 竞赛类奖项，映射为技能点「计算机竞赛获奖」 */
const COMPETITION_AWARDS = new Set([
  'ACM/ICPC', '数学建模竞赛', '蓝桥杯', '电子设计大赛', '挑战杯',
  '创新创业大赛', '大创项目', '机器人大赛', '计算机设计大赛', '算法/程序竞赛',
])

function splitSegments(text: string): string[] {
  return text.split(/[\n。；;!！?？]+/).map(s => s.trim()).filter(s => s.length >= 4)
}

/** 技能出现在动作动词句子里 → 达标；仅罗列 → listed */
function evidenceFor(terms: string[], text: string): 'mastered' | 'listed' {
  const lower = text.toLowerCase()
  const lterms = terms.map(t => t.toLowerCase())
  for (const seg of splitSegments(lower)) {
    if (lterms.some(t => seg.includes(t)) && ACTION_VERBS.test(seg)) return 'mastered'
  }
  return 'listed'
}

function collectPatterns(text: string, patterns: [RegExp, string][]): string[] {
  const found: string[] = []
  for (const [re, label] of patterns) {
    if (re.test(text) && !found.includes(label)) found.push(label)
  }
  return found
}

/** 提取项目：识别含动作动词 + 项目名词的句子，抽取项目名与含金量信号 */
function extractProjects(text: string): ProjectInfo[] {
  const segments = splitSegments(text)
  const projects: ProjectInfo[] = []
  const seen = new Set<string>()
  for (const seg of segments) {
    if (projects.length >= 8) break
    if (!ACTION_VERBS.test(seg) || !PROJECT_NOUNS.test(seg)) continue
    const nameMatch = seg.match(/([\u4e00-\u9fffA-Za-z0-9+\-#]{2,16}?)(系统|平台|项目|App|小程序|网站|引擎|中台|工具|服务)/)
    const name = nameMatch ? nameMatch[1] + nameMatch[2] : '项目'
    if (seen.has(name)) continue
    const signals = PROJECT_SIGNALS.filter(([re]) => re.test(seg)).map(([, label]) => label)
    if (signals.length === 0 && projects.length >= 3) continue // 无信号的项目仅在数量少时保留
    seen.add(name)
    projects.push({ name, signals })
  }
  return projects
}

export function parseResumeText(text: string): ResumeParseResult {
  const lower = text.toLowerCase()
  const dict = getDict()
  const skills: ParsedSkill[] = []
  const byName = new Map<string, ParsedSkill>()
  for (const entry of dict) {
    const terms = entry.matchCanonical ? [entry.name, ...entry.aliases] : entry.aliases
    const { hits, matched } = countUniqueHits(terms, lower)
    if (hits > 0) {
      const s: ParsedSkill = {
        name: entry.name,
        confidence: confidenceFor(hits),
        hits,
        evidence: evidenceFor(terms, text),
        terms: emitTerms(entry.name, matched),
      }
      byName.set(entry.name, s)
      skills.push(s)
    }
  }
  for (const [re, label] of CAPABILITY_PATTERNS) {
    if (!re.test(text)) continue
    const cur = byName.get(label)
    if (cur) {
      if (!cur.terms.includes(label)) cur.terms.push(label)
      continue
    }
    const s: ParsedSkill = { name: label, confidence: 0.72, hits: 1, evidence: 'mastered', terms: [label] }
    byName.set(label, s)
    skills.push(s)
  }
  const awards = collectPatterns(text, AWARD_PATTERNS)
  // 竞赛奖项映射为技能点，奖学金/荣誉称号不算
  if (awards.some(a => COMPETITION_AWARDS.has(a)) && !byName.has('计算机竞赛获奖')) {
    const s: ParsedSkill = { name: '计算机竞赛获奖', confidence: 0.72, hits: 1, evidence: 'mastered', terms: ['计算机竞赛获奖'] }
    byName.set(s.name, s)
    skills.push(s)
  }
  skills.sort((a, b) => b.confidence - a.confidence || b.hits - a.hits)
  return {
    skills,
    years: extractYears(text),
    education: extractEducation(text),
    certificates: collectPatterns(text, CERT_PATTERNS),
    awards,
    projects: extractProjects(text),
    rawText: text,
  }
}

/** 解析 PDF 文本（懒加载 pdfjs-dist，worker 用 vite ?worker 创建） */
export async function extractPdfText(buf: ArrayBuffer): Promise<{ text: string; hasImages: boolean }> {
  // 必须用 legacy 构建：新版 default 构建在旧浏览器会抛 Iterator is not defined
  const pdfjs: any = await import('pdfjs-dist/legacy/build/pdf.mjs')
  const workerMod: any = await import('pdfjs-dist/legacy/build/pdf.worker.min.mjs?worker')
  pdfjs.GlobalWorkerOptions.workerPort = new workerMod.default()
  // pdfjs v6 的销毁必须走 loadingTask
  const loadingTask = pdfjs.getDocument({ data: buf, isEvalSupported: false })
  const doc = await loadingTask.promise
  let text = ''
  let hasImages = false
  try {
    for (let i = 1; i <= doc.numPages; i++) {
      const page = await doc.getPage(i)
      const tc = await page.getTextContent()
      text += tc.items.map((it: any) => ('str' in it ? it.str : '')).join(' ') + '\n'
      if (!hasImages) {
        // 检测扫描版 PDF（无文字层）
        try {
          const opList = await page.getOperatorList()
          hasImages = opList.fnArray.includes(pdfjs.OPS.paintImageXObject)
        } catch {
          // 忽略单页失败
        }
      }
      page.cleanup()
    }
  } finally {
    await loadingTask.destroy()
  }
  return { text, hasImages }
}

/** 解析 DOCX 文本（懒加载 mammoth 浏览器版） */
export async function extractDocxText(buf: ArrayBuffer): Promise<string> {
  const mammoth: any = await import('mammoth/mammoth.browser.min.js')
  const res = await mammoth.extractRawText({ arrayBuffer: buf })
  return res?.value || ''
}

/** 根据文件类型解析简历文件 → 结构化结果 */
export async function parseResumeFile(file: File): Promise<ResumeParseResult> {
  const name = (file.name || '').toLowerCase()
  const buf = await file.arrayBuffer()
  let text = ''
  if (name.endsWith('.pdf')) {
    const pdf = await extractPdfText(buf)
    text = pdf.text
    if (!text.trim()) {
      if (pdf.hasImages) {
        throw new Error('检测到该 PDF 为图片型/扫描版简历（无文字层），无法自动解析。请粘贴简历文本，或重新导出为带文字层的 PDF 后再试')
      }
      throw new Error('未能从文件中解析出文本内容，请确认文件未加密或粘贴文本重试')
    }
  } else if (name.endsWith('.docx')) {
    text = await extractDocxText(buf)
  } else if (name.endsWith('.doc')) {
    throw new Error('暂不支持旧版 .doc 二进制格式，请另存为 .docx，或直接粘贴简历文本')
  } else if (/\.(txt|md|text)$/.test(name)) {
    text = new TextDecoder().decode(buf)
  } else {
    throw new Error('不支持的文件格式，请上传 PDF / Word / TXT，或粘贴简历文本')
  }
  if (!text.trim()) throw new Error('未能从文件中解析出文本内容，请确认文件未加密或粘贴文本重试')
  return parseResumeText(text)
}
