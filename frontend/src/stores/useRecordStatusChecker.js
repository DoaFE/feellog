import { ref, onMounted, onUnmounted } from 'vue';
import axios from 'axios';

// Axios 인스턴스 설정 (필요에 따라 baseURL, withCredentials 등을 설정)
const apiClient = axios.create({
  baseURL: 'http://localhost:5000/api', // 백엔드 주소
  withCredentials: true, // 세션 쿠키를 주고받기 위해 필수
});

export function useRecordStatusChecker() {
  // --- 상태 관리 (State) ---

  // 현재 추적 중인 'processing' 상태의 레코드 ID
  const processingRecordId = ref(null);

  // 토스트 알림을 표시할지 여부
  const showToast = ref(false);

  // 토스트 알림에 표시될 메시지
  const toastMessage = ref('');

  // 주기적인 API 호출을 위한 인터벌 ID
  let intervalId = null;

  // --- 핵심 로직 (Core Logic) ---

  /**
   * 백엔드 API를 호출하여 최신 레코드의 상태를 확인하는 함수.
   */
  const checkStatus = async () => {
    try {
      const { data } = await apiClient.get('/records/latest-status');

      // 추적 중인 record_id가 있을 경우 (이전에 'processing' 상태를 발견한 경우)
      if (processingRecordId.value) {
        // 추적 중이던 ID와 현재 최신 ID가 동일하고, 상태가 'completed'로 변경되었는지 확인
        if (processingRecordId.value === data.record_id && data.status === 'completed') {
          console.log(`[StatusChecker] Record ${data.record_id} completed!`);

          // 토스트 알림 표시
          toastMessage.value = '영상 분석 완료!';
          showToast.value = true;

          // 3초 후에 토스트 알림 숨기기
          setTimeout(() => {
            showToast.value = false;
          }, 3000);

          // 상태 추적 종료 (중복 알림 방지)
          processingRecordId.value = null;
        }
      }
      // 추적 중인 record_id가 없을 경우
      else {
        // 새로운 레코드가 'processing' 상태인지 확인
        if (data.record_id && data.status === 'processing') {
          console.log(`[StatusChecker] Start tracking record ${data.record_id}`);
          // 새로운 'processing' 레코드 추적 시작
          processingRecordId.value = data.record_id;
        }
      }
    } catch (error) {
      // 로그인되지 않았거나(401) 다른 서버 에러 발생 시 인터벌을 계속 유지하되, 콘솔에 에러를 기록함.
      // 404 (Not Found)와 같은 특정 에러는 무시할 수 있음.
      if (error.response && error.response.status !== 401) {
          console.error('분석 상태 확인 중 오류 발생:', error);
      }
    }
  };

  // --- 생명주기 훅 (Lifecycle Hooks) ---

  // 컴포넌트가 마운트될 때 인터벌 시작
  onMounted(() => {
    // 1초(1000ms)마다 checkStatus 함수를 실행
    intervalId = setInterval(checkStatus, 1000);
  });

  // 컴포넌트가 언마운트될 때 인터벌 정리 (메모리 누수 방지)
  onUnmounted(() => {
    if (intervalId) {
      clearInterval(intervalId);
    }
  });

  // --- 반환 값 (Return) ---
  // 외부 컴포넌트에서 사용할 반응형 상태와 함수를 반환
  return {
    showToast,
    toastMessage,
  };
}
