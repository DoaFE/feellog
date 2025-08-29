<script setup>
    import { ref, onMounted, nextTick, watch } from 'vue';
    import { useRouter } from 'vue-router';
    import axios from 'axios';
    import { createLucideIcon, icons } from 'lucide-vue-next';
    import EmotionCard from '../components/EmotionCard.vue'; // EmotionCard 컴포넌트 임포트
    import { useMainStore } from '@/stores/main';

    const router = useRouter();
    const mainStore = useMainStore();

    const chatbotName = ref('도담이'); // 기본 챗봇 이름 (추후 DB에서 불러올 예정)
    const messages = ref([]); // { type: 'user' | 'chatbot' | 'report_card', content: string | object }
    const userInput = ref('');
    const isLoading = ref(false);
    const chatbotContent = ref(null); // Ref for the scrollable chat content area

    const refreshIcons = () => {
        nextTick(() => {
            createLucideIcon({ icons, attrs: { class: 'lucide-icon' }, nameAttr: 'data-lucide' });
        });
    };

    const scrollToBottom = () => {
        nextTick(() => {
            if (chatbotContent.value) {
                chatbotContent.value.scrollTop = chatbotContent.value.scrollHeight;
            }
        });
    };

    const fetchLatestReport = async () => {
        if (!mainStore.isLoggedIn) {
            // 게스트 모드이거나 로그인되지 않은 경우 초기 메시지
            messages.value.push({
                type: 'chatbot',
                content: "안녕하세요! Feel-Log에 오신 것을 환영합니다. 로그인 후 영상을 기록하여 감정 리포트를 받아보세요!"
            });
            scrollToBottom();
            return;
        }

        try {
            const response = await axios.get('/api/reports/latest');
            if (response.data.success && response.data.report) {
                const report = response.data.report;
                messages.value.push({
                    type: 'chatbot',
                    content: `안녕하세요! ${report.report_created}자 감정 분석이 완료되었어요. ${mainStore.userId}님의 하루는 어땠는지 함께 살펴볼까요?`
                });
                messages.value.push({
                    type: 'report_card',
                    content: report.report_card_data // EmotionCard에 직접 전달할 데이터
                });
            } else {
                messages.value.push({
                    type: 'chatbot',
                    content: "안녕하세요! 아직 기록된 감정 분석 결과가 없네요. '감정 기록하기'를 통해 첫 리포트를 만들어 보세요!"
                });
            }
        } catch (error) {
            console.error('Failed to fetch latest report:', error);
            messages.value.push({
                type: 'chatbot',
                content: "죄송해요, 최신 감정 리포트를 가져오는 데 문제가 발생했어요. 다시 시도해 주세요."
            });
        } finally {
            scrollToBottom();
        }
    };

    const sendMessage = async () => {
        if (!userInput.value.trim() || isLoading.value) return;

        const userMessage = userInput.value;
        messages.value.push({ type: 'user', content: userMessage });
        userInput.value = ''; // 입력 필드 초기화
        scrollToBottom();

        isLoading.value = true;

        try {
            const response = await axios.post('/api/chatbot/chat', {
                message: userMessage,
                user_id: mainStore.userId // 로그인된 사용자 ID 전달
            });

            if (response.data.success) {
                messages.value.push({ type: 'chatbot', content: response.data.response });
            } else {
                messages.value.push({ type: 'chatbot', content: `챗봇 오류: ${response.data.message}` });
            }
        } catch (error) {
            console.error('Chatbot API error:', error);
            messages.value.push({ type: 'chatbot', content: '죄송해요, 챗봇과 연결하는 데 문제가 발생했어요.' });
        } finally {
            isLoading.value = false;
            scrollToBottom();
        }
    };

    const viewReport = (reportId) => {
      // TODO: ReportView로 이동하면서 reportId를 넘겨주도록 구현
      console.log('View full report for ID:', reportId);
      router.push({ name: 'report', query: { reportId: reportId } });
    };

    onMounted(async () => {
        await mainStore.checkLoginStatus(); // 로그인 상태 확인
        await fetchLatestReport(); // 최신 리포트 불러오기
        refreshIcons();
    });

    // 라우트 변경 시 아이콘 새로고침
    watch(router.currentRoute, () => {
        refreshIcons();
    });

    // messages 배열이 업데이트될 때마다 스크롤바를 아래로 이동
    watch(messages, () => {
        scrollToBottom();
    }, { deep: true });
    </script>

    <template>
        <div id="screen-chatbot" class="screen p-6 flex flex-col flex-grow">
            <header class="flex items-center mb-6">
                <div class="w-12 h-12 bg-indigo-200 rounded-full flex items-center justify-center mr-4">
                    <i data-lucide="bot" class="text-indigo-600"></i>
                </div>
                <h2 id="chatbot-name" class="text-2xl font-bold text-gray-800">{{ chatbotName }}</h2>
            </header>
            <div ref="chatbotContent" class="chatbot-content flex-grow space-y-4 overflow-y-auto scrollbar-hide pb-8">
                <template v-for="(message, index) in messages" :key="index">
                    <div v-if="message.type === 'chatbot'" class="bg-gray-200 p-4 rounded-lg rounded-bl-none max-w-xs self-start">
                        <p>{{ message.content }}</p>
                    </div>
                    <div v-else-if="message.type === 'user'" class="bg-indigo-500 text-white p-4 rounded-lg rounded-br-none max-w-xs self-end ml-auto">
                        <p>{{ message.content }}</p>
                    </div>
                    <div v-else-if="message.type === 'report_card'" class="w-full">
                        <div class="bg-white p-5 rounded-2xl shadow-md border border-indigo-200 mx-auto">
                            <h3 class="font-bold text-lg mb-2">오늘의 감정 카드 💌</h3>
                            <div class="flex items-center justify-between mb-4">
                                <div class="flex items-center">
                                <p class="text-5xl mr-4">{{ message.content.overall_emotion_icon }}</p>
                                <div>
                                    <p class="text-gray-600">주요 감정</p>
                                    <p class="text-2xl font-bold text-gray-800">{{ message.content.dominant_overall_emotion }}</p>
                                </div>
                                </div>
                                <div class="text-right">
                                    <p class="text-gray-600">감정 비율</p>
                                    <p class="text-2xl font-bold text-indigo-600">{{ message.content.emotion_distribution?.[0]?.percentage || 'N/A' }}</p>
                                </div>
                            </div>
                            <button
                                @click="viewReport(message.content.report_id)"
                                class="mt-4 w-full bg-indigo-100 text-indigo-700 font-semibold py-3 rounded-lg hover:bg-indigo-200"
                            >
                                자세한 리포트 보기
                            </button>
                        </div>
                    </div>
                </template>
                <div v-if="isLoading" class="bg-gray-200 p-4 rounded-lg rounded-bl-none max-w-xs self-start animate-pulse">
                    <p>... 생각 중 ...</p>
                </div>
            </div>
            <div class="chatbot-input-container">
                <div class="p-2 bg-white rounded-full flex items-center shadow-sm border">
                    <input type="text" id="chatbot-input" v-model="userInput" @keyup.enter="sendMessage" placeholder="이번 주 감정은 어땠어?" class="flex-grow bg-transparent px-4 focus:outline-none">
                    <button id="chatbot-send-btn" class="bg-indigo-500 text-white rounded-full p-2 hover:bg-indigo-600" @click="sendMessage">
                        <i data-lucide="send"></i>
                    </button>
                </div>
            </div>
        </div>
    </template>

    <style scoped>
    .screen {
        display: flex !important; /* Force display */
    }
    .chatbot-content {
        padding-bottom: 8rem; /* Enough space for the input container */
    }
    </style>
