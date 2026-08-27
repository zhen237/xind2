/**
 * 无后端模拟适配器（仅在 VITE_USE_MOCK=true 时启用）
 * ------------------------------------------------------------------
 * 拦截 M03 设计域相关 GET 请求，返回 src/mock/fixtures.js 中的虚拟数据，
 * 包装成与真实后端一致的响应结构 { code, msg, data }，使拦截器与页面逻辑
 * 无需任何改动即可在 GitHub Pages 静态部署下跑通。
 */
import {
  MOCK_PROJECTS,
  MOCK_DESIGNS,
  MOCK_SITES,
  MOCK_TEMPLATES,
  MOCK_GEOJSON
} from './fixtures.js'

// 统一响应包装：与后端 Result<T> 结构保持一致
function ok(data) {
  return { code: 200, msg: 'ok', data }
}

// 路由表：url 模式 → 数据工厂
const ROUTES = [
  { test: (u) => u === '/m03/project', make: () => ok(MOCK_PROJECTS) },
  { test: (u) => u === '/m03/design/templates', make: () => ok(MOCK_TEMPLATES) },
  { test: (u) => /\/m03\/design\/\d+\/sites$/.test(u), make: () => ok(MOCK_SITES) },
  { test: (u) => /\/m03\/design\/\d+\/geojson$/.test(u), make: () => ok(MOCK_GEOJSON) },
  {
    test: (u) => /\/m03\/design\/\d+$/.test(u),
    make: (u) => {
      const id = parseInt(u.split('/').pop(), 10)
      return ok(MOCK_DESIGNS[id] || MOCK_DESIGNS[1])
    }
  }
]

/**
 * Axios 自定义适配器签名
 * @param {import('axios').AxiosRequestConfig} config
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export default function mockAdapter(config) {
  const url = config.url || ''
  const matched = ROUTES.find((r) => r.test(url))
  const payload = matched ? matched.make(url) : ok(null)

  // 模拟轻微网络延迟，贴近真实交互体验
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        data: payload,
        status: 200,
        statusText: 'OK',
        headers: { 'content-type': 'application/json' },
        config,
        request: {}
      })
    }, 120)
  })
}
