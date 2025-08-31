<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import axios from 'axios';
import { Smile, Frown, Angry, Annoyed, Drama, Meh, ChevronDown, Clock } from 'lucide-vue-next';

const route = useRoute();
const router = useRouter();

const reportData = ref(null);
const isLoading = ref(true);
const error = ref(null);
const performanceVisible = ref(false);

// 감정 아이콘 및 색상 매핑
const getEmotionDetails = (emotion) => {
  const details = {
    '기쁨': { icon: Smile, color: 'text-green-500', bgColor: 'bg-green-100' },
    '슬픔': { icon: Frown, color: 'text-blue-500', bgColor: 'bg-blue-100' },
    '분노': { icon: Angry, color: 'text-red-500', bgColor: 'bg-red-100' },
    '불안': { icon: Annoyed, color: 'text-yellow-500', bgColor: 'bg-yellow-100' },
    '당황': { icon: Drama, color: 'text-purple-500', bgColor: 'bg-purple-100' },
    '상처': { icon: Drama, color: 'text-orange-500', bgColor: 'bg-orange-100' },
    '중립': { icon: Meh, color: 'text-gray-500', bgColor: 'bg-gray-100' },
  };
  return details[emotion] || details['중립'];
};

// 백분율 막대 너비 계산
const getBarWidth = (value) => `${Math.round(value * 100)}%`;

const fetchDetailedReport = async (reportId) => {
  isLoading.value = true;
  error.value = null;
  try {
    // [수정] API 경로를 백엔드와 일치시킴
    const response = await axios.get(`/api/report/${reportId}`);
    reportData.value = response.data;
  } catch (err) {
    console.error('Error fetching detailed report:', err);
    error.value = '상세 리포트를 불러오는 데 실패했습니다.';
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  const reportId = route.params.reportId; // [수정] .query -> .params
  if (reportId) {
    fetchDetailedReport(reportId);
  } else {
    error.value = '리포트 ID가 제공되지 않았습니다.';
    isLoading.value = false;
  }
});

// 초를 MM:SS 형식으로 변환하는 헬퍼
const formatTime = (seconds) => {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
};

// 가장 높은 비율의 감정을 찾는 헬퍼
const getDominantEmotion = (emotions) => {
    if (!emotions || typeof emotions !== 'object') return null;
    return Object.entries(emotions).reduce((a, b) => a[1] > b[1] ? a : b, [null, -1])[0];
};

</script>

<template>
  <div class="flex flex-col h-screen bg-gray-50 p-4">
    <header class="flex items-center mb-4 flex-shrink-0">
      <button class="p-2 rounded-full hover:bg-gray-200" @click="router.go(-1)">
        <ArrowLeftIcon class="w-6 h-6" />
      </button>
      <h1 class="text-xl font-bold mx-auto">상세 감정 리포트</h1>
      <div class="w-10"></div> </header>

    <div v-if="isLoading" class="text-center py-10 flex-grow flex items-center justify-center">
      <p>리포트를 불러오는 중...</p>
    </div>
    <div v-else-if="error" class="text-center py-10 flex-grow flex items-center justify-center text-red-500">
      <p>{{ error }}</p>
    </div>

    <div v-else-if="reportData" class="flex-grow overflow-y-auto no-scrollbar space-y-6 pb-4">

      <div class="bg-white p-5 rounded-2xl shadow-sm">
        <p class="text-sm text-gray-500">{{ new Date(reportData.created_at).toLocaleString('ko-KR') }}</p>
        <div class="flex items-center justify-between mt-2">
          <div>
            <h2 class="text-lg font-semibold">종합 분석 결과</h2>
            <p class="text-3xl font-bold mt-1" :class="getEmotionDetails(reportData.report_summary.dominant_emotion).color">
              {{ reportData.report_summary.dominant_emotion }}
            </p>
          </div>
          <div class="text-right">
            <p class="text-lg font-semibold">종합 점수</p>
            <p class="text-3xl font-bold text-indigo-600">{{ reportData.report_summary.overall_score }}점</p>
          </div>
        </div>
      </div>

      <div>
        <h2 class="text-lg font-semibold mb-3 px-2">구간별 상세 분석</h2>
        <div class="space-y-4">
          <div v-for="segment in reportData.report_detail.segment_analyses" :key="segment.segment_id" class="bg-white p-4 rounded-xl shadow-sm">
            <div class="flex items-center justify-between mb-3">
              <span class="font-bold text-indigo-600">구간 {{ segment.segment_id }}</span>
              <span class="text-sm text-gray-500">{{ formatTime(segment.start_time) }} - {{ formatTime(segment.end_time) }}</span>
            </div>
            <p class="p-3 bg-gray-100 rounded-lg mb-4 text-gray-800">"{{ segment.transcribed_text }}"</p>
            <div class="space-y-3 text-sm">
              <div class="flex items-center">
                <span class="w-16 font-semibold">표정 분석</span>
                <div class="flex items-center gap-2">
                   <component :is="getEmotionDetails(segment.visual_analysis.dominant_emotion).icon" class="w-5 h-5" :class="getEmotionDetails(segment.visual_analysis.dominant_emotion).color" />
                   <span>{{ segment.visual_analysis.dominant_emotion }}</span>
                </div>
              </div>
              <div class="flex items-center">
                <span class="w-16 font-semibold">대화 분석</span>
                 <div class="flex items-center gap-2">
                   <component :is="getEmotionDetails(getDominantEmotion(segment.audio_analysis.text_based_analysis.emotions)).icon" class="w-5 h-5" :class="getEmotionDetails(getDominantEmotion(segment.audio_analysis.text_based_analysis.emotions)).color" />
                   <span>{{ getDominantEmotion(segment.audio_analysis.text_based_analysis.emotions) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-2xl shadow-sm">
        <button @click="performanceVisible = !performanceVisible" class="w-full flex justify-between items-center p-4 font-semibold">
          <span>기술 정보</span>
          <ChevronDown class="w-5 h-5 transition-transform" :class="{'rotate-180': performanceVisible}" />
        </button>
        <div v-if="performanceVisible" class="p-4 border-t text-xs text-gray-600 space-y-2">
           <p><strong>총 처리 시간:</strong> {{ reportData.report_detail.performance.overall_processing.total_elapsed_seconds.toFixed(2) }}초</p>
           <p><strong>음성 분리 시간:</strong> {{ reportData.report_detail.performance.overall_processing.speech_segmentation_seconds.toFixed(2) }}초</p>
           <p><strong>총 구간 수:</strong> {{ reportData.report_detail.total_segments }}개</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* [추가] 스크롤바를 숨기기 위한 유틸리티 클래스 */
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;  /* IE and Edge */
  scrollbar-width: none;  /* Firefox */
}
</style>
