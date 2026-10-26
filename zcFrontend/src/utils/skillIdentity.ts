import type { CapabilityChange } from '@/models'

const aliases: Record<string, string> = {
  'c语言': 'c', 'c programming': 'c',
  'golang': 'go', 'go语言': 'go',
  'js': 'javascript', 'javascript语言': 'javascript',
  'ts': 'typescript', 'vue.js': 'vue', 'vuejs': 'vue',
  'react.js': 'react', 'reactjs': 'react',
  'k8s': 'kubernetes', 'mcp协议': 'mcp',
}

export function skillIdentity(name: string): string {
  const normalized = name.normalize('NFKC').trim().toLowerCase().replace(/\s+/g, ' ')
  return aliases[normalized] ?? normalized
}

export function sameSkill(a: string, b: string): boolean {
  return skillIdentity(a) === skillIdentity(b)
}

/** 历史新增不代表当前周期仍为新增。 */
export function latestJobChanges(changes: CapabilityChange[], jobId: string): CapabilityChange[] {
  const own = changes.filter(c => c.jobId === jobId)
  const latest = own.reduce((period, c) => c.period > period ? c.period : period, '')
  return own.filter(c => c.period === latest)
}

export function skillTrend(changes: CapabilityChange[], jobId: string, skill: string): 'new' | 'up' | 'down' | 'stable' {
  const latest = latestJobChanges(changes, jobId)
  const contains = (names: string[] | undefined) => names?.some(name => sameSkill(name, skill)) === true
  const up = latest.some(c => contains(c.importanceUp))
  const down = latest.some(c => contains(c.importanceDown) || contains(c.removedSkills))
  if (latest.some(c => contains(c.addedSkills)) && !down) return 'new'
  return up && !down ? 'up' : down && !up ? 'down' : 'stable'
}
