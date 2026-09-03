<script setup lang="ts">
// Root component: intentionally just the router outlet.
// Chrome (nav, sidebar) lives in layouts/DefaultLayout.vue, not here,
// so the /login route can render without any app chrome around it.
</script>

<template>
  <RouterView />
</template>
