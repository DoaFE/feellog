// TrendView.vue (Refactored)
<template>
  <div class="trends-view relative p-4 bg-gray-50 h-screen overflow-y-auto no-scrollbar">
    <div class="pb-20">
      <div class="flex justify-between items-center mb-4">
        <button @click="changeMonth(-1)" class="text-lg font-bold p-2">&lt;</button>
        <h2 class="text-xl font-bold">{{ year }}년 {{ month }}월</h2>
        <button @click="changeMonth(1)" class="text-lg font-bold p-2">&gt;</button>
      </div>

      <div class="bg-white p-4 rounded-lg shadow mb-6">
        <p class="text-center text-gray-700">{{ monthlySummary }}</p>
      </div>

      <div class="calendar bg-white p-4 rounded-lg shadow mb-6">
        <div class="grid grid-cols-7 text-center font-bold text-gray-600">
          <div v-for="day in weekDays" :key="day" class="py-2">{{ day }}</div>
        </div>
        <div class="grid grid-cols-7 text-center">
          <div v-for="(day, index) in calendarDays" :key="index"
              class="py-3 relative"
              :class="{ 'text-gray-300': !day.isCurrentMonth, 'cursor-pointer': day.emotionData }"
              @click="handleDateClick(day)">

            <span :class="{'bg-blue-500 text-white rounded-full px-2 py-1': isToday(day.date)}">
              {{ day.day }}
            </span>

            <div v-if="day.emotionData" class="absolute bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full"
                :class="getDotColor(day.emotionData.color)">
            </div>
          </div>
        </div>
      </div>
      <TrendChart v-if="isDataReady" :positiveData="positiveTrend" :negativeData="negativeTrend" />

      <div v-if="isModalOpen" class="absolute inset-0 bg-black bg-opacity-60 flex flex-col justify-center items-center z-50 p-4" @click.self="closeDayModal">
        <div class="w-full max-w-sm">
          <div
            ref="swiperContainerRef"
            class="flex overflow-x-auto snap-x gap-x-4 snap-mandatory no-scrollbar rounded-lg"
            :class="{ 'is-scrolling': isScrolling }"
            @scroll.passive="handleScroll"
          >
            <div
              v-for="(report, index) in selectedDayReports"
              :key="report.report_id"
              class="w-80 flex-shrink-0 snap-center aspect-[2/3]"
              :data-index="index"
            >
              <EmotionCard :report="report.report_card" :reportId="report.report_id" />
            </div>
          </div>

          <div v-if="selectedDayReports.length > 1" class="fixed bottom-80 left-1/2 transform -translate-x-1/2 flex justify-center items-center space-x-4">
            <button
              v-for="(report, index) in selectedDayReports"
              :key="`dot-${report.report_id}`"
              @click="scrollToCard(index)"
              class="w-2 h-2 rounded-full transition-colors duration-300 focus:outline-none"
              :class="currentCardIndex === index ? 'bg-indigo-500 scale-125' : 'bg-gray-300'"
              :aria-label="`${index + 1}번 카드로 이동`"
            ></button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick } from 'vue';
import EmotionCard from '@/components/EmotionCard.vue';
import TrendChart from '@/components/TrendChart.vue';
import axios from 'axios';

// --- 스와이퍼 로직을 위한 ref 추가 ---
const swiperContainerRef = ref(null);
const currentCardIndex = ref(0);
const isScrolling = ref(false); // 스크롤 중인지 상태를 추적하는 ref
let observer = null;
let scrollTimeout = null; // 스크롤 종료 감지를 위한 타임아웃 변수

// ... 기존 ref, computed, 함수들 (변경 없음) ...
const currentDate = ref(new Date());
const monthlySummary = ref("감정 기록을 불러오는 중입니다...");
const emotionsByDate = ref({});
const positiveTrend = ref([]);
const negativeTrend = ref([]);
const isDataReady = ref(false);
const isModalOpen = ref(false);
const selectedDayReports = ref([]);

// --- 기존 computed 및 함수들 (변경 없음) ---
const year = computed(() => currentDate.value.getFullYear());
const month = computed(() => currentDate.value.getMonth() + 1);
const weekDays = ['일', '월', '화', '수', '목', '금', '토'];

const selectedDateForTitle = computed(() => {
  if (selectedDayReports.value.length === 0) return '';
  const date = new Date(selectedDayReports.value[0].created_at);
  return `${date.getMonth() + 1}월 ${date.getDate()}일의 감정 기록`;
});

