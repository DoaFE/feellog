// EmotionCard.vue
<template>
  <div class="flip-card" :style="{ height: cardHeight }">
    <div class="flip-card-inner" :class="{ 'is-flipped': isFlipped }" @click="toggleFlip">

      <div class="flip-card-front" ref="emotionCardFront">
        <div class="weather flex min-h-[10em] w-full flex-col items-center justify-center gap-[0.5em] rounded-[1.5em] bg-[#FFDAE9] px-4 py-3 font-nunito text-[#F471A6] shadow-[0px_4px_16px_0px_#222]">
          <div class="flex h-fit w-full items-center justify-center gap-4">
            <span class="text-5xl">{{ overallEmotionIcon }}</span>
            <span class="h-16 w-[1px] rounded-full bg-[hsla(336,86%,70%,0.5)]"></span>
            <div class="flex flex-col items-start justify-center">
              <p class="text-xs font-bold">현재 당신의 감정온도는?!</p>
              <p class="text-2xl font-semibold">{{ sentimentScore }}°C</p>
              <div class="flex items-center justify-center gap-1">
                <p class="text-[0.725rem]" style="text-align: left;">{{ overallEmotionMessage }}</p>
              </div>
            </div>
          </div>
          <div class="h-[0.5px] w-full rounded-full bg-[hsla(336,86%,70%,0.5)]"></div>
          <div class="flex h-fit w-full items-center justify-between">
            <div class="flex h-fit w-full flex-col items-start justify-between text-xs">
              <div v-for="(item, index) in emotionDistribution" :key="index" class="flex flex-row items-center justify-center gap-2 p-1">
                <span>{{ item.icon }}</span>
                <span class="h-2 w-[1px] rounded-full bg-[hsla(336,86%,70%,0.5)]"></span>
                <p class="w-10">{{ item.emotion }}</p>
                <span class="h-2 w-[1px] rounded-full bg-[hsla(336,86%,70%,0.5)]"></span>
                <p>{{ item.percentage }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="flip-card-back">
        <div ref="emotionCardBack" class="p-4 rounded-lg shadow-md border h-full overflow-y-auto no-scrollbar" :class="cardBorderColor">
          <div v-if="report && report.report_html_content" v-html="report.report_html_content" class="w-full"></div>
          <div v-else class="text-center text-gray-500">리포트 데이터를 불러올 수 없습니다.</div>
        </div>
        <div class="actions-container absolute bottom-2 left-1/2 -translate-x-1/2 flex justify-center space-x-2 w-full">
          <button @click.stop="saveCardAsImage" class="px-3 py-1.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-xs shadow-md">
            이미지로 저장
          </button>
          <button @click.stop="goToReportView" class="px-3 py-1.5 bg-gray-700 text-white rounded-lg hover:bg-gray-800 transition-colors text-xs shadow-md">
            상세 리포트 보기
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// [수정 3] onMounted, onUnmounted, onUpdated 생명주기 훅 추가
import { ref, computed, onMounted, onUnmounted, onUpdated } from 'vue';
import { useRouter } from 'vue-router';
import html2canvas from 'html2canvas';
import axios from 'axios';

const props = defineProps({
  report: { type: Object, required: true },
  reportId: { type: String, required: true }
});

const isFlipped = ref(false);
const router = useRouter();
const emotionCardBack = ref(null);

// --- 높이 계산 로직 추가 ---
const emotionCardFront = ref(null); // 앞면 div를 참조할 ref
const cardHeight = ref('auto'); // 카드 높이를 저장할 ref

const updateCardHeight = () => {
  if (emotionCardFront.value) {
    // 앞면 div의 실제 높이를 측정하여 cardHeight 값으로 설정
    cardHeight.value = `${emotionCardFront.value.offsetHeight}px`;
  }
};

// 컴포넌트가 마운트(생성)될 때 높이 계산 및 resize 이벤트 리스너 추가
onMounted(() => {
  updateCardHeight();
  window.addEventListener('resize', updateCardHeight);
});

// 컴포넌트가 업데이트될 때 높이 재계산 (내부 데이터 변경으로 높이가 달라질 경우 대비)
onUpdated(() => {
  updateCardHeight();
});

// 컴포넌트가 언마운트(제거)될 때 메모리 누수 방지를 위해 이벤트 리스너 제거
onUnmounted(() => {
  window.removeEventListener('resize', updateCardHeight);
});
// --- 높이 계산 로직 끝 ---


const toggleFlip = () => {
  isFlipped.value = !isFlipped.value;
};

// ... 기존 computed 속성들은 변경 없이 그대로 유지 ...
const sentimentScore = computed(() => props.report?.sentiment_score?.toFixed(1) || 'N/A');
const overallEmotionMessage = computed(() => props.report?.overall_emotion_message || '감정 분석 결과가 없습니다.');
const overallEmotionIcon = computed(() => props.report?.overall_emotion_icon || '😐');
const emotionDistribution = computed(() => {
  if (props.report?.emotion_distribution && Array.isArray(props.report.emotion_distribution)) {
    const distribution = [...props.report.emotion_distribution];
    while (distribution.length < 3) {
      distribution.push({ icon: 'N/A', emotion: 'N/A', percentage: '0%' });
    }
    return distribution;
  }
  return [
    { icon: 'N/A', emotion: 'N/A', percentage: '0%' },
    { icon: 'N/A', emotion: 'N/A', percentage: '0%' },
    { icon: 'N/A', emotion: 'N/A', percentage: '0%' },
  ];
});
const cardBorderColor = computed(() => {
  if (!props.report || typeof props.report.sentiment_score === 'undefined') return 'border-gray-200';
  return props.report.sentiment_score >= 50 ? 'border-blue-300' : 'border-red-300';
});


const goToReportView = () => {
  if (props.reportId) router.push(`/report/${props.reportId}`);
};

const saveCardAsImage = async () => {
  if (!emotionCardBack.value) return;
  try {
    const canvas = await html2canvas(emotionCardBack.value, {
      useCORS: true,
      backgroundColor: '#ffffff',
      scale: 2
    });
    const base64Image = canvas.toDataURL('image/png');
    await axios.post(`/api/report/${props.reportId}/image`, { base64_image: base64Image });
    alert('감정 카드가 이미지로 저장되었습니다.');
  } catch (error) {
    console.error('이미지 저장 실패:', error);
    alert('이미지 저장 중 오류가 발생했습니다.');
  }
};
</script>

<style scoped>
/* 스타일은 변경 없음 */
.flip-card {
  background-color: transparent;
  width: 100%;
  /* min-height는 유지하되, 실제 height는 script에서 동적으로 제어 */
  min-height: 10em;
  perspective: 1000px;
  /* 부드러운 높이 전환 효과 추가 (선택 사항) */
  transition: height 0.3s ease-in-out;
}
.flip-card-inner {
  position: relative;
  width: 100%;
  height: 100%;
  text-align: center;
  transition: transform 0.6s;
  transform-style: preserve-3d;
}
.flip-card-inner.is-flipped {
  transform: rotateY(180deg);
}
.flip-card-front, .flip-card-back {
  position: absolute;
  width: 100%;
  height: 100%;
  -webkit-backface-visibility: hidden;
  backface-visibility: hidden;
}
.flip-card-back {
  transform: rotateY(180deg);
  background-color: white;
  border-radius: 1.5em;
  padding-bottom: 50px;
}
.actions-container {
  padding: 0 1rem;
}
.no-scrollbar::-webkit-scrollbar { display: none; }
.no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
</style>
