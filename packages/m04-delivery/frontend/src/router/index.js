import { createRouter, createWebHistory } from 'vue-router'
import ProjectList from '../views/ProjectList.vue'
import WorkOrderList from '../views/WorkOrderList.vue'
import ConstructionRecord from '../views/ConstructionRecord.vue'
import AcceptanceList from '../views/AcceptanceList.vue'
import DeliveryPackage from '../views/DeliveryPackage.vue'

const routes = [
  { path: '/', redirect: '/project' },
  { path: '/project', component: ProjectList },
  { path: '/work-order', component: WorkOrderList },
  { path: '/construction', component: ConstructionRecord },
  { path: '/acceptance', component: AcceptanceList },
  { path: '/delivery', component: DeliveryPackage }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router