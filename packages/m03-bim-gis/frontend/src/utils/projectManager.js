/**
 * 项目管理器
 * 负责项目的保存、加载、删除等持久化操作
 * 使用localStorage存储项目数据
 */

import { logger } from '@/utils/logger'

const PROJECTS_STORAGE_KEY = 'm03_projects'
const AUTO_SAVE_KEY = 'm03_autosave'
const MAX_PROJECTS = 50 // 最多保存50个项目

/**
 * 项目数据结构
 * {
 *   id: string,
 *   name: string,
 *   location: string,
 *   params: Object,
 *   sites: Array,
 *   createdAt: number,
 *   updatedAt: number
 * }
 */

export class ProjectManager {
  /**
   * 加载所有项目列表
   * @returns {Array} 项目数组
   */
  static loadProjects() {
    try {
      const data = localStorage.getItem(PROJECTS_STORAGE_KEY)
      return data ? JSON.parse(data) : []
    } catch (error) {
      logger.error('ProjectManager', '加载项目列表失败', error)
      return []
    }
  }

  /**
   * 保存项目
   * @param {Object} projectData - 项目数据
   * @returns {string} 项目ID
   */
  static saveProject(projectData) {
    try {
      const projects = this.loadProjects()
      
      // 添加时间戳
      projectData.updatedAt = Date.now()
      
      // 如果是更新现有项目
      const index = projects.findIndex(p => p.id === projectData.id)
      if (index >= 0) {
        projects[index] = projectData
      } else {
        // 新项目
        projectData.id = this.generateId()
        projectData.createdAt = Date.now()
        projects.unshift(projectData)
      }
      
      // 限制项目数量
      if (projects.length > MAX_PROJECTS) {
        projects.pop()
      }
      
      localStorage.setItem(PROJECTS_STORAGE_KEY, JSON.stringify(projects))
      return projectData.id
    } catch (error) {
      logger.error('ProjectManager', '保存项目失败', error)
      throw new Error('保存项目失败，存储空间可能已满')
    }
  }

  /**
   * 自动保存 — 保存到独立 key，不污染正常项目列表
   * @param {Object} state - { sites, generateParams, designInfo, currentLocation }
   */
  static saveProjectForAutoSave(state) {
    try {
      localStorage.setItem(AUTO_SAVE_KEY, JSON.stringify({
        ...state,
        savedAt: Date.now()
      }))
    } catch (error) {
      logger.error('ProjectManager', '自动保存失败', error)
    }
  }

  /**
   * 加载自动保存的草稿
   * @returns {Object|null}
   */
  static loadAutoSave() {
    try {
      const data = localStorage.getItem(AUTO_SAVE_KEY)
      return data ? JSON.parse(data) : null
    } catch {
      return null
    }
  }

  /**
   * 清除自动保存草稿
   */
  static clearAutoSave() {
    localStorage.removeItem(AUTO_SAVE_KEY)
  }

  /**
   * 加载单个项目
   * @param {string} projectId - 项目ID
   * @returns {Object|null} 项目数据
   */
  static loadProject(projectId) {
    try {
      const projects = this.loadProjects()
      const project = projects.find(p => p.id === projectId)
      return project || null
    } catch (error) {
      logger.error('ProjectManager', '加载项目失败', error)
      return null
    }
  }

  /**
   * 删除项目
   * @param {string} projectId - 项目ID
   * @returns {boolean} 是否成功
   */
  static deleteProject(projectId) {
    try {
      let projects = this.loadProjects()
      const initialLength = projects.length
      projects = projects.filter(p => p.id !== projectId)
      
      if (projects.length < initialLength) {
        localStorage.setItem(PROJECTS_STORAGE_KEY, JSON.stringify(projects))
        return true
      }
      return false
    } catch (error) {
      logger.error('ProjectManager', '删除项目失败', error)
      return false
    }
  }

  /**
   * 更新项目
   * @param {string} projectId - 项目ID
   * @param {Object} updates - 更新内容
   * @returns {boolean} 是否成功
   */
  static updateProject(projectId, updates) {
    try {
      const projects = this.loadProjects()
      const index = projects.findIndex(p => p.id === projectId)
      
      if (index >= 0) {
        projects[index] = {
          ...projects[index],
          ...updates,
          updatedAt: Date.now()
        }
        localStorage.setItem(PROJECTS_STORAGE_KEY, JSON.stringify(projects))
        return true
      }
      return false
    } catch (error) {
      logger.error('ProjectManager', '更新项目失败', error)
      return false
    }
  }

  /**
   * 生成唯一ID
   * @returns {string}
   */
  static generateId() {
    return `proj_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * 格式化时间
   * @param {number} timestamp
   * @returns {string}
   */
  static formatTime(timestamp) {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  /**
   * 获取项目统计信息
   * @returns {Object}
   */
  static getStats() {
    const projects = this.loadProjects()
    return {
      total: projects.length,
      storageUsed: new Blob([JSON.stringify(projects)]).size,
      lastUpdated: projects.length > 0 ? projects[0].updatedAt : null
    }
  }

  /**
   * 清空所有项目
   * @returns {boolean}
   */
  static clearAll() {
    try {
      localStorage.removeItem(PROJECTS_STORAGE_KEY)
      return true
    } catch (error) {
      logger.error('ProjectManager', '清空项目失败', error)
      return false
    }
  }

  /**
   * 导出项目为JSON文件
   * @param {string} projectId
   * @returns {string|null} JSON字符串
   */
  static exportProject(projectId) {
    const project = this.loadProject(projectId)
    if (project) {
      return JSON.stringify(project, null, 2)
    }
    return null
  }

  /**
   * 从JSON字符串导入项目
   * @param {string} jsonData
   * @returns {string|null} 项目ID
   */
  static importProject(jsonData) {
    try {
      const project = JSON.parse(jsonData)
      if (project.sites && project.params) {
        return this.saveProject(project)
      }
      return null
    } catch (error) {
      logger.error('ProjectManager', '导入项目失败', error)
      return null
    }
  }
}

/**
 * 自动保存管理器
 */
export class AutoSaveManager {
  constructor(projectManager, delay = 30000) {
    this.manager = projectManager
    this.delay = delay
    this.timer = null
    this.isEnabled = false
    this._getState = null  // 获取当前保存状态的回调
  }

  /**
   * 设置状态获取回调
   * @param {Function} getStateFn - 返回 { sites, generateParams, designInfo, currentLocation } 的回调
   */
  setStateProvider(getStateFn) {
    this._getState = getStateFn
  }

  /**
   * 启动自动保存
   */
  start() {
    this.isEnabled = true
    this.scheduleSave()
  }

  /**
   * 停止自动保存
   */
  stop() {
    this.isEnabled = false
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
  }

  /**
   * 调度保存
   */
  scheduleSave() {
    if (this.timer) {
      clearTimeout(this.timer)
    }
    this.timer = setTimeout(() => {
      this.save()
    }, this.delay)
  }

  /**
   * 执行保存 — 需先通过 setStateProvider 注册状态获取器
   */
  save() {
    if (!this.isEnabled) return
    if (!this._getState) {
      logger.warn('AutoSaveManager', '未注册状态获取器，跳过自动保存')
      return
    }
    const state = this._getState()
    if (!state || state.sites.length === 0) return
    logger.info('AutoSaveManager', '执行自动保存')
    this.manager.saveProjectForAutoSave(state)
  }
}
