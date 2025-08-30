<script setup>
    import { ref, onMounted, onUpdated, watch } from 'vue';
    import { useRouter } from 'vue-router';
    import axios from 'axios';
    import { createLucideIcon, icons } from 'lucide-vue-next';
    import { ArrowLeftIcon } from 'lucide-vue-next';
    import { useMainStore } from '@/stores/main';
    const mainStore = useMainStore();

    const router = useRouter();

    const personas = ref([]);
    const selectedPersonaId = ref(null);
    const isLoading = ref(true);
    const error = ref(null);

    const refreshIcons = () => {
        createLucideIcon({ icons, attrs: { class: 'lucide-icon' }, nameAttr: 'data-lucide' });
    };

    const fetchPersonas = async () => {
        isLoading.value = true;
        error.value = null;
        try {
            const response = await axios.get('/api/chatbot/personas');
            if (response.data.success) {
                personas.value = response.data.personas;
            } else {
                error.value = response.data.message;
            }
        } catch (err) {
            console.error('Error fetching personas:', err);
            error.value = '챗봇 페르소나 목록을 불러오는 데 실패했습니다.';
        } finally {
            isLoading.value = false;
        }
    };

    const fetchUserSelectedPersona = async () => {
        try {
            const response = await axios.get('/api/user/persona');
            if (response.data.success && response.data.selected_persona_id) {
                selectedPersonaId.value = response.data.selected_persona_id;
            } else {
                selectedPersonaId.value = null; // 선택된 페르소나 없음
            }
        } catch (err) {
            console.error('Error fetching user selected persona:', err);
            selectedPersonaId.value = null;
        }
    };

    const selectPersona = async (personaId, personaName) => {
        if (!mainStore.isLoggedIn) {
            alert('로그인이 필요한 기능입니다.');
            router.push({ name: 'login' });
            return;
        }
        if (selectedPersonaId.value === personaId) {
            alert('이미 선택된 페르소나입니다.');
            return;
        }

        try {
            const response = await axios.post('/api/user/persona', { chatbot_id: personaId });
            if (response.data.success) {
                selectedPersonaId.value = personaId;
                alert(`챗봇 페르소나가 '${personaName}'으로 변경되었습니다.`);
            } else {
                alert(`페르소나 변경 실패: ${response.data.message}`);
            }
        } catch (err) {
            console.error('Error selecting persona:', err);
            alert('페르소나 변경 중 오류가 발생했습니다.');
        }
    };
    const goBack = () => {
      router.push({ name: 'settings' });
    };

    onMounted(async () => {
        await mainStore.checkLoginStatus();
        if (!mainStore.isLoggedIn) {
            alert('로그인이 필요한 기능입니다.');
            router.push({ name: 'login' });
            return;
        }
        await fetchPersonas();
        await fetchUserSelectedPersona();
        refreshIcons();
    });

    onUpdated(refreshIcons);
    watch(router.currentRoute, () => {
        refreshIcons();
    });
    </script>

    <template>
        <div id="screen-character-settings" class="screen p-6 flex flex-col flex-grow">
            <header class="flex items-center mb-4">
              <button class="p-2 rounded-full hover:bg-gray-700" @click="goBack">
                <ArrowLeftIcon class="cta-icon" aria-hidden="true" />
              </button>
              <h2 class="text-xl font-semibold mx-auto">챗봇 캐릭터 설정</h2>
            </header>

            <div v-if="isLoading" class="flex-grow flex items-center justify-center text-gray-500">
                <i data-lucide="loader" class="animate-spin mr-2"></i> 페르소나를 불러오는 중...
            </div>
            <div v-else-if="error" class="flex-grow flex items-center justify-center text-red-500">
                <i data-lucide="alert-triangle" class="mr-2"></i> {{ error }}
            </div>
            <div v-else class="space-y-6 flex-grow overflow-y-auto scrollbar-hide">
                <div
                    v-for="persona in personas"
                    :key="persona.chatbot_id"
                    :class="['bg-white p-5 rounded-2xl shadow-md border-2 cursor-pointer persona-card',
                             selectedPersonaId === persona.chatbot_id ? 'border-indigo-500' : 'border-transparent hover:border-indigo-300']"
                    @click="selectPersona(persona.chatbot_id, persona.chatbot_name)"
                >
                    <h3 :class="['font-bold text-lg mb-2', selectedPersonaId === persona.chatbot_id ? 'text-indigo-600' : 'text-gray-800']">{{ persona.chatbot_name }}</h3>
                    <p class="text-gray-600 mb-4">{{ persona.chatbot_identity }} ({{ persona.chatbot_personality }})</p>
                    <button
                        :class="['w-full font-semibold py-2 rounded-lg persona-select-btn',
                                 selectedPersonaId === persona.chatbot_id ? 'bg-indigo-500 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300']"
                        :disabled="selectedPersonaId === persona.chatbot_id"
                        @click.stop="selectPersona(persona.chatbot_id, persona.chatbot_name)"
                    >
                        {{ selectedPersonaId === persona.chatbot_id ? '선택됨' : '선택하기' }}
                    </button>
                </div>
                <div class="h-20"></div>
            </div>
        </div>
    </template>

    <style scoped>
    .screen {
        display: flex !important;
    }
    </style>
