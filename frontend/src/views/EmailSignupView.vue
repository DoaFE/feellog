<template>
  <div class="flex flex-col items-center justify-center h-screen bg-gray-100">
    <div class="w-full max-w-sm p-8 space-y-6 bg-white rounded-xl shadow-md">
      <h2 class="text-2xl font-bold text-center">회원가입</h2>

      <form @submit.prevent="handleSignup">
        <div>
          <label for="email" class="block text-sm font-medium text-gray-700">이메일</label>
          <input type="email" id="email" v-model="email" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500">
        </div>
        <div>
          <label for="nickname" class="block text-sm font-medium text-gray-700">닉네임</label>
          <input type="text" id="nickname" v-model="nickname" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500">
        </div>
        <div>
          <label for="password" class="block text-sm font-medium text-gray-700">비밀번호</label>
          <input type="password" id="password" v-model="password" required class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500">
        </div>

        <div class="space-y-2">
          <div class="flex items-center">
            <input id="agree_privacy" type="checkbox" v-model="agreePrivacy" required class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded">
            <label for="agree_privacy" class="ml-2 block text-sm text-gray-900">개인정보 수집 및 이용 동의 (필수)</label>
          </div>
          <div class="flex items-center">
            <input id="agree_alarm" type="checkbox" v-model="agreeAlarm" class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded">
            <label for="agree_alarm" class="ml-2 block text-sm text-gray-900">알림 수신 동의 (선택)</label>
          </div>
        </div>

        <button type="submit" class="w-full py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
          회원가입
        </button>
      </form>

      <div v-if="message" :class="messageClass" class="mt-4 text-sm text-center">
        {{ message }}
      </div>

      <p class="text-center text-sm mt-4">
        이미 회원이신가요? <router-link to="/login/email" class="font-medium text-indigo-600 hover:text-indigo-500">로그인</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';

const email = ref('');
const nickname = ref('');
const password = ref('');
const agreePrivacy = ref(false);
const agreeAlarm = ref(false);
const message = ref('');
const messageClass = ref('');
const router = useRouter();

const handleSignup = async () => {
  try {
    const response = await axios.post('http://localhost:5000/api/signup_email', {
      email: email.value,
      nickname: nickname.value,
      password: password.value,
      agree_privacy: agreePrivacy.value,
      agree_alarm: agreeAlarm.value,
    });
    message.value = response.data.message;
    messageClass.value = 'text-green-500';
    setTimeout(() => {
      router.push('/login/email');
    }, 2000);
  } catch (error) {
    message.value = error.response?.data?.message || '회원가입 중 오류가 발생했습니다.';
    messageClass.value = 'text-red-500';
  }
};
</script>
