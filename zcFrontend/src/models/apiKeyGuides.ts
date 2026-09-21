/** 各 provider 的官方获取指引 */
export interface ApiKeyGuide {
  provider: 'deepseek' | 'dashscope'
  title: string
  officialUrl: string
  officialLabel: string
  steps: string[]
  notes: string[]
}

export const DEEPSEEK_GUIDE: ApiKeyGuide = {
  provider: 'deepseek',
  title: 'DeepSeek 开放平台',
  officialUrl: 'https://platform.deepseek.com',
  officialLabel: '前往 DeepSeek 开放平台',
  steps: [
    '打开官网，使用手机号 / 微信扫码登录（未注册的手机号会自动完成注册）。',
    '点击左侧菜单「充值」，确认账户有可用余额（API 为预付费、按 Token 计费）。',
    '点击左侧菜单「API keys」，再点击「创建 API key」，填写备注名称后确认。',
    '生成的密钥以 sk- 开头，且仅完整显示一次——请立即复制并保存到安全位置。',
  ],
  notes: [
    '密钥关闭弹窗后无法再次查看完整内容，丢失只能删除重建。',
    '若保存时报「余额不足」，回到官网「充值」页充值后重试。',
  ],
}

export const DASHSCOPE_GUIDE: ApiKeyGuide = {
  provider: 'dashscope',
  title: '阿里云百炼',
  officialUrl: 'https://bailian.console.aliyun.com',
  officialLabel: '前往阿里云百炼控制台',
  steps: [
    '打开控制台，使用阿里云账号登录（需完成实名认证）。',
    '首次使用先开通百炼平台，并按提示「确认开通，并领取免费额度」。',
    '开通模型服务：在「创建 API-Key」提示处点击「去开通模型服务」并确认（不开通无法创建 Key）。',
    '进入右上角设置 →「API-Key」，选择业务空间后点击「创建 API-Key」，填写名称并确定。',
    '生成的密钥以 sk- 开头，且仅完整显示一次——请立即复制并保存。',
  ],
  notes: [
    '新用户通常附赠免费 Token 额度，可用于验证配置是否生效。',
    '若保存时报「未开通模型服务」，回到控制台先开通模型服务再重试。',
  ],
}
