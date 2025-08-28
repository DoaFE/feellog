<template>
  <div class="flex flex-col items-center justify-center h-screen bg-gray-100">
    <div class="w-full max-w-sm p-8 space-y-6 bg-white rounded-xl shadow-md">
      <h2 class="text-2xl font-bold text-center">로그인</h2>

      <form @submit.prevent="handleLogin">
        <div>
          <label for="email" class="block text-sm font-medium text-gray-700">이메일</label>
          <input type="email" id="email" v-model="email" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500">
        </div>
        <div>
          <label for="password" class="block text-sm font-medium text-gray-700">비밀번호</label>
          <input type="password" id="password" v-model="password" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500">
        </div>

        <button type="submit" class="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
          로그인
        </button>
      </form>

      <div v-if="message" :class="messageClass" class="mt-4 text-sm text-center">
        {{ message }}
      </div>

      <p class="text-center text-sm mt-4">
        계정이 없으신가요? <router-link to="/signup/email" class="font-medium text-indigo-600 hover:text-indigo-500">회원가입</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useMainStore } from '@/stores/main';
import axios from 'axios';

const email = ref('');
const password = ref('');
const message = ref('');
const messageClass = ref('');
const router = useRouter();
const mainStore = useMainStore();

const handleLogin = async () => {
  try {
    const response = await axios.post('http://localhost:5000/api/login_email', {
      email: email.value,
      password: password.value,
    });

    message.value = response.data.message;
    messageClass.value = 'text-green-500';

    // Pinia 스토어 업데이트
    await mainStore.checkLoginStatus();

    setTimeout(() => {
      router.push('/home');
    }, 1000);
  } catch (error) {
    message.value = error.response?.data?.message || '로그인 중 오류가 발생했습니다.';
    messageClass.value = 'text-red-500';
  }
};
</script>