const fetchMonthlyTrends = async () => {
  isDataReady.value = false;
  try {
    const response = await axios.get('api/trends/monthly', {
      params: { year: year.value, month: month.value }
    });
    if (response.data.success) {
      const data = response.data.current_month_data;
      monthlySummary.value = data.monthly_summary;
      positiveTrend.value = data.positive_trend || [];
      negativeTrend.value = data.negative_trend || [];

      emotionsByDate.value = data.days_with_emotions.reduce((acc, item) => {
        acc[item.date] = item;
        return acc;
      }, {});
      isDataReady.value = true;
    } else {
      monthlySummary.value = "데이터를 불러오지 못했습니다.";
    }
  } catch (error) {
    console.error("Error fetching monthly trends:", error);
    monthlySummary.value = "오류가 발생했습니다.";
    positiveTrend.value = [];
    negativeTrend.value = [];
  }
};

onMounted(fetchMonthlyTrends);

const changeMonth = (delta) => {
  currentDate.value.setMonth(currentDate.value.getMonth() + delta);
  currentDate.value = new Date(currentDate.value);
  fetchMonthlyTrends();
};

const calendarDays = computed(() => {
    const firstDayOfMonth = new Date(year.value, month.value - 1, 1);
    const lastDayOfMonth = new Date(year.value, month.value, 0);
    const firstDayOfWeek = firstDayOfMonth.getDay();
    const daysInMonth = lastDayOfMonth.getDate();
    const days = [];
    const lastDayOfPrevMonth = new Date(year.value, month.value - 1, 0).getDate();

    for (let i = firstDayOfWeek; i > 0; i--) {
        days.push({ day: lastDayOfPrevMonth - i + 1, isCurrentMonth: false, date: null, emotionData: null });
    }

    for (let i = 1; i <= daysInMonth; i++) {
        const dateStr = `${year.value}-${String(month.value).padStart(2, '0')}-${String(i).padStart(2, '0')}`;
        days.push({
            date: dateStr,
            day: i,
            isCurrentMonth: true,
            emotionData: emotionsByDate.value[dateStr] || null
        });
    }

    const totalDays = days.length;
    const remainingDays = (totalDays > 35 ? 42 : 35) - totalDays;
    for(let i=1; i<=remainingDays; i++) {
        days.push({ day: i, isCurrentMonth: false, date: null, emotionData: null });
    }

    return days;
});

const isToday = (dateStr) => {
  if (!dateStr) return false;
  const today = new Date();
  return new Date(dateStr).toDateString() === today.toDateString();
};

const getDotColor = (color) => ({
  'red': 'bg-red-500',
  'blue': 'bg-blue-500',
  'green': 'bg-green-500'
}[color] || 'bg-gray-300');


const handleDateClick = (day) => {
  if (day.emotionData && day.emotionData.reports) {
    openDayModal(day.emotionData.reports);
  }
};

// --- [신규] Dot 클릭 시 해당 카드로 스크롤하는 함수 ---
const scrollToCard = (index) => {
  if (!swiperContainerRef.value) return;
  const container = swiperContainerRef.value;
  const cardWidth = container.offsetWidth;
  container.scrollTo({
    left: index * cardWidth,
    behavior: 'smooth'
  });
};

// --- [신규] 스크롤 이벤트를 처리하여 스와이프와 클릭 충돌을 방지하는 함수 ---
const handleScroll = () => {
  isScrolling.value = true;
  clearTimeout(scrollTimeout);
  // 스크롤이 멈춘 후 150ms 뒤에 isScrolling 상태를 false로 변경 (디바운싱)
  scrollTimeout = setTimeout(() => {
    isScrolling.value = false;
  }, 150);
};

// --- [수정] 모달 열기/닫기 함수 ---
const openDayModal = (reports) => {
  selectedDayReports.value = reports;
  currentCardIndex.value = 0;
  isModalOpen.value = true;

  nextTick(() => {
    if (swiperContainerRef.value && reports.length > 1) {
      const options = {
        root: swiperContainerRef.value,
        threshold: 0.5
      };
      observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            currentCardIndex.value = parseInt(entry.target.dataset.index, 10);
          }
        });
      }, options);
      Array.from(swiperContainerRef.value.children).forEach(child => {
        observer.observe(child);
      });
    }
  });
};

const closeDayModal = () => {
  isModalOpen.value = false;
  if (observer) {
    observer.disconnect();
    observer = null;
  }
  clearTimeout(scrollTimeout); // 모달 닫을 때 타임아웃 정리
};

</script>

<style scoped>
.no-scrollbar::-webkit-scrollbar { display: none; }
.no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }

/* [추가] 스크롤 중일 때 카드 내부의 클릭 이벤트를 비활성화 */
.is-scrolling > div > * {
  pointer-events: none;
}
</style>
