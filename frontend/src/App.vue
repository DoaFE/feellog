<!-- app/frontend/src/App.vue -->
<script setup>
import { onMounted } from 'vue';
import { useRoute } from 'vue-router';
import MobileLayout from './components/MobileLayout.vue';
import { useMainStore } from '@/stores/main';

const mainStore = useMainStore();

onMounted(() => {
  mainStore.checkLoginStatus();
});
</script>

<template>
  <MobileLayout :show-navbar="$route.meta.showNavbar">
    <router-view />
  </MobileLayout>
</template>

<style>
/* Global styles or specific app styles if needed */
body {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}
</style>
