/**
 * 地图操作工具集
 * 封装常用的Cesium地图操作逻辑
 */

import * as Cesium from 'cesium'

/**
 * 清除地图上的所有站点实体
 * @param {Cesium.Viewer} viewer - Cesium查看器
 * @returns {number} 清除的实体数量
 */
export function clearMapEntities(viewer) {
  if (!viewer) return 0
  
  const entitiesToRemove = []
  viewer.entities.values.forEach(entity => {
    if (entity.metadata?.isSite) {
      entitiesToRemove.push(entity)
    }
  })
  
  entitiesToRemove.forEach(entity => viewer.entities.remove(entity))
  return entitiesToRemove.length
}

/**
 * 平滑飞行到指定位置
 * @param {Cesium.Viewer} viewer - Cesium查看器
 * @param {Object} destination - 目标位置 {longitude, latitude, height}
 * @param {number} duration - 飞行时长(毫秒)，默认2000ms
 */
export function flyToLocation(viewer, destination, duration = 2000) {
  if (!viewer || !destination) return
  
  const position = Cesium.Cartesian3.fromDegrees(
    destination.longitude,
    destination.latitude,
    destination.height || 10000
  )
  
  viewer.camera.flyTo({
    destination: position,
    orientation: {
      heading: Cesium.Math.toRadians(0),
      pitch: Cesium.Math.toRadians(-45),
      roll: 0
    },
    duration: duration / 1000
  })
}

/**
 * 缩放到站点范围
 * @param {Cesium.Viewer} viewer - Cesium查看器
 * @param {Array} sites - 站点数据数组
 */
export function zoomToSitesBounds(viewer, sites) {
  if (!viewer || !sites?.length) return
  
  const boundingSphere = Cesium.BoundingSphere.fromPoints(
    sites.map(s => Cesium.Cartesian3.fromDegrees(s.longitude, s.latitude))
  )
  
  viewer.camera.flyToBoundingSphere(boundingSphere, {
    offset: new Cesium.HeadingPitchRange(
      0,
      -Cesium.Math.PI_OVER_TWO / 3,
      5000
    )
  })
}

/**
 * 添加站点标记到地图
 * @param {Cesium.Viewer} viewer - Cesium查看器
 * @param {Array} sites - 站点数据
 * @param {Object} options - 可选配置
 * @returns {number} 添加的站点数量
 */
export function addSitesToMap(viewer, sites, options = {}) {
  if (!viewer || !sites?.length) return 0
  
  let count = 0
  
  sites.forEach(site => {
    const position = Cesium.Cartesian3.fromDegrees(site.longitude, site.latitude)
    
    // 站点标记
    viewer.entities.add({
      position: position,
      point: {
        pixelSize: options.pointSize || 10,
        color: site.isValid ? Cesium.Color.GREEN : Cesium.Color.RED,
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2
      },
      label: {
        text: site.siteId,
        font: '12px sans-serif',
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -15),
        showBackground: true,
        backgroundColor: new Cesium.Color(0.2, 0.2, 0.2, 0.8)
      },
      metadata: { isSite: true, siteId: site.siteId }
    })
    
    count++
  })
  
  return count
}

/**
 * 添加塔桅标记到地图
 * @param {Cesium.Viewer} viewer - Cesium查看器
 * @param {Array} sites - 站点数据
 * @param {Object} options - 可选配置
 * @returns {number} 添加的塔桅数量
 */
export function addTowersToMap(viewer, sites, options = {}) {
  if (!viewer || !sites?.length) return 0
  
  let count = 0
  
  sites.forEach(site => {
    const position = Cesium.Cartesian3.fromDegrees(site.longitude, site.latitude)
    const height = site.towerHeight || 30
    
    // 塔桅圆柱体
    viewer.entities.add({
      position: position,
      cylinder: {
        length: height,
        topRadius: 0.5,
        bottomRadius: 1.0,
        material: Cesium.Color.GRAY.withAlpha(0.7),
        outline: true,
        outlineColor: Cesium.Color.DARKGRAY
      },
      metadata: { isTower: true, siteId: site.siteId }
    })
    
    count++
  })
  
  return count
}

/**
 * 添加覆盖范围到地图
 * @param {Cesium.Viewer} viewer - Cesium查看器
 * @param {Array} sites - 站点数据
 * @param {Object} options - 可选配置
 * @returns {number} 添加的覆盖范围数量
 */
export function addCoverageToMap(viewer, sites, options = {}) {
  if (!viewer || !sites?.length) return 0
  
  let count = 0
  
  sites.forEach(site => {
    const position = Cesium.Cartesian3.fromDegrees(site.longitude, site.latitude)
    const radius = options.coverageRadius || 200
    
    // 覆盖椭圆
    viewer.entities.add({
      position: position,
      ellipse: {
        semiMinorAxis: radius,
        semiMajorAxis: radius,
        material: site.isValid 
          ? Cesium.Color.GREEN.withAlpha(0.2)
          : Cesium.Color.RED.withAlpha(0.2),
        outline: true,
        outlineColor: site.isValid ? Cesium.Color.GREEN : Cesium.Color.RED,
        height: 0
      },
      metadata: { isCoverage: true, siteId: site.siteId }
    })
    
    count++
  })
  
  return count
}

/**
 * 切换图层可见性
 * @param {Cesium.Viewer} viewer - Cesium查看器
 * @param {string} layerType - 图层类型 (site/tower/coverage/label)
 * @param {boolean} visible - 是否可见
 */
export function toggleLayerVisibility(viewer, layerType, visible) {
  if (!viewer) return
  
  viewer.entities.values.forEach(entity => {
    if (!entity.metadata) return
    
    switch (layerType) {
      case 'site':
        if (entity.metadata.isSite) {
          entity.show = visible
        }
        break
      case 'tower':
        if (entity.metadata.isTower) {
          entity.show = visible
        }
        break
      case 'coverage':
        if (entity.metadata.isCoverage) {
          entity.show = visible
        }
        break
      case 'label':
        if (entity.label) {
          entity.label.show = visible
        }
        break
    }
  })
}

/**
 * 获取图层可见性状态
 * @param {Cesium.Viewer} viewer - Cesium查看器
 * @param {string} layerType - 图层类型
 * @returns {boolean} 是否可见
 */
export function getLayerVisibility(viewer, layerType) {
  if (!viewer) return false
  
  const entity = viewer.entities.values.find(e => e.metadata?.[`is${layerType.charAt(0).toUpperCase() + layerType.slice(1)}`])
  return entity?.show ?? false
}
