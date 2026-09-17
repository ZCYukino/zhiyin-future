import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'
import App from './App.vue'
import router from './router'
import './style.css'

NProgress.configure({ showSpinner: false, speed: 300, trickleSpeed: 100 })

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.mount('#app')
