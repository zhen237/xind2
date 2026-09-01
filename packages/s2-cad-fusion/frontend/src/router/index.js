import Upload from '../views/Upload.vue'
import Transform from '../views/Transform.vue'
import Fusion from '../views/Fusion.vue'

export default [
  { path: '/', redirect: '/upload' },
  { path: '/upload', name: 'upload', component: Upload, meta: { title: '图纸上传' } },
  { path: '/transform', name: 'transform', component: Transform, meta: { title: '转换结果' } },
  { path: '/fusion', name: 'fusion', component: Fusion, meta: { title: '融合结果' } },
]
