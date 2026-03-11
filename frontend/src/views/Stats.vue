<template>
  <div id="chart" style="width: 600px; height: 400px;"></div>
</template>

<script setup>
import { onMounted } from 'vue';
import * as echarts from 'echarts';
import request from '../api/request';

onMounted(async () => {
  const res = await request.get('/stats/views');
  const chart = echarts.init(document.getElementById('chart'));
  chart.setOption({
    title: { text: '新闻阅读量排行' },
    xAxis: { data: res.data.categories },
    yAxis: {},
    series: [{ type: 'bar', data: res.data.values }]
  });
});
</script>