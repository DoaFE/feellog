<script setup>
  import { ref, onMounted, computed, watch, nextTick } from 'vue';
  import { useRouter } from 'vue-router';
  import axios from 'axios';
  import { createLucideIcon, icons } from 'lucide-vue-next';
  import { useMainStore } from '@/stores/main';

  const mainStore = useMainStore();
  const router = useRouter();
  const currentDate = ref(new Date()); // Currently displayed month
  const monthData = ref(null); // Data from backend for the current month
  const isLoading = ref(true);
  const error = ref(null);
  const selectedView = ref('monthly'); // 'monthly' or 'weekly' - for now, only monthly is implemented

  const refreshIcons = () => {
      nextTick(() => {
          createLucideIcon({ icons, attrs: { class: 'lucide-icon' }, nameAttr: 'data-lucide' });
      });
  };

  // --- Helper Functions ---
  const getDaysInMonth = (year, month) => new Date(year, month + 1, 0).getDate();
  const getFirstDayOfMonth = (year, month) => new Date(year, month, 1).getDay(); // 0 for Sunday, 1 for Monday...

  const getSentimentColorClass = (score) => {
      if (score >= 70) return 'bg-green-400';
      if (score >= 55) return 'bg-green-200';
      if (score >= 45) return 'bg-gray-200';
      if (score >= 30) return 'bg-red-200';
      return 'bg-red-400';
  };

  const fetchMonthlyData = async (year, month) => {
      isLoading.value = true;
      error.value = null;
      if (!mainStore.isLoggedIn) {
          error.value = '로그인이 필요한 기능입니다.';
          isLoading.value = false;
          return;
      }

      try {
          const response = await axios.get(`/api/trends/monthly?year=${year}&month=${month}`);
          if (response.data.success) {
              monthData.value = response.data.current_month_data;
              console.log("Fetched monthly data:", monthData.value);
          } else {
              error.value = response.data.message;
          }
      } catch (err) {
          console.error('Error fetching monthly trends:', err);
          error.value = '월간 트렌드 데이터를 불러오는 데 실패했습니다.';
      } finally {
          isLoading.value = false;
          refreshIcons();
      }
  };

  // --- Computed Properties ---
  const formattedMonthYear = computed(() => {
      return currentDate.value.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long' });
  });

  const generateCalendarDays = computed(() => {
      const year = currentDate.value.getFullYear();
      const month = currentDate.value.getMonth(); // 0-indexed

      const numDaysInMonth = getDaysInMonth(year, month);
      const firstDay = getFirstDayOfMonth(year, month); // 0=Sun, 1=Mon...

      const days = [];

      // Previous month's days to fill the first row
      const prevMonthNumDays = getDaysInMonth(year, month - 1);
      for (let i = firstDay - 1; i >= 0; i--) {
          days.push({ day: prevMonthNumDays - i, isCurrentMonth: false });
      }

      // Current month's days
      const emotionsMap = new Map();
      if (monthData.value && monthData.value.days_with_emotions) {
          monthData.value.days_with_emotions.forEach(item => {
              const day = new Date(item.date).getDate();
              emotionsMap.set(day, { sentiment_score: item.sentiment_score, report_id: item.report_id });
          });
      }

      for (let i = 1; i <= numDaysInMonth; i++) {
          const emotionInfo = emotionsMap.get(i);
          days.push({
              day: i,
              isCurrentMonth: true,
              hasEmotion: !!emotionInfo,
              sentimentScore: emotionInfo ? emotionInfo.sentiment_score : null,
              reportId: emotionInfo ? emotionInfo.report_id : null,
              isToday: new Date().toDateString() === new Date(year, month, i).toDateString() // Check if it's today
          });
      }

      // Next month's days to fill the last row
      const remainingCells = 42 - days.length; // Max 6 weeks in a calendar (6*7=42)
      for (let i = 1; i <= remainingCells; i++) {
          days.push({ day: i, isCurrentMonth: false });
      }

      return days;
  });

  // 라인 차트 포인트 계산
  const getLineChartPoints = (trendData) => {
      if (!trendData || trendData.length === 0) return '';

      const svgWidth = 200;
      const svgHeight = 100;
      const padding = 10;
      const usableWidth = svgWidth - 2 * padding;
      const usableHeight = svgHeight - 2 * padding;

      const maxScore = Math.max(...trendData.map(d => d.score)); // 최대값 (동적으로 스케일)
      const minScore = Math.min(...trendData.map(d => d.score)); // 최소값

      // score 0.0 ~ 1.0 (비율)을 SVG Y 좌표로 변환
      const points = trendData.map((data, index) => {
          const x = padding + (index / (trendData.length - 1)) * usableWidth;
          // Y축은 상단이 0, 하단이 max_height
          // score 0.0 -> Y값은 usableHeight + padding (SVG 바닥)
          // score 1.0 -> Y값은 padding (SVG 천장)
          const y = padding + usableHeight - ((data.score - 0) / (1.0 - 0)) * usableHeight; // 0~1.0 스케일
          return `${x},${y}`;
      }).join(' ');

      return points;
  };

  const positiveTrendPoints = computed(() => getLineChartPoints(monthData.value?.positive_trend || []));
  const negativeTrendPoints = computed(() => getLineChartPoints(monthData.value?.negative_trend || []));


  // --- Event Handlers ---
  const prevMonth = () => {
      currentDate.value = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth() - 1, 1);
      fetchMonthlyData(currentDate.value.getFullYear(), currentDate.value.getMonth() + 1);
  };

  const nextMonth = () => {
      currentDate.value = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth() + 1, 1);
      fetchMonthlyData(currentDate.value.getFullYear(), currentDate.value.getMonth() + 1);
  };

  const goToReport = (reportId) => {
      if (reportId) {
          router.push({ name: 'report', query: { reportId: reportId } });
      }
  };

  const toggleView = (view) => {
      selectedView.value = view;
      // In a real app, you'd fetch weekly data if 'weekly' is selected
      // For now, it just changes the active button style.
  };

  // --- Lifecycle Hooks ---
  onMounted(async () => {
      await mainStore.checkLoginStatus();
      if (!mainStore.isLoggedIn) {
          router.push({ name: 'login' }); // 로그인되지 않은 경우 로그인 페이지로 리다이렉트
          return;
      }
      await fetchMonthlyData(currentDate.value.getFullYear(), currentDate.value.getMonth() + 1);
      refreshIcons();
  });

  watch(router.currentRoute, () => {
      refreshIcons();
  });

  </script>

  <template>
      <div id="screen-trends" class="screen screen-scrollable flex-grow">
          <div class="p-6">
              <header class="flex justify-center mb-6">
                  <div class="bg-gray-200 p-1 rounded-full flex">
                      <button
                          :class="['px-6 py-2 rounded-full font-semibold', selectedView === 'monthly' ? 'bg-white shadow text-indigo-600' : 'text-gray-600']"
                          @click="toggleView('monthly')"
                      >월간</button>
                      <button
                          :class="['px-6 py-2 rounded-full font-semibold', selectedView === 'weekly' ? 'bg-white shadow text-indigo-600' : 'text-gray-600']"
                          @click="toggleView('weekly')"
                      >주간</button>
                  </div>
              </header>

              <div v-if="isLoading" class="flex items-center justify-center h-64 text-gray-500">
                  <i data-lucide="loader" class="animate-spin mr-2"></i> 데이터를 불러오는 중...
              </div>
              <div v-else-if="error" class="flex items-center justify-center h-64 text-red-500">
                  <i data-lucide="alert-triangle" class="mr-2"></i> {{ error }}
              </div>
              <div v-else>
                  <!-- 캘린더 -->
                  <div class="bg-white p-4 rounded-2xl shadow-md mb-6">
                      <div class="flex justify-between items-center mb-4 px-2">
                          <button @click="prevMonth" class="text-gray-500 p-1 rounded-full hover:bg-gray-100"><i data-lucide="chevron-left"></i></button>
                          <h3 class="font-bold text-lg cursor-pointer" @click="console.log('Month/Year picker TBD')">{{ formattedMonthYear }}</h3>
                          <button @click="nextMonth" class="text-gray-500 p-1 rounded-full hover:bg-gray-100"><i data-lucide="chevron-right"></i></button>
                      </div>
                      <div class="grid grid-cols-7 text-center text-sm text-gray-500 mb-2">
                          <div>일</div><div>월</div><div>화</div><div>수</div><div>목</div><div>금</div><div>토</div>
                      </div>
                      <div id="calendar-grid" class="grid grid-cols-7 text-center gap-1">
                          <div
                              v-for="(day, index) in generateCalendarDays"
                              :key="index"
                              :class="[
                                  'w-8 h-8 mx-auto rounded-full flex items-center justify-center',
                                  day.isCurrentMonth ? (day.hasEmotion ? getSentimentColorClass(day.sentimentScore) : 'text-gray-800') : 'text-gray-400',
                                  { 'border-2 border-indigo-500 font-bold': day.isToday && day.isCurrentMonth && day.hasEmotion },
                                  { 'cursor-pointer hover:bg-opacity-75': day.hasEmotion }
                              ]"
                              @click="goToReport(day.reportId)"
                          >
                              {{ day.day }}
                          </div>
                      </div>
                  </div>

                  <!-- 월간 감정 변화 추이 -->
                  <div class="bg-white p-5 rounded-2xl shadow-md mb-6">
                      <h3 class="font-bold text-lg mb-4">월간 감정 변화 추이</h3>
                      <div class="w-full h-40 flex items-end justify-center relative">
                          <svg viewBox="0 0 200 100" class="w-full h-full absolute">
                              <!-- Baseline (0.5 for a 0-1 scale, or 50 for 0-100 scale) -->
                              <line x1="10" y1="50" x2="190" y2="50" stroke="#ccc" stroke-width="1" stroke-dasharray="2 2"/>

                              <!-- Positive Trend Line -->
                              <polyline :points="positiveTrendPoints" fill="none" stroke="#22c55e" stroke-width="2"/>
                              <!-- Negative Trend Line -->
                              <polyline :points="negativeTrendPoints" fill="none" stroke="#ef4444" stroke-width="2"/>
                          </svg>
                          <div class="absolute bottom-1 left-0 right-0 flex justify-between px-2 text-xs text-gray-500 w-full">
                              <span v-if="monthData && monthData.positive_trend.length > 0">{{ monthData.positive_trend[0].day }}일</span>
                              <span v-if="monthData && monthData.positive_trend.length > 0">{{ monthData.positive_trend[monthData.positive_trend.length-1].day }}일</span>
                          </div>
                      </div>
                        <div class="flex justify-around text-sm mt-4">
                          <div class="flex items-center"><span class="w-3 h-3 rounded-full bg-green-500 mr-2"></span>긍정 감정</div>
                          <div class="flex items-center"><span class="w-3 h-3 rounded-full bg-red-500 mr-2"></span>부정 감정</div>
                      </div>
                  </div>

                  <!-- 8월 요약 -->
                  <div class="bg-white p-5 rounded-2xl shadow-md">
                      <h3 class="font-bold text-lg mb-2">{{ currentDate.getMonth() + 1 }}월 요약</h3>
                      <p class="text-gray-600" id="monthly-summary">{{ monthData.monthly_summary }}</p>
                  </div>
              </div>
              <div class="h-20"></div> <!-- 하단 여백 -->
          </div>
      </div>
  </template>

  <style scoped>
  .screen {
      display: flex !important; /* Force display */
  }
  </style>
