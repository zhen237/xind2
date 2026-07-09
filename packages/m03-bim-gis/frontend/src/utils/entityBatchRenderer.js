/**
 * 实体批量渲染器
 * 使用Primitive替代Entity提升渲染性能
 */

import * as Cesium from 'cesium'

export class EntityBatchRenderer {
  /**
   * @param {Cesium.Viewer} viewer - Cesium查看器
   */
  constructor(viewer) {
    this.viewer = viewer
    this.primitive = null
    this.positions = []
    this.colors = []
    this.labels = []
  }

  /**
   * 批量添加站点标记
   * @param {Array} sites - 站点数据
   */
  addSites(sites) {
    if (!sites?.length) return
    
    this.positions = sites.map(site => 
      Cesium.Cartesian3.fromDegrees(site.longitude, site.latitude)
    )
    
    this.colors = sites.map(site => 
      site.isValid ? Cesium.Color.GREEN : Cesium.Color.RED
    )
    
    this.labels = sites.map(site => site.siteId)
    
    this.render()
  }

  /**
   * 渲染点集合
   */
  render() {
    if (this.primitive) {
      this.viewer.primitives.remove(this.primitive)
    }

    const pointCollection = new Cesium.PointPrimitiveCollection()

    this.positions.forEach((pos, i) => {
      pointCollection.add({
        position: pos,
        pixelSize: 10,
        color: this.colors[i],
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        scaleByDistance: new Cesium.NearFarScalar(1e2, 1.5, 1.5e7, 0.5),
        translucencyByDistance: new Cesium.NearFarScalar(1e2, 1.0, 1.5e7, 0.6),
        eyeOffset: new Cesium.NearFarScalar(1e2, 0.0, 1.5e7, -4.0)
      })
    })

    this.primitive = this.viewer.primitives.add(pointCollection)
  }

  /**
   * 清除所有实体
   */
  clear() {
    if (this.primitive) {
      this.viewer.primitives.remove(this.primitive)
      this.primitive = null
    }
    this.positions = []
    this.colors = []
    this.labels = []
  }

  /**
   * 更新站点数据
   * @param {Array} newSites - 新的站点数据
   */
  update(newSites) {
    this.clear()
    this.addSites(newSites)
  }

  /**
   * 获取渲染统计
   * @returns {Object}
   */
  getStats() {
    return {
      siteCount: this.positions.length,
      hasPrimitive: !!this.primitive
    }
  }
}

/**
 * 创建批量渲染器实例
 * @param {Cesium.Viewer} viewer
 * @returns {EntityBatchRenderer}
 */
export function createBatchRenderer(viewer) {
  return new EntityBatchRenderer(viewer)
}
