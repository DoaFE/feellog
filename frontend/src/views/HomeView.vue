<template>
  <div class="container">
    <main class="screen">
      <header class="px pt">
        <div class="brand">Feel-Log</div>
        <div class="date">{{ currentDate }}</div>
        <p class="subtitle">안녕하세요, {{ user_nickname }}님!<br />오늘 하루도 기록하며 자신을 알아가세요!</p>
      </header>

      <div class="cta-wrap">
        <button @click="goToRecord" class="cta-card" aria-label="오늘의 감정 기록하기">
          <CameraIcon class="cta-icon" aria-hidden="true" />
          <div class="cta-text">오늘의 감정 기록하기</div>
        </button>
      </div>

      <h3 class="section-title">최근 감정 요약</h3>
      <div class="cards-wrapper">
        <!--<button class="scroll-btn left" @click="scrollLeft" aria-label="왼쪽으로 스크롤">&lt;</button>-->
        <section class="cards" ref="cardsContainer" aria-label="최근 감정 요약 카드 목록">
          <article class="card">
            <div v-if="latestReport" class="bg-white p-4 rounded-lg shadow row">
              <div>
                <p class="font-bold text-gray-800 mb-2">주요 감정은 '{{ reportSummary.dominant_emotion }}'이며, 전체 점수는 {{ reportSummary.overall_score }}점입니다.</p>
                <p class="text-sm text-gray-600">
                  {{ generatedSummaryMessage }}
                </p>
                <!--
                <div class="text-right mt-2">
                  <router-link :to="`/report/${latestReport.report_id}`" class="text-blue-500 text-sm hover:underline">
                    자세히 보기 &rarr;
                  </router-link>
                </div>
                -->
              </div>
            </div>
            <div v-else class="bg-white p-4 rounded-lg shadow text-center text-gray-500">
              <p>{{ loadingMessage }}</p>
            </div>
          </article>
        </section>
        <!--<button class="scroll-btn right" @click="scrollRight" aria-label="오른쪽으로 스크롤">&gt;</button>-->
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { CameraIcon } from 'lucide-vue-next';
import { useMainStore } from '@/stores/main';
import axios from 'axios';

// --- 스크립트 통합: 기존 Options API 로직을 Composition API로 변환 ---

// 1. 날짜 및 DOM 요소 관련 ref 선언
const currentDate = ref('');
const cardsContainer = ref(null); // template의 ref="cardsContainer"와 연결됨

// 2. 스크롤 메서드 정의
const scrollAmount = 316; // 300px card + 16px gap
const scrollLeft = () => {
  if (cardsContainer.value) {
    cardsContainer.value.scrollTo({
      left: cardsContainer.value.scrollLeft - scrollAmount,
      behavior: 'smooth'
    });
  }
};
const scrollRight = () => {
  if (cardsContainer.value) {
    cardsContainer.value.scrollTo({
      left: cardsContainer.value.scrollLeft + scrollAmount,
      behavior: 'smooth'
    });
  }
};

// --- 기존 <script setup> 로직 유지 ---

const router = useRouter();
const mainStore = useMainStore();

const latestReport = ref(null);
const reportSummary = ref(null); // 객체를 받을 수 있으므로 초기값을 null로 변경
const generatedSummaryMessage = ref('');
const loadingMessage = ref('최신 리포트를 불러오는 중입니다...');
const user = ref(null);
const user_nickname = ref("게스트");

const goToRecord = () => {
  router.push('/record');
};

const fetchLatestReport = async () => {
  try {
    const response = await axios.get('api/reports/latest');
    //console.log("받아온 데이터:", response.data);
    //console.log("데이터 타입:", typeof response.data);
    if (response.data.success && response.data.report) {
      latestReport.value = response.data.report;
      reportSummary.value = response.data.report_summary; // 객체 자체를 저장
      generatedSummaryMessage.value = response.data.generated_summary_message;
    } else {
      loadingMessage.value = "기록된 감정 리포트가 없습니다.";
    }
  } catch (error) {
    console.error("Error fetching latest report:", error);
    loadingMessage.value = "리포트를 불러오는 중 오류가 발생했습니다.";
  }
};

