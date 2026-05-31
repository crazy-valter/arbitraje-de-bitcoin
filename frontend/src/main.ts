import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import 'primeicons/primeicons.css'
import '@/assets/styles/main.css'

// Componentes PrimeVue usados en la aplicación
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import InputSwitch from 'primevue/inputswitch'
import Password from 'primevue/password'
import Message from 'primevue/message'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import ProgressBar from 'primevue/progressbar'
import Menubar from 'primevue/menubar'
import Card from 'primevue/card'
import Chart from 'primevue/chart'
import ProgressSpinner from 'primevue/progressspinner'
import MultiSelect from 'primevue/multiselect'
import ToggleButton from 'primevue/togglebutton'
import ConfirmDialog from 'primevue/confirmdialog'
import ConfirmationService from 'primevue/confirmationservice'
import Tooltip from 'primevue/tooltip'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: Aura,
  },
})
app.use(ConfirmationService)

// Registrar componentes PrimeVue globalmente
app.component('Button', Button)
app.component('InputText', InputText)
app.component('InputNumber', InputNumber)
app.component('InputSwitch', InputSwitch)
app.component('Password', Password)
app.component('Message', Message)
app.component('Dialog', Dialog)
app.component('DataTable', DataTable)
app.component('Column', Column)
app.component('Tag', Tag)
app.component('ProgressBar', ProgressBar)
app.component('Menubar', Menubar)
app.component('Card', Card)
app.component('Chart', Chart)
app.component('ProgressSpinner', ProgressSpinner)
app.component('MultiSelect', MultiSelect)
app.component('ToggleButton', ToggleButton)
app.component('ConfirmDialog', ConfirmDialog)

// Directiva Tooltip
app.directive('tooltip', Tooltip)

app.mount('#app')
