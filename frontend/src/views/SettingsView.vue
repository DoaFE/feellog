<script setup>
    import { ref, onMounted, onUpdated, computed } from 'vue';
    import { useRouter } from 'vue-router';
    import { createLucideIcon } from 'lucide-vue-next';
    import { useMainStore } from '@/stores/main';
    const mainStore = useMainStore();
    const router = useRouter();

    const refreshIcons = () => {
        createLucideIcon({ icons, attrs: { class: 'lucide-icon' }, nameAttr: 'data-lucide' });
    };

    const handleLogout = async () => {
        const success = await mainStore.logout();
        if (success) {
            router.push({ name: 'login' }); // 로그아웃 성공 시 로그인 페이지로 이동
        }
    };

    const goToChatbotPersonaSettings = () => {
        if (mainStore.isLoggedIn) {
            router.push({ name: 'setting-persona' });
        } else {
            alert('로그인이 필요한 기능입니다.');
        }
    };

    onMounted(async () => {
        await mainStore.checkLoginStatus(); // 컴포넌트 마운트 시 로그인 상태 확인
        refreshIcons();
    });

    onUpdated(refreshIcons); // Ensure icons are refreshed if component updates
    </script>

    <template>
        <div id="screen-settings" class="screen bg-gray-50 flex flex-col flex-grow">
            <div class="p-6">
                <h2 class="text-3xl font-bold text-gray-800 mb-8">설정</h2>
            </div>
            <div class="flex-grow overflow-y-auto scrollbar-hide">
                <div class="px-6 py-4">
                    <h3 class="text-sm font-semibold text-gray-500 uppercase mb-3">계정</h3>
                    <ul class="bg-white rounded-2xl shadow-md divide-y divide-gray-200">
                        <li class="p-4 flex justify-between items-center cursor-pointer hover:bg-gray-50"><span>프로필 설정</span><i data-lucide="chevron-right" class="text-gray-400"></i></li>
                    </ul>
                </div>
                <div class="px-6 py-4">
                    <h3 class="text-sm font-semibold text-gray-500 uppercase mb-3">앱 설정</h3>
                    <ul class="bg-white rounded-2xl shadow-md divide-y divide-gray-200">
                        <li class="p-4 flex justify-between items-center cursor-pointer hover:bg-gray-50"><span>알림 설정</span><i data-lucide="chevron-right" class="text-gray-400"></i></li>
                        <li class="p-4 flex justify-between items-center cursor-pointer hover:bg-gray-50"><span>데이터 관리</span><i data-lucide="chevron-right" class="text-gray-400"></i></li>
                        <li
                            :class="['p-4 flex justify-between items-center cursor-pointer', mainStore.isLoggedIn ? 'hover:bg-gray-50' : 'text-gray-400 cursor-not-allowed']"
                            @click="goToChatbotPersonaSettings"
                        >
                            <span>챗봇 캐릭터 설정</span><i data-lucide="chevron-right" :class="{'text-gray-400': !mainStore.isLoggedIn}"></i>
                        </li>
                    </ul>
                </div>
                <div class="px-6 py-4">
                    <h3 class="text-sm font-semibold text-gray-500 uppercase mb-3">정보</h3>
                    <ul class="bg-white rounded-2xl shadow-md divide-y divide-gray-200">
                        <li class="p-4 flex justify-between items-center cursor-pointer hover:bg-gray-50"><span>개인정보 처리방침 및 약관</span><i data-lucide="chevron-right" class="text-gray-400"></i></li>
                        <li class="p-4 flex justify-between items-center"><span>앱 버전 정보</span><span class="text-gray-500">v1.0.0</span></li>
                    </ul>
                </div>
                <div class="px-6 py-4">
                    <ul class="bg-white rounded-2xl shadow-md divide-y divide-gray-200">
                        <li v-if="mainStore.isLoggedIn"
                            class="p-4 flex justify-between items-center text-red-500 cursor-pointer hover:bg-red-50"
                            @click="handleLogout"
                        ><span>로그아웃</span></li>
                        <li v-else
                            class="p-4 flex justify-between items-center text-indigo-600 cursor-pointer hover:bg-indigo-50"
                            @click="router.push({ name: 'login' })"
                        ><span>로그인</span></li>
                        <li class="p-4 flex justify-between items-center text-gray-500 cursor-pointer hover:bg-gray-50"><span>회원 탈퇴</span></li>
                    </ul>
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