// onMounted 훅으로 로직 통합
onMounted(async () => {
  // 날짜 설정 로직
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  const day = today.getDate();
  const weekday = today.toLocaleDateString('ko-KR', { weekday: 'long' });
  currentDate.value = `${year}년 ${month}월 ${day}일 ${weekday}`;

  // 로그인 상태 확인 및 데이터 호출
  await mainStore.checkLoginStatus();
  if (mainStore.isLoggedIn) {
    await fetchLatestReport();
    user_nickname.value = mainStore.user.user_nickname;
  } else {
    loadingMessage.value = "로그인 후 감정 기록을 확인해보세요.";
  }
});
</script>

<style scoped>
/* 스타일은 변경되지 않았으므로 생략 */
:root{
  --indigo:#4f46e5;
  --indigo-700:#4338ca;
  --text:#0f172a;
  --muted:#64748b;
  --card:#ffffff;
  --shell:#0b1220;
  --bg:#f1f5f9;
}
*{box-sizing:border-box}
body{
  margin:0;
  background:var(--bg);
  font-family: 'Inter','Noto Sans KR', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
  color:var(--text);
}
.container {
  display: flex;
  flex-direction: column;
  height: 100vh; /* 화면 전체 높이 */
}
.screen{
  background:#fff;
  border-radius:10px;
  overflow:hidden;
  box-shadow:0 10px 30px rgba(2,6,23,.06);
  display:flex;
  flex-direction:column;
}
/* content paddings */
.px{padding-left:24px; padding-right:24px;}
.pt{padding-top:24px;}
.pb{padding-bottom:16px;}
.brand{
  font-family:'Montserrat', sans-serif; font-weight:700; color:var(--indigo);
  font-size:28px; letter-spacing:.3px;
}
.date{ color:var(--muted); margin-top:8px; font-size:20px; }
.subtitle{ margin-top:8px; font-size:18px; line-height:1.6; color:#1f2937; }
/* Big CTA card */
.cta-wrap{ margin-top:24px; padding:0 24px; }
.cta-card{
  width:100%; height:280px; border-radius:28px; background:#4f46e5;
  display:flex; flex-direction:column; align-items:center; justify-content:center; gap:14px;
  color:#ffffff; text-decoration:none; box-shadow: 0 18px 30px rgba(79,70,229,.32);
}
.cta-icon{ width:120px; height:120px; display:block; }
.cta-text{ font-size:20px; font-weight:700; }
/* Section title */
.section-title{ font-weight:700; color:#1f2937; margin-top:28px; margin-bottom:12px; padding:0 24px; }
/* Horizontal cards */
.cards-wrapper {
  position: relative;
  margin: 0 8px; /* Optional adjustment for button placement */
}
.cards{
  padding:0 16px 8px 16px;
  overflow-x: scroll;
  display:flex; gap:16px; scroll-snap-type:x mandatory;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}
.cards::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}
.card{
  min-width:300px; max-width:360px; background:var(--card); border-radius:18px;
  box-shadow:0 8px 24px rgba(2,6,23,.08);
  padding:20px; scroll-snap-align:start;
}
.card .row{ display:flex; flex-direction: column; gap:14px; } /* flex-direction 변경 */
.emoji{ font-size:32px; line-height:1; }
.card-title{ margin:0 0 4px 0; font-weight:700; }
.card-desc{ margin:0; color:#6b7280; }
.emphasis{ color:#16a34a; font-weight:700; }
/* Scroll buttons */
.scroll-btn {
  position: absolute;
  top: 50%; /* 수직 중앙 정렬 개선 */
  transform: translateY(-50%);
  background: white;
  border: 1px solid #ccc;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  font-size: 18px;
  color: #333;
}
.left {
  left: 16px;
}
.right {
  right: 16px;
}
.sr-only{ position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); border:0;}
</style>
