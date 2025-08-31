<script setup>
// [추가] 아이콘을 사용하기 위해 import 합니다.
import { CheckCircle2Icon } from 'lucide-vue-next';

defineProps({
  show: {
    type: Boolean,
    required: true,
  },
  message: {
    type: String,
    default: '',
  },
});
</script>

<template>
  <transition name="fade">
    <div
      v-if="show"
      class="fixed bottom-28 left-1/2 -translate-x-1/2 z-50 flex items-center gap-x-2 rounded-lg bg-indigo-600 px-5 py-3 text-base text-white shadow-lg"
    >
      <CheckCircle2Icon class="h-5 w-5" aria-hidden="true" />
      <span>{{ message }}</span>
    </div>
  </transition>
</template>

<style scoped>
/* 애니메이션 효과는 기존과 동일하게 유지합니다. */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease, transform 0.5s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(20px);
}
</style>
