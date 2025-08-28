import { defineStore } from 'pinia';
import axios from 'axios';

axios.defaults.withCredentials = true;

export const useMainStore = defineStore('main', {
  state: () => ({
    isLoggedIn: false,
    user: null,
    chatbotPersona: null,
    recentReports: [],
    loading: {
      videoAnalysis: false,
    },
    error: {
      message: null,
    }
  }),
  getters: {
    isGuest: (state) => !state.isLoggedIn,
  },
  actions: {
    async checkLoginStatus() {
      try {
        const response = await axios.get('http://localhost:5000/api/auth/status');
        this.isLoggedIn = response.data.is_logged_in;
        if (this.isLoggedIn) {
          this.user = response.data.user;
        } else {
          this.user = null;
        }
      } catch (error) {
        console.error('Failed to check login status:', error);
        this.isLoggedIn = false;
        this.user = null;
      }
    },
    async login(email, password) {
      this.error.message = null;
      try {
        const response = await axios.post('http://localhost:5000/api/login', { email, password });
        this.isLoggedIn = true;
        this.user = response.data.user; // 백엔드에서 user 정보 반환 필요
        return true;
      } catch (error) {
        this.error.message = error.response?.data?.message || '로그인에 실패했습니다.';
        this.isLoggedIn = false;
        this.user = null;
        return false;
      }
    },
    async fetchRecentReports() {
      try {
        const response = await axios.get('http://localhost:5000/api/dashboard');
        this.recentReports = response.data.reports;
      } catch (error) {
        console.error('Failed to fetch recent reports:', error);
        this.recentReports = [];
      }
    },
    async startVideoAnalysis() {
      this.loading.videoAnalysis = true;
      // ... API 호출 로직 ...
    },
    endVideoAnalysis() {
      this.loading.videoAnalysis = false;
    },
    async setChatbotPersona(personaId) {
    try {
      const response = await axios.post('http://localhost:5000/api/settings/persona', {
        chatbot_id: personaId,
      });
      console.log('Chatbot persona set successfully:', response.data.message);
      this.chatbotPersona = personaId;
      return true;
    } catch (error) {
      console.error('Failed to set chatbot persona:', error.response?.data?.message || error.message);
      this.error.message = '챗봇 페르소나 변경에 실패했습니다.';
      return false;
    }
  }
});
