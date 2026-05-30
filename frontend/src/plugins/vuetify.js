import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import { md3 } from 'vuetify/blueprints'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

const jadeTheme = {
  dark: false,
  colors: {
    primary:    '#00897B',
    secondary:  '#00695C',
    accent:     '#26A69A',
    success:    '#4CAF50',
    warning:    '#FF9800',
    error:      '#EF5350',
    info:       '#26C6DA',
    background: '#F1F8F7',
    surface:    '#FFFFFF',
    'on-primary': '#FFFFFF',
  },
}

export default createVuetify({
  blueprint: md3,
  components,
  directives,
  theme: {
    defaultTheme: 'jadeTheme',
    themes: { jadeTheme },
  },
  defaults: {
    VCard:      { rounded: 'lg', elevation: 1 },
    VBtn:       { rounded: 'lg' },
    VTextField: { variant: 'outlined', density: 'comfortable' },
    VSelect:    { variant: 'outlined', density: 'comfortable' },
  },
})
