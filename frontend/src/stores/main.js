import { defineStore } from 'pinia';
import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://localhost:5000/api',
  withCredentials: true,
});

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
    },
    processingRecordId: null,
    showToast: false,
    toastMessage: '',
    intervalId: null,
  }),

  getters: {
    isGuest: (state) => !state.isLoggedIn,
  },
  actions: {
    async checkLoginStatus() {
      try {
        const response = await apiClient.get('/auth/status');
        this.isLoggedIn = response.data.is_logged_in;
        if (this.isLoggedIn) {
          this.user = response.data.user;
          this.startPolling(); // [연동] 로그인 상태이면 폴링 시작
        } else {
          this.user = null;
          this.stopPolling(); // [연동] 비로그인 상태이면 폴링 중지
        }
      } catch (error) {
        console.error('Failed to check login status:', error);
        this.isLoggedIn = false;
        this.user = null;
        this.stopPolling();
      }
    },
    async login(email, password) {
      this.error.message = null;
      try {
        const response = await apiClient.post('/login_email', { email, password });
        this.isLoggedIn = true;
        this.user = response.data.user; // 백엔드에서 user 정보 반환 필요
        this.startPolling(); // [연동] 로그인 성공 시 폴링 시작
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
        const response = await apiClient.get('/dashboard');
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
    async logout() {
      try {
        await apiClient.post('/logout');
        this.isLoggedIn = false;
        this.user = null;
        this.stopPolling();
        alert('로그아웃 되었습니다.');
        return true;
      } catch (error) {
        console.error('Logout failed:', error);
        alert('로그아웃 중 오류가 발생했습니다.');
        return false;
      }
    },
    async checkStatus() {
      if (!this.isLoggedIn) return;
      try {
        const { data } = await apiClient.get('/records/latest-status');

        if (this.processingRecordId) {
          if (this.processingRecordId === data.record_id && data.status === 'completed') {
            console.log(`[Main Store] Record ${data.record_id} completed!`);
            this.toastMessage = '영상 분석이 완료되었습니다!';
            this.showToast = true;

            setTimeout(() => {
              this.showToast = false;
            }, 3000);

            this.processingRecordId = null;
          }
        } else {
          if (data.record_id && data.status === 'processing') {
            console.log(`[Main Store] Start tracking record ${data.record_id}`);
            this.processingRecordId = data.record_id;
          }
        }
      } catch (error) {
        if (error.response?.status !== 401) {
          console.error('분석 상태 확인 중 오류 발생:', error);
        }
      }
    },

    startPolling() {
      if (this.intervalId) return; // 중복 실행 방지
      console.log('[Main Store] Starting status polling.');
      this.intervalId = setInterval(this.checkStatus, 5000);
    },

    stopPolling() {
      if (this.intervalId) {
        clearInterval(this.intervalId);
        this.intervalId = null;
        console.log('[Main Store] Stopped status polling.');
      }
    },
    async setChatbotPersona(personaId) {
      try {
        const response = await apiClient.post('/settings/persona', {
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
  }
});
