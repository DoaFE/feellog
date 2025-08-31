<template>
  <div class="bg-white p-4 rounded-lg shadow">
    <h3 class="font-bold mb-4 text-center text-gray-800">월간 감정 트렌드</h3>
    <apexchart
      type="area"
      height="300"
      :options="chartOptions"
      :series="series"
    ></apexchart>
  </div>
</template>

<script setup>
import { computed } from 'vue';
// vue3-apexcharts를 import
import Apexchart from 'vue3-apexcharts';

const props = defineProps({
  positiveData: {
    type: Array,
    required: true,
  },
  negativeData: {
    type: Array,
    required: true,
  },
});

// ApexCharts의 series 형식에 맞게 데이터 가공
const series = computed(() => [
  {
    name: '긍정 감정',
    data: props.positiveData.map(d => (d.score * 100).toFixed(2)),
  },
  {
    name: '부정 감정',
    data: props.negativeData.map(d => (d.score * 100).toFixed(2)),
  },
]);

// ApexCharts의 options 설정
const chartOptions = computed(() => ({
  chart: {
    height: 300,
    type: 'area',
    toolbar: {
      show: false, // 차트 상단 툴바 숨기기
    },
    animations: {
      enabled: true, // 부드러운 애니메이션 사용
      easing: 'easeinout',
      speed: 800,
    }
  },
  colors: ['#3B82F6', '#EF4444'], // 긍정(파랑), 부정(빨강) 색상
  dataLabels: {
    enabled: false, // 데이터 포인트에 라벨 숨기기
  },
  stroke: {
    curve: 'smooth', // 부드러운 곡선
    width: 2,
  },
  xaxis: {
    categories: props.positiveData.map(d => `${d.day}일`), // X축 라벨 (날짜)
    labels: {
      style: {
        colors: '#6B7280', // 라벨 색상
      },
    },
  },
  yaxis: {
    labels: {
      formatter: (value) => {
        return value ? `${value.toFixed(0)}%` : '0%'; // Y축 라벨에 '%' 추가
      },
      style: {
        colors: '#6B7280',
      },
    },
  },
  tooltip: {
    x: {
      format: 'dd일',
    },
    y: {
      formatter: (value) => `${value.toFixed(2)}%`,
    },
    theme: 'light',
  },
  legend: {
    position: 'top',
    horizontalAlign: 'center',
    markers: {
      width: 12,
      height: 12,
    },
  },
  fill: {
    type: 'gradient',
    gradient: {
      shadeIntensity: 1,
      opacityFrom: 0.7,
      opacityTo: 0.2,
      stops: [0, 100]
    }
  },
  grid: {
    borderColor: '#f1f1f1',
  }
}));
</script>
