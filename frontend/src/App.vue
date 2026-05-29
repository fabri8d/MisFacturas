<script setup>
/** App raíz con barra de navegación inferior y router-view. */
import { useRoute } from 'vue-router'
const route = useRoute()
</script>

<template>
  <div class="layout">
    <main class="content">
      <router-view />
    </main>

    <nav class="bottom-nav">
      <router-link to="/" class="nav-item" :class="{ active: route.path === '/' }">
        <span class="icon">🏠</span>
        <span>Inicio</span>
      </router-link>
      <router-link to="/bills" class="nav-item" :class="{ active: route.path.startsWith('/bills') }">
        <span class="icon">📄</span>
        <span>Facturas</span>
      </router-link>
      <router-link to="/history" class="nav-item" :class="{ active: route.path === '/history' }">
        <span class="icon">📊</span>
        <span>Historial</span>
      </router-link>
      <router-link to="/settings" class="nav-item" :class="{ active: route.path === '/settings' }">
        <span class="icon">⚙️</span>
        <span>Ajustes</span>
      </router-link>
    </nav>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.content {
  flex: 1;
  max-width: 680px;
  width: 100%;
  margin: 0 auto;
  padding: 20px 16px 80px;
}

.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 64px;
  background: var(--surface);
  border-top: 1px solid var(--border);
  display: flex;
  z-index: 100;
}

.nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  font-size: 0.65rem;
  color: var(--text-muted);
  transition: color 0.15s;
  padding: 8px 0;
}
.nav-item .icon { font-size: 1.3rem; }
.nav-item.active { color: var(--accent-light); }
.nav-item:hover  { color: var(--text); }
</style>
