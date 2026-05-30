import { config } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { beforeEach } from 'vitest'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

const vuetify = createVuetify({ components, directives })

beforeEach(() => {
  config.global.plugins = [vuetify, createPinia()]
})
