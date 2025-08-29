<script setup>
    import { ref, onMounted, nextTick, watch, computed } from 'vue';
    import { useRouter, useRoute } from 'vue-router';
    import axios from 'axios';
    import { createLucideIcon } from 'lucide-vue-next';
    import { useMainStore } from '@/stores/main';

    const mainStore = useMainStore();
    const router = useRouter();
    const route = useRoute();

    const reportData = ref(null);
    const isLoading = ref(true);
    const error = ref(null);

    const refreshIcons = () => {
        nextTick(() => {
            createLucideIcon({ icons, attrs: { class: 'lucide-icon' }, nameAttr: 'data-lucide' });
        });
    };

    // SVG 파이 차트 그리기 헬퍼 함수
    const getCoordinatesForPercent = (percent) => {
        const x = Math.cos(2 * Math.PI * percent);
        const y = Math.sin(2 * Math.PI * percent);
        return [x, y];
    };

    const getPieChartPath = (startPercent, endPercent) => {
        if (!reportData.value) return '';
        const radius = 45; // SVG viewBox (0 0 100 100) 기준
        const cx = 50;
        const cy = 50;

        const [startX, startY] = getCoordinatesForPercent(startPercent);
        const [endX, endY] = getCoordinatesForPercent(endPercent);

        const largeArcFlag = endPercent - startPercent > 0.5 ? 1 : 0; // 0.5 = 180 degrees

        const pathData = [
            `M ${cx + startX * radius} ${cy + startY * radius}`, // Start at arc perimeter
            `A ${radius} ${radius} 0 ${largeArcFlag} 1 ${cx + endX * radius} ${cy + endY * radius}`, // Arc
            `L ${cx} ${cy}`, // Line to center
            `Z` // Close path
        ].join(' ');
        return pathData;
    };

    // 감정별 색상 매핑
    const getEmotionColor = (emotion) => {
        switch (emotion) {
            case '기쁨': return '#4ade80'; // green-400
            case '슬픔': return '#f87171'; // red-400
            case '분노': return '#60a5fa'; // blue-400
            case '불안': return '#fbbf24'; // amber-400
            case '당황': return '#a78bfa'; // purple-400
            case '상처': return '#ef4444'; // red-500
            case '중립': return '#a1a1aa'; // zinc-400
            default: return '#e5e7eb'; // gray-200
        }
    };

    // 파이 차트 데이터 계산 (reportData.analysis_emotion_distribution 사용)
    const pieChartSegments = computed(() => {
        if (!reportData.value || !reportData.value.analysis_emotion_distribution) return [];

        let currentPercent = 0;
        const segments = [];
        // Gemini에서 오는 emotion_distribution은 이미 정렬되어 있고 퍼센티지가 % 문자열로 되어있음
        const sortedDistribution = [...reportData.value.analysis_emotion_distribution].filter(item => parseFloat(item.percentage) > 0);

        // 상위 3개 감정 외 '기타'로 묶기
        let otherPercentage = 100;
        const top3Emotions = sortedDistribution.slice(0, 3);
        top3Emotions.forEach(item => {
            const percentageValue = parseFloat(item.percentage.replace('%', ''));
            otherPercentage -= percentageValue;
        });

        // Calculate paths for top 3 emotions
        top3Emotions.forEach(item => {
            const percentageValue = parseFloat(item.percentage.replace('%', '')) / 100;
            const start = currentPercent;
            const end = currentPercent + percentageValue;
            segments.push({
                emotion: item.emotion,
                percentage: item.percentage,
                color: getEmotionColor(item.emotion),
                path: getPieChartPath(start, end)
            });
            currentPercent = end;
        });

        // Add '기타' segment if remaining percentage is positive
        if (otherPercentage > 0) {
            const start = currentPercent;
            const end = currentPercent + (otherPercentage / 100);
            segments.push({
                emotion: '기타',
                percentage: `${Math.round(otherPercentage)}%`,
                color: getEmotionColor('기타'), // 기본 기타 색상
                path: getPieChartPath(start, end)
            });
        }
        return segments;
    });

    // 시간별 감정 변화 데이터 계산 (간단한 예시: 얼굴 감정 중 긍정/부정 비율 추이)
    const timeSeriesData = computed(() => {
        if (!reportData.value || !reportData.value.analysis_face_emotions_time_series_rates) return { points: '', labels: [] };

        const series = reportData.value.analysis_face_emotions_time_series_rates;
        if (series.length === 0) return { points: '', labels: [] };

        const svgWidth = 200;
        const svgHeight = 100;
        const padding = 10;
        const usableWidth = svgWidth - 2 * padding;
        const usableHeight = svgHeight - 2 * padding;

        // 모든 감정 점수 (0-100)를 통합해서 단일 라인으로 그리기 (예: 긍정-부정 스코어)
        const scores = series.map(segment => {
            const dist = segment.emotions;
            return (dist['기쁨'] || 0) - ((dist['분노'] || 0) + (dist['슬픔'] || 0) + (dist['불안'] || 0) + (dist['상처'] || 0));
        });

        // score를 -1 ~ 1 에서 0 ~ 100 으로 스케일링
        const scaledScores = scores.map(score => ((score + 1) / 2) * 100);

        const maxScore = 100; // Fixed for 0-100 scale
        const minScore = 0;   // Fixed for 0-100 scale

        const points = scaledScores.map((score, index) => {
            const x = padding + (index / (series.length - 1)) * usableWidth;
            const y = padding + usableHeight - ((score - minScore) / (maxScore - minScore)) * usableHeight;
            return `${x},${y}`;
        }).join(' ');

        // 시간 레이블 (시작/중간/끝 3개 정도)
        const labels = [];
        if (series.length > 0) {
            labels.push(series[0].time);
            if (series.length > 2) {
                labels.push(series[Math.floor(series.length / 2)].time);
            }
            if (series.length > 1) {
                 labels.push(series[series.length - 1].time);
            }
        }
        return { points, labels, rawScores: scaledScores, times: series.map(s => s.time) };
    });


    const fetchDetailedReport = async (reportId) => {
        isLoading.value = true;
        error.value = null;
        try {
            const response = await axios.get(`/api/reports/${reportId}`);
            if (response.data.success) {
                reportData.value = response.data.report;
                console.log("Fetched detailed report:", reportData.value);
            } else {
                error.value = response.data.message;
            }
        } catch (err) {
            console.error('Error fetching detailed report:', err);
            error.value = '상세 리포트를 불러오는 데 실패했습니다.';
        } finally {
            isLoading.value = false;
            refreshIcons();
        }
    };

    onMounted(async () => {
        await mainStore.checkLoginStatus();
        if (!mainStore.isLoggedIn) {
            alert('로그인이 필요한 기능입니다. 로그인 해주세요.');
            router.push({ name: 'login' });
            return;
        }

        const reportId = route.query.reportId;
        if (reportId) {
            await fetchDetailedReport(reportId);
        } else {
            error.value = '리포트 ID가 제공되지 않았습니다.';
            isLoading.value = false;
        }
        refreshIcons();
    });

    watch(route, (newRoute, oldRoute) => {
        if (newRoute.query.reportId && newRoute.query.reportId !== oldRoute.query.reportId) {
            fetchDetailedReport(newRoute.query.reportId);
        }
    });

    </script>

    <template>
        <div id="screen-report" class="screen p-6 flex flex-col flex-grow">
            <div class="screen-report-navi">
                <header class="flex items-center mb-4 sticky top-0 bg-gray-50/80 backdrop-blur-sm z-10 -mx-6 px-6 pt-6 pb-4">
                    <button class="p-2 rounded-full hover:bg-gray-200" @click="router.go(-1)">
                        <i data-lucide="arrow-left"></i>
                    </button>
                    <h2 class="text-xl font-semibold mx-auto">일일 감정 리포트</h2>
                </header>
            </div>

            <div v-if="isLoading" class="flex-grow flex items-center justify-center text-gray-500">
                <i data-lucide="loader" class="animate-spin mr-2"></i> 리포트를 불러오는 중...
            </div>
            <div v-else-if="error" class="flex-grow flex items-center justify-center text-red-500">
                <i data-lucide="alert-triangle" class="mr-2"></i> {{ error }}
            </div>
            <div v-else-if="reportData" id="screen-report-scrollable" class="space-y-6 flex-grow overflow-y-auto scrollbar-hide">
                <p class="text-center text-gray-500 mb-6" id="report-date">{{ new Date(reportData.report_created).toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' }) }}</p>

                <!-- 주요 감정 분포 -->
                <div class="bg-white p-5 rounded-2xl shadow-md">
                    <h3 class="font-bold text-lg mb-4">주요 감정 분포</h3>
                    <div class="w-full h-48 flex items-center justify-center">
                        <svg viewBox="0 0 100 100" class="w-40 h-40">
                            <!-- 회색 배경원 -->
                            <circle cx="50" cy="50" r="45" fill="none" stroke="#e5e7eb" stroke-width="10"></circle>
                            <!-- 감정별 파이 세그먼트 -->
                            <path
                                v-for="(segment, index) in pieChartSegments"
                                :key="index"
                                :d="segment.path"
                                fill="none"
                                :stroke="segment.color"
                                stroke-width="10"
                                stroke-linecap="round"
                            ></path>
                        </svg>
                    </div>
                     <div class="grid grid-cols-2 gap-2 mt-4 text-sm" id="emotion-distribution-legend">
                        <div v-for="(segment, index) in pieChartSegments" :key="index" class="flex items-center">
                            <span class="w-3 h-3 rounded-full mr-2" :style="{ backgroundColor: segment.color }"></span>
                            {{ segment.emotion }} {{ segment.percentage }}
                        </div>
                    </div>
                </div>

                <!-- 시간별 감정 변화 -->
                <div class="bg-white p-5 rounded-2xl shadow-md">
                    <h3 class="font-bold text-lg mb-4">시간별 감정 변화</h3>
                    <div class="w-full h-40 flex items-end justify-center relative">
                        <svg viewBox="0 0 200 100" class="w-full h-full absolute">
                            <!-- X축 라인 -->
                            <line x1="10" y1="90" x2="190" y2="90" stroke="#ccc" stroke-width="1"/>
                            <!-- Y축 라인 (좌표 50점 기준) -->
                            <line x1="10" y1="45" x2="190" y2="45" stroke="#eee" stroke-width="1" stroke-dasharray="2 2"/>

                            <polyline :points="timeSeriesData.points" fill="none" stroke="#818cf8" stroke-width="2"/>
                            <circle
                                v-for="(score, index) in timeSeriesData.rawScores"
                                :key="index"
                                :cx="10 + (index / (timeSeriesData.rawScores.length - 1)) * (200 - 2 * 10)"
                                :cy="10 + (100 - 2 * 10) - ((score - 0) / (100 - 0)) * (100 - 2 * 10)"
                                r="3"
                                fill="#4f46e5"
                            />
                        </svg>
                        <div class="absolute bottom-1 left-0 right-0 flex justify-between px-2 text-xs text-gray-500 w-full">
                            <span v-for="(time, index) in timeSeriesData.labels" :key="index">{{ time }}</span>
                        </div>
                    </div>
                </div>

                <!-- 챗봇의 종합적인 감정 메시지 -->
                <div class="bg-indigo-50 p-5 rounded-2xl shadow-inner">
                    <p class="text-3xl mb-2" id="report-overall-emotion-icon">{{ reportData.report_summary.overall_emotion_icon }}</p>
                    <p class="text-gray-800" id="report-overall-message">{{ reportData.report_summary.overall_emotion_message }}</p>
                </div>

                <!-- 챗봇의 추가 코멘트 (임시) -->
                <div class="bg-white p-5 rounded-2xl shadow-md">
                    <h3 class="font-bold text-lg mb-2">챗봇의 추가 코멘트</h3>
                    <p class="text-gray-600" id="chatbot-comment">
                        {{ reportData.report_detail?.gemini_additional_comment || '분석된 세그먼트를 종합해 볼 때, 전반적으로 긍정적인 감정 흐름을 보였어요. 특히 특정 구간에서 활발한 감정 표현이 관찰되었답니다.' }}
                    </p>
                </div>
                <!-- 감정 관리 팁 (임시) -->
                <div class="bg-white p-5 rounded-2xl shadow-md">
                    <h3 class="font-bold text-lg mb-2">감정 관리 팁</h3>
                    <p class="text-gray-600" id="emotion-management-tip">
                        {{ reportData.report_detail?.gemini_emotion_tip || '오늘의 긍정적인 감정을 더욱 풍성하게 만들려면, 그 순간의 기분을 일기로 기록해 보세요. 부정적인 감정은 잠시 멈추고 심호흡을 하며 자신을 돌아보는 시간을 갖는 것이 도움이 될 수 있습니다.' }}
                    </p>
                </div>
                <div class="h-20"></div> <!-- 하단 여백 -->
            </div>
        </div>
    </template>

    <style scoped>
    .screen {
        display: flex !important; /* Force display */
    }
    .screen-report-navi {
        position: sticky;
        top: 0;
        z-index: 10;
    }
    .report-date {
        margin-top: -1rem; /* Adjust if header has more padding */
    }
    </style>
